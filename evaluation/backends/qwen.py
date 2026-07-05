"""
backends/qwen.py — Qwen2.5-VL（HuggingFace 本地开源模型）后端
backends/qwen.py — Qwen2.5-VL backend using a local open-source HuggingFace model

特性：
Features:
  - Qwen2.5-VL 推理流程（apply_chat_template + process_vision_info）
  - Qwen2.5-VL inference flow with apply_chat_template and process_vision_info
  - _fix_prediction：动作别名映射、坐标字段兼容、噪声清洗
  - _fix_prediction: action alias mapping, coordinate-field compatibility, and noise cleanup
  - _strip_think：去除 <think>...</think> 推理链
  - _strip_think: remove <think>...</think> reasoning traces
  - _extract_last_json：取最后一个 JSON 块（Qwen 系列输出习惯）
  - _extract_last_json: take the last JSON block, matching Qwen-style outputs
  - 统一里程碑格式：{"milestones": [{"content_en":..., "description_en":...}]}
  - unified milestone format: {"milestones": [{"content_en":..., "description_en":...}]}
"""

import os
import re
import json
import time

import json_repair
import torch
from PIL import Image
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

from base_evaluator import BaseEvaluator


# ─── HF 模型封装 ──────────────────────────────────────────────────────────────
# ─── HF model wrapper ────────────────────────────────────────────────────────

class _HFModel:
    """Qwen2.5-VL 推理封装，单 GPU 友好。
    Qwen2.5-VL inference wrapper, friendly to single-GPU setups.
    """

    # 允许的 action 值（用于别名映射）
    # Allowed action values used for alias mapping.
    _ACTION_ALIAS = {
        "click":      "tap",
        "tap":        "tap",
        "press":      "long_press",
        "longpress":  "long_press",
        "long_press": "long_press",
        "input_text": "text",
        "type":       "text",
        "input":      "text",
        "text":       "text",
        "swipe":      "swipe",
        "scroll":     "swipe",
        "open":       "open_app",
        "open_app":   "open_app",
        "wait":       "wait",
        "back":       "back",
        "home":       "home",
        "terminate":  "FINISH",
        "finish":     "FINISH",
        "FINISH":     "FINISH",
        "need_feedback":    "need_feedback",
        "capture_screen":   "capture_screen",
        "swipe_two_points": "swipe_two_points",
    }

    def __init__(self, model_id: str, max_pixels: int, dtype: str, use_flash_attn: bool):
        torch_dtype = {
            "bfloat16": torch.bfloat16,
            "float16":  torch.float16,
            "float32":  torch.float32,
        }.get(dtype.lower(), torch.float16)

        if not torch.cuda.is_available():
            torch_dtype = torch.float32

        model_kwargs: dict = {"torch_dtype": torch_dtype, "device_map": "auto"}
        if use_flash_attn:
            model_kwargs["attn_implementation"] = "flash_attention_2"

        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id, **model_kwargs
        )
        self.processor = AutoProcessor.from_pretrained(
            model_id, max_pixels=max_pixels, padding_side="left"
        )

    # ── 后处理工具 ────────────────────────────────────────────────────────────
    # ── Post-processing helpers ──────────────────────────────────────────────

    @staticmethod
    def _strip_think(text: str) -> str:
        return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()

    @staticmethod
    def _extract_last_json(text: str) -> str:
        matches = list(re.finditer(r"\{.*\}", text, flags=re.DOTALL))
        return matches[-1].group(0).strip() if matches else text.strip()

    def _normalize_action(self, pred: dict) -> dict:
        """
        修复开源模型常见的输出噪声：
        Fix common output noise from open-source models:
          - tool_call 风格展开
          - expand tool_call-style outputs
          - 扁平化 action 字段
          - normalize flattened action fields
          - 动作别名映射
          - map action aliases
          - 坐标字段兼容（coordinate / coordinate2 / point_2d）
          - support coordinate-field variants: coordinate / coordinate2 / point_2d
          - 数值类型清洗
          - clean numeric field types
          - 缺省字段补全
          - fill missing default fields
        """
        _ERR = lambda reason="": {
            "action": {
                "action": "ERROR", "x": 0, "y": 0,
                "value": "", "x_end": 0, "y_end": 0,
                "direction": "", "distance": "",
            },
            "error": reason,
        }

        if not isinstance(pred, dict):
            return _ERR(f"non-dict output: {type(pred)}")

        # tool_call 风格
        # tool_call-style output.
        if "arguments" in pred and isinstance(pred["arguments"], dict):
            pred = {"action": pred["arguments"]}

        if "action" not in pred:
            return _ERR("missing 'action' key")

        action_field = pred["action"]

        # 扁平化：{"action": "tap", "x": ...}
        # Flattened form: {"action": "tap", "x": ...}.
        if isinstance(action_field, str):
            pred["action"] = {
                "action":    action_field,
                "x":         pred.pop("x", 0),
                "y":         pred.pop("y", 0),
                "value":     pred.pop("value", ""),
                "direction": pred.pop("direction", ""),
                "distance":  pred.pop("distance", ""),
                "x_end":     pred.pop("x_end", 0),
                "y_end":     pred.pop("y_end", 0),
            }
            action_field = pred["action"]
        elif not isinstance(action_field, dict):
            return _ERR(f"action field has unexpected type: {type(action_field)}")

        act = action_field

        # 动作别名映射
        # Map action aliases.
        raw_action = str(act.get("action", "")).strip()
        act["action"] = self._ACTION_ALIAS.get(raw_action, raw_action) or "ERROR"

        # 坐标字段兼容
        # Support coordinate-field variants.
        def pop_coord(key, alt1, alt2=None):
            if key in act:
                return
            for src in [alt1, alt2]:
                if src and src in act:
                    val = act.pop(src)
                    if isinstance(val, list) and len(val) >= 2:
                        act["x" if "x" in key else "y"] = val[0]
                        # 双点坐标会在 alt2 中处理
                        # Two-point coordinates are handled through alt2.
                    break

        if "coordinate" in act:
            c = act.pop("coordinate")
            if isinstance(c, list) and len(c) >= 2:
                act["x"], act["y"] = c[0], c[1]
        if "coordinate2" in act:
            c2 = act.pop("coordinate2")
            if isinstance(c2, list) and len(c2) >= 2:
                act["x_end"], act["y_end"] = c2[0], c2[1]
        if "point_2d" in act:
            p = act.pop("point_2d")
            if isinstance(p, list) and len(p) >= 2:
                act["x"], act["y"] = p[0], p[1]

        # 数值字段清洗
        # Clean numeric fields.
        def to_number(v):
            if isinstance(v, list):      v = v[0] if v else 0
            if isinstance(v, str):
                try:                     return float(v)
                except ValueError:       return 0
            if v is None:                return 0
            return v if isinstance(v, (int, float)) else 0

        for f in ("x", "y", "x_end", "y_end"):
            act[f] = to_number(act.get(f, 0))

        # 字符串字段补全
        # Fill string fields.
        for f in ("value", "direction", "distance"):
            if not isinstance(act.get(f), str):
                act[f] = ""

        return pred

    def _normalize_milestones(self, pred: dict) -> dict:
        """
        将模型输出的里程碑字段统一为：
        Normalize model milestone fields to:
          {"milestones": [{"content_en": "...", "description_en": "..."}]}

        兼容以下可能的输出变体：
        Supports the following possible output variants:
          - 顶层标量: {"content_en": ..., "description_en": ...}  (API 旧格式)
          - top-level scalar fields: {"content_en": ..., "description_en": ...} (legacy API format)
          - milestones 列表（已是目标格式）
          - milestones list, already in the target format
        """
        if "milestones" not in pred:
            # 兼容旧格式：顶层标量 → 包装成列表
            # Legacy compatibility: wrap top-level scalar fields into a list.
            if "content_en" in pred or "description_en" in pred:
                pred["milestones"] = [{
                    "content_en":     pred.pop("content_en",     ""),
                    "description_en": pred.pop("description_en", ""),
                }]
            else:
                pred["milestones"] = []
            return pred

        raw = pred["milestones"]
        if not isinstance(raw, list):
            pred["milestones"] = []
            return pred

        cleaned = []
        for m in raw:
            if isinstance(m, dict):
                cleaned.append({
                    "content_en":     str(m.get("content_en",     "")).strip(),
                    "description_en": str(m.get("description_en", "")).strip(),
                })
        pred["milestones"] = cleaned
        return pred

    # ── 主推理入口 ────────────────────────────────────────────────────────────
    # ── Main inference entry point ───────────────────────────────────────────

    def generate(
        self,
        system_prompt: str,
        user_text: str,
        image_path: str,
        version: str,
        max_new_tokens: int = 512,
        temperature: float = 0.0,
    ) -> tuple[dict, dict]:
        image = Image.open(image_path).convert("RGB")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text",  "text": user_text},
            ]},
        ]

        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        prompt_tokens = int(inputs["input_ids"].shape[1])

        gen_kwargs = dict(max_new_tokens=max_new_tokens, do_sample=(temperature > 0))
        if temperature > 0:
            gen_kwargs["temperature"] = temperature

        t_start = time.time()
        with torch.inference_mode():
            output_ids = self.model.generate(**inputs, **gen_kwargs)
        t_end = time.time()

        gen_only = output_ids[:, inputs["input_ids"].shape[1]:]
        completion_tokens = int(gen_only.shape[1])
        e2e = round(t_end - t_start, 3)
        tpot = round(e2e / max(completion_tokens, 1), 4) if completion_tokens > 0 else 0.0
        # 非流式 generate 无法准确采集首 token 延迟，因此 ttft_sec 置为 0。
        # Non-streaming generate cannot measure first-token latency accurately, so ttft_sec is 0.
        metrics = {
            "e2e_sec": e2e,
            "ttft_sec": 0.0,
            "tpot_sec": tpot,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        out_text = self.processor.batch_decode(
            gen_only, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]

        out_text = self._strip_think(out_text)
        out_text = self._extract_last_json(out_text)

        try:
            obj = json_repair.loads(out_text)
            # 若返回 list，取首个含 action 的 dict
            # If a list is returned, take the first dict containing action.
            if isinstance(obj, list):
                obj = next((x for x in obj if isinstance(x, dict) and "action" in x), obj[0] if obj else {})
            if not isinstance(obj, dict):
                obj = {}
        except Exception:
            obj = {}

        obj = self._normalize_action(obj)
        if version == "v3":
            obj = self._normalize_milestones(obj)

        return obj, metrics


# ─── Backend 实现 ─────────────────────────────────────────────────────────────
# ─── Backend implementation ──────────────────────────────────────────────────

class QwenBackend(BaseEvaluator):

    def __init__(self, cfg: dict):
        self._image_base   = cfg["image_base_path"]
        self._max_retries  = cfg.get("max_retries", 3)
        self._retry_backoff = cfg.get("retry_backoff", 2)
        self._max_new_tokens = cfg.get("max_new_tokens", 512)
        self._temperature  = cfg.get("temperature", 0.0)

        self._hf = _HFModel(
            model_id=cfg["hf_model_id"],
            max_pixels=cfg.get("max_image_pixels", 5600 * 28 * 28),
            dtype=cfg.get("dtype", "float16"),
            use_flash_attn=cfg.get("use_flash_attn", False),
        )

        super().__init__(cfg)

    # ── prepare_image ─────────────────────────────────────────────────────────

    def prepare_image(self, image_name: str) -> tuple[str | None, int, int]:
        """返回图像文件路径（HF 模型直接读取文件）。
        Return the image file path; the HF model reads the file directly.
        """
        path = os.path.join(self._image_base, image_name)
        if not os.path.exists(path):
            # print(f"  ❌ Image not found: {path}")
            return None, 0, 0
        try:
            with Image.open(path) as img:
                w, h = img.size
            return path, w, h
        except Exception as e:
            # print(f"  ❌ Image open error [{image_name}]: {e}")
            return None, 0, 0

    # ── request_model ─────────────────────────────────────────────────────────

    def request_model(self, prompt_text: str, image_input: str) -> tuple[dict, dict]:
        """
        调用本地 HF 模型推理。
        Run inference with the local HF model.

        Args:
            prompt_text: 用户侧 context 文本
            prompt_text: user-side context text.
            image_input: 图像文件路径
            image_input: image file path.

        Returns:
            (raw_pred_dict, metrics_dict)  — 本地模型采集非流式 metrics
            (raw_pred_dict, metrics_dict) with non-streaming local-model metrics.
        """
        sys_prompt = self.get_sys_prompt()

        for attempt in range(self._max_retries):
            try:
                result, metrics = self._hf.generate(
                    system_prompt=sys_prompt,
                    user_text=prompt_text,
                    image_path=image_input,
                    version=self.version,
                    max_new_tokens=self._max_new_tokens,
                    temperature=self._temperature,
                )
                return result, metrics
            except Exception as e:
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_backoff ** attempt)
                else:
                    return {
                        "action": {
                            "action": "ERROR", "x": 0, "y": 0,
                            "value": "", "x_end": 0, "y_end": 0,
                            "direction": "", "distance": "",
                        },
                        "error": str(e),
                    }, {}
