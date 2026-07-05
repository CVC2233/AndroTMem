"""
utils.py — 工具函数
utils.py — utility functions

包含：
Includes:
  - context 构建（v1/v2/v3）
  - context construction for v1/v2/v3
  - 里程碑提取（统一格式）
  - milestone extraction in a unified format
  - 坐标反归一化（深拷贝，不修改原对象）
  - coordinate denormalization by deep copy without mutating the original object
"""

import json
import copy
from typing import Any


# ─── Context 构建 ─────────────────────────────────────────────────────────────
# ─── Context construction ────────────────────────────────────────────────────

def build_context_v1(instruction: str, history: list[dict]) -> str:
    """
    v1: 任务指令 + 最近 3 步的动作历史。
    v1: task instruction plus the last three action-history steps.
    history 中的坐标为像素坐标（与 checkpoint 恢复保持一致）。
    Coordinates in history are pixel coordinates, consistent with checkpoint recovery.
    """
    recent = history[-3:]
    return (
        f"Task: {instruction}\n"
        f"Action History (last {len(recent)} steps): {json.dumps(recent, ensure_ascii=False)}"
    )


def build_context_v2(instruction: str, last_summary: str) -> str:
    """v2: 任务指令 + 上一步的文字摘要。
    v2: task instruction plus the previous-step text summary.
    """
    return (
        f"Task: {instruction}\n"
        f"Last Step Summary: {last_summary}"
    )


def build_context_v3(
    instruction: str,
    milestones: list[dict],
    max_milestones: int = 50,
) -> str:
    """
    v3: 任务指令 + 累积里程碑列表。
    v3: task instruction plus the accumulated milestone list.

    milestones 格式（统一）:
    Unified milestones format:
      [{"content_en": "...", "description_en": "..."}, ...]

    同时输出 content_en 和 description_en，让模型获取完整的因果上下文。
    Include both content_en and description_en so the model has full causal context.
    """
    kept = milestones[-max_milestones:]
    if kept:
        lines = []
        for m in kept:
            c = m.get("content_en", "").strip()
            d = m.get("description_en", "").strip()
            if c:
                lines.append(f"- {c}" + (f" → {d}" if d else ""))
        ms_str = "\n".join(lines) if lines else "Start"
    else:
        ms_str = "Start"

    return (
        f"Task: {instruction}\n"
        f"Milestone Anchors:\n{ms_str}"
    )


# ─── 里程碑提取 ───────────────────────────────────────────────────────────────
# ─── Milestone extraction ────────────────────────────────────────────────────

def extract_milestones(pred: dict) -> list[dict]:
    """
    从统一格式的预测结果中提取里程碑列表。
    Extract the milestone list from a prediction in the unified format.

    统一输出格式:
    Unified output format:
      {"action": {...}, "milestones": [{"content_en": "...", "description_en": "..."}]}

    Args:
        pred: 模型原始预测 dict
        pred: raw prediction dict returned by the model.

    Returns:
        [{"content_en": "...", "description_en": "..."}, ...]
        解析失败或无里程碑时返回 []
        Return [] when parsing fails or no milestones exist.
    """
    if not isinstance(pred, dict):
        return []

    milestones = pred.get("milestones", [])
    if not isinstance(milestones, list):
        return []

    result = []
    for m in milestones:
        if isinstance(m, dict):
            result.append({
                "content_en":     str(m.get("content_en",     "")).strip(),
                "description_en": str(m.get("description_en", "")).strip(),
            })
    return result


# ─── 坐标反归一化 ─────────────────────────────────────────────────────────────
# ─── Coordinate denormalization ──────────────────────────────────────────────

def denormalize_prediction(
    pred: dict,
    orig_w: int,
    orig_h: int,
    coord_scale: int = 1000,
) -> dict:
    """
    将归一化坐标（0 ~ coord_scale）反映射为原图像素坐标。
    Map normalized coordinates (0 to coord_scale) back to original image pixels.

    ⚠️  始终对 pred 做深拷贝，绝不修改原对象。
    Always deep-copy pred and never mutate the original object.
        调用方可以在调用后继续安全使用 pred（归一化坐标）更新上下文。
        Callers can safely keep using pred with normalized coordinates for context updates.

    Args:
        pred:        模型原始预测 dict（含归一化坐标）
        pred:        raw model prediction dict with normalized coordinates.
        orig_w:      原图宽度（像素）
        orig_w:      original image width in pixels.
        orig_h:      原图高度（像素）
        orig_h:      original image height in pixels.
        coord_scale: 归一化坐标系上限，默认 1000
        coord_scale: upper bound of the normalized coordinate system, default 1000.

    Returns:
        深拷贝后、坐标已转换为像素的新 dict
        A new deep-copied dict whose coordinates have been converted to pixels.
    """
    pred = copy.deepcopy(pred)

    if not isinstance(pred, dict) or "action" not in pred:
        return pred

    act = pred["action"]

    def to_pixel(val: Any, total: int) -> int:
        try:
            if total <= 0:
                return 0
            px = int(round((float(val) / coord_scale) * (total - 1)))
            return max(0, min(px, total - 1))
        except Exception:
            return 0

    for field, dim in [("x", orig_w), ("y", orig_h), ("x_end", orig_w), ("y_end", orig_h)]:
        if field in act:
            act[field] = to_pixel(act[field], dim)

    return pred
