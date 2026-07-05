"""
backends/gpt4o.py — GPT-4o（OpenAI 兼容接口）后端
backends/gpt4o.py — GPT-4o backend using the OpenAI-compatible API

特性：
Features:
  - 多 API Key 轮询池（修复单 key 空转 bug）
  - multi-API-key round-robin pool, fixing the single-key idle-loop bug
  - 流式请求 + TTFT / TPOT / E2E / Token 性能打点
  - streaming requests with TTFT / TPOT / E2E / token metrics
  - json_repair 容错解析
  - fault-tolerant parsing with json_repair
"""

import base64
import time
import threading
from io import BytesIO

import json_repair
from openai import OpenAI
from PIL import Image

from base_evaluator import BaseEvaluator


class _ClientPool:
    """
    多 API Key 轮询池，按 keys_rpm 限速。
    Round-robin pool for multiple API keys, rate-limited by keys_rpm.

    修复原始实现中单 key 场景下的空转问题：
    Fixes the idle-loop issue in the original single-key scenario:
    只有当前 key 不满足最小间隔时才切换；
    switch keys only when the current key does not meet the minimum interval;
    所有 key 都不满足时精确 sleep 到最早可用时间，而非盲目 sleep 0.5s。
    when all keys are unavailable, sleep exactly until the earliest key is ready instead of blindly sleeping 0.5s.
    """

    def __init__(self, api_keys: list[str], base_url: str, keys_rpm: int):
        self._clients = [
            OpenAI(api_key=k, base_url=base_url)
            for k in api_keys
        ]
        self._min_interval = 60.0 / max(keys_rpm, 1)
        self._last_used    = [0.0] * len(api_keys)
        self._lock         = threading.Lock()

    def get_client(self) -> OpenAI:
        """阻塞直到有可用 key，返回对应 client。
        Block until a key is available, then return its client.
        """
        while True:
            with self._lock:
                now = time.time()
                # 找最早可用的 key
                # Find the earliest available key.
                earliest_idx  = 0
                earliest_ready = float("inf")
                for i, last in enumerate(self._last_used):
                    ready_at = last + self._min_interval
                    if ready_at <= now:
                        self._last_used[i] = now
                        return self._clients[i]
                    if ready_at < earliest_ready:
                        earliest_ready = ready_at
                        earliest_idx   = i

            # 所有 key 都需要等待：精确 sleep 到最早可用
            # All keys need waiting; sleep until the earliest one is available.
            sleep_time = earliest_ready - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)


class GPT4OBackend(BaseEvaluator):

    def __init__(self, cfg: dict):
        self._pool = _ClientPool(
            api_keys=cfg["api_keys"],
            base_url=cfg["base_url"],
            keys_rpm=cfg.get("keys_rpm", 60),
        )
        self._model_name    = cfg["model_name"]
        self._max_retries   = cfg.get("max_retries", 3)
        self._max_image_size = cfg.get("max_image_size", 1024)
        self._image_base    = cfg["image_base_path"]

        super().__init__(cfg)

    # ── prepare_image ─────────────────────────────────────────────────────────

    def prepare_image(self, image_name: str) -> tuple[str | None, int, int]:
        """
        加载图像 → 缩放 → JPEG base64 data_url。
        Load image, resize it, and convert it to a JPEG base64 data URL.

        Returns:
            (data_url, orig_w, orig_h) 或 (None, 0, 0)
            (data_url, orig_w, orig_h) or (None, 0, 0)
        """
        import os
        path = os.path.join(self._image_base, image_name)
        try:
            with Image.open(path) as img:
                orig_w, orig_h = img.size
                if max(img.size) > self._max_image_size:
                    img.thumbnail(
                        (self._max_image_size, self._max_image_size),
                        Image.Resampling.LANCZOS,
                    )
                buf = BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=85)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                return f"data:image/jpeg;base64,{b64}", orig_w, orig_h
        except Exception as e:
            # print(f"  ❌ Image error [{image_name}]: {e}")
            return None, 0, 0

    # ── request_model ─────────────────────────────────────────────────────────

    def request_model(self, prompt_text: str, image_input: str) -> tuple[dict, dict]:
        """
        流式请求 OpenAI 兼容闭源模型，同时采集 TTFT / TPOT / E2E / Token 指标。
        Stream an OpenAI-compatible closed-model request while collecting TTFT / TPOT / E2E / token metrics.

        Args:
            prompt_text: 用户侧 context 文本
            prompt_text: user-side context text.
            image_input: base64 data_url

        Returns:
            (raw_pred_dict, metrics_dict)
        """
        sys_prompt = self.get_sys_prompt()
        client     = self._pool.get_client()

        for attempt in range(self._max_retries):
            try:
                t_start  = time.time()
                t_first  = None
                full_txt = ""
                usage    = None

                stream = client.chat.completions.create(
                    model=self._model_name,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text",      "text": prompt_text},
                                {"type": "image_url", "image_url": {"url": image_input}},
                            ],
                        },
                    ],
                    temperature=0.0,
                    stream=True,
                    stream_options={"include_usage": True},
                )

                for chunk in stream:
                    delta = (
                        chunk.choices[0].delta.content
                        if chunk.choices and chunk.choices[0].delta.content
                        else ""
                    )
                    if delta:
                        if t_first is None:
                            t_first = time.time()
                        full_txt += delta
                    if chunk.usage is not None:
                        usage = chunk.usage

                t_end = time.time()

                prompt_tokens     = usage.prompt_tokens     if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                ttft = round(t_first - t_start, 3) if t_first else 0.0
                e2e  = round(t_end   - t_start, 3)
                tpot = (
                    round((t_end - t_first) / max(completion_tokens, 1), 4)
                    if t_first and completion_tokens > 0 else 0.0
                )

                metrics = {
                    "e2e_sec":          e2e,
                    "ttft_sec":         ttft,
                    "tpot_sec":         tpot,
                    "prompt_tokens":    prompt_tokens,
                    "completion_tokens": completion_tokens,
                }

                raw_pred = json_repair.loads(full_txt)
                if not isinstance(raw_pred, dict):
                    raw_pred = {"action": {"action": "ERROR"}, "raw": str(raw_pred)}

                return raw_pred, metrics

            except Exception as e:
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return {"action": {"action": "ERROR"}, "error": str(e)}, {}
