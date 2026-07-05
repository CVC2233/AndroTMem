"""
base_evaluator.py — 评估器抽象基类
base_evaluator.py — abstract evaluator base class

子类必须实现：
Subclasses must implement:
  - prepare_image(image_name) -> (image_input, orig_w, orig_h)
  - request_model(prompt_text, image_input) -> (raw_pred, metrics)

eval_task 主循环由基类统一管理：
The eval_task main loop is centrally managed by the base class:
  - 断点续传
  - checkpoint resume
  - v1/v2/v3 context 构建与更新
  - v1/v2/v3 context construction and updates
  - 深拷贝反归一化（修复原地修改 bug）
  - deep-copy denormalization to avoid in-place mutation bugs
  - 写盘
  - result persistence
"""

import os
import copy
import threading
import jsonlines
from abc import ABC, abstractmethod
from typing import Any

from prompts import get_sys_prompt
from utils import (
    build_context_v1,
    build_context_v2,
    build_context_v3,
    extract_milestones,
    denormalize_prediction,
)


class BaseEvaluator(ABC):

    def __init__(self, cfg: dict):
        self.cfg         = cfg
        self.version     = cfg["version"]
        self.coord_scale = cfg.get("coord_scale", 1000)

        os.makedirs(cfg["output_dir"], exist_ok=True)

        # output_filename 支持 {version} / {model_name} 等占位符
        # output_filename supports placeholders such as {version} and {model_name}.
        filename = cfg["output_filename"].format(**cfg)
        self.output_path = os.path.join(cfg["output_dir"], filename)

        self.write_lock    = threading.Lock()
        self.finished_data = self._load_checkpoint()

    # ── Checkpoint ────────────────────────────────────────────────────────────

    def _load_checkpoint(self) -> dict:
        """
        加载已完成的 (task_id, step_index) → prediction 映射。
        Load the completed (task_id, step_index) -> prediction mapping.
        key 统一为 (str, str)，避免 int/str 不一致导致的匹配失败。
        Normalize keys to (str, str) to avoid misses caused by int/str mismatches.
        """
        data_map = {}
        if not os.path.exists(self.output_path):
            return data_map

        print(f"Loading checkpoint: {self.output_path}")
        try:
            with jsonlines.open(self.output_path) as reader:
                for obj in reader:
                    key = (str(obj["task_id"]), str(obj["step_index"]))
                    data_map[key] = obj["prediction"]
        except Exception as e:
            print(f"Checkpoint load error: {e}")
        return data_map

    def _write_result(
        self,
        task_id: str,
        step_index: Any,
        prediction: dict,
        extra: dict | None = None,
    ) -> None:
        """线程安全地追加写入一条预测结果。
        Append one prediction record in a thread-safe way.
        """
        record = {
            "task_id":    task_id,
            "step_index": step_index,
            "prediction": prediction,
        }
        if extra:
            record.update(extra)

        with self.write_lock:
            with jsonlines.open(self.output_path, mode="a") as writer:
                writer.write(record)

        # 更新内存缓存
        # Update the in-memory cache.
        self.finished_data[(str(task_id), str(step_index))] = prediction

    @staticmethod
    def _build_auto_pass_prediction(image_name: str) -> dict:
        """构造缺图步骤的自动判对结果。
        Build an auto-pass prediction for a missing-image step.
        """
        return {
            "action": {
                "action": "AUTO_PASS",
                "x": 0,
                "y": 0,
                "value": "",
                "x_end": 0,
                "y_end": 0,
                "direction": "",
                "distance": "",
            },
        }

    @staticmethod
    def _build_execution_extra(prediction: dict) -> dict:
        """构造统一的单条执行状态字段。
        Build unified per-record execution status fields.
        """
        if not isinstance(prediction, dict):
            return {
                "execution_status": "error",
                "execution_message": f"invalid prediction type: {type(prediction).__name__}",
            }

        action = prediction.get("action", {})
        if action.get("action") == "ERROR" or prediction.get("error"):
            return {
                "execution_status": "error",
                "execution_message": str(prediction.get("error", "model inference failed")),
            }
        return {
            "execution_status": "success",
            "execution_message": "model inference completed",
        }

    # ── Prompt ────────────────────────────────────────────────────────────────

    def get_sys_prompt(self) -> str:
        return get_sys_prompt(
            version=self.version,
            coord_scale=self.coord_scale,
            compact=self.cfg.get("compact_prompt", False),
        )

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def prepare_image(self, image_name: str) -> tuple[Any, int, int]:
        """
        准备图像输入。
        Prepare the image input.

        Returns:
            (image_input, orig_w, orig_h)
            image_input 类型由子类决定（base64 data_url / 文件路径）
            The image_input type is decided by subclasses: base64 data URL or file path.
            失败时返回 (None, 0, 0)
            Return (None, 0, 0) on failure.
        """
        ...

    @abstractmethod
    def request_model(self, prompt_text: str, image_input: Any) -> tuple[dict, dict]:
        """
        向模型发起推理请求。
        Send an inference request to the model.

        Returns:
            (raw_pred, metrics)
            raw_pred: 归一化坐标的预测 dict
            raw_pred: prediction dict with normalized coordinates.
            metrics:  性能指标 dict（无则返回 {}）
            metrics: performance metrics dict, or {} when unavailable.
        """
        ...

    # ── Main eval loop ────────────────────────────────────────────────────────

    def eval_task(self, task: dict) -> None:
        tid   = str(task.get("task_id", ""))
        steps = task.get("steps", [])
        if not tid or not steps:
            return

        instr = task.get("instruction_en") or task.get("instruction", "")

        # version 专属的上下文累积状态
        # Version-specific accumulated context state.
        h_v1 = []        # v1: 动作历史（像素坐标，与 checkpoint 保持一致）
                         # v1: action history in pixel coordinates, consistent with checkpoints.
        s_v2 = "None"    # v2: 上一步摘要
                         # v2: previous-step summary.
        m_v3 = []        # v3: 里程碑列表 [{"content_en":..., "description_en":...}]
                         # v3: milestone list [{"content_en":..., "description_en":...}].

        for step in steps:
            step_idx = step.get("step_index")
            if step_idx is None:
                continue

            key = (tid, str(step_idx))

            # ── 断点续传 ──────────────────────────────────────────────────────
            # ── Checkpoint resume ─────────────────────────────────────────────
            if key in self.finished_data:
                cp = self.finished_data[key]
                # cp 是已写盘的 pixel_pred（像素坐标）
                # cp is the persisted pixel_pred in pixel coordinates.
                # AUTO_PASS 是缺图自动判对结果，不加入后续上下文。
                # AUTO_PASS is a missing-image auto-credit result; do not add it to context.
                if cp.get("action", {}).get("action") == "AUTO_PASS":
                    continue
                if self.version == "v1":
                    h_v1.append(copy.deepcopy(cp.get("action", {})))
                elif self.version == "v2":
                    s_v2 = cp.get("summary_en", s_v2)
                else:
                    m_v3.extend(extract_milestones(cp))
                continue

            # ── 准备图像 ─────────────────────────────────────────────────────
            # ── Prepare image ────────────────────────────────────────────────
            image_name = step.get("image_name", "")
            image_input, orig_w, orig_h = self.prepare_image(image_name)
            if image_input is None:
                # print(f"  ⚠️  Image load failed: {image_name}，AUTO_PASS: {tid}/{step_idx}")
                auto_pass_pred = self._build_auto_pass_prediction(image_name)
                self._write_result(
                    task_id=tid,
                    step_index=step_idx,
                    prediction=auto_pass_pred,
                    extra={
                        "execution_status": "error",
                        "execution_message": f"image missing: {image_name}",
                        "image_missing": True,
                        "credited_as_correct": True,
                        "image_name": image_name,
                    },
                )
                continue

            # ── 构建 context ──────────────────────────────────────────────────
            # ── Build context ────────────────────────────────────────────────
            if self.version == "v1":
                ctx = build_context_v1(instr, h_v1)
            elif self.version == "v2":
                ctx = build_context_v2(instr, s_v2)
            else:
                ctx = build_context_v3(
                    instr,
                    m_v3,
                    max_milestones=self.cfg.get("v3_max_milestones_in_prompt", 50),
                )

            # ── 模型推理 ─────────────────────────────────────────────────────
            # ── Model inference ──────────────────────────────────────────────
            raw_pred, metrics = self.request_model(ctx, image_input)

            # ── 反归一化：深拷贝，raw_pred 保持归一化坐标 ─────────────────────
            # ── Denormalize by deep copy, keeping raw_pred in normalized coordinates.
            #   修复原始代码中 denormalize 原地修改 raw_pred 的 bug。
            #   Fix the original bug where denormalize mutated raw_pred in place.
            pixel_pred = denormalize_prediction(raw_pred, orig_w, orig_h, self.coord_scale)

            # ── 更新 context ──────────────────────────────────────────────────
            # ── Update context ───────────────────────────────────────────────
            #   v1: 用 pixel_pred（与 checkpoint 恢复保持一致）
            #   v1: use pixel_pred to stay consistent with checkpoint recovery.
            #   v2/v3: text 字段，用 raw_pred 或 pixel_pred 均可
            #   v2/v3: text fields work with either raw_pred or pixel_pred.
            if self.version == "v1":
                h_v1.append(copy.deepcopy(pixel_pred.get("action", {})))
            elif self.version == "v2":
                s_v2 = raw_pred.get("summary_en", "")
            else:
                m_v3.extend(extract_milestones(raw_pred))

            # ── 写盘（pixel_pred，与评估脚本坐标体系对齐）────────────────────
            # ── Persist pixel_pred, aligned with the evaluator coordinate system.
            extra = self._build_execution_extra(pixel_pred)
            if metrics:
                extra["metrics"] = metrics
            self._write_result(
                task_id=tid,
                step_index=step_idx,
                prediction=pixel_pred,
                extra=extra,
            )
