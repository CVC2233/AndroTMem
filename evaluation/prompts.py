"""
prompts.py — 统一 Prompt 定义模块
prompts.py — unified prompt definition module

支持两种风格：
Supports two styles:
  compact=True   API 闭源模型（GPT-4o 等），精简以节省 token
  compact=True   closed API models such as GPT-4o; compact to save tokens
  compact=False  本地开源模型（Qwen2.5-VL 等），完整以提升理解
  compact=False  local open-source models such as Qwen2.5-VL; full prompt to improve understanding
"""

# ─── I. Action Space ──────────────────────────────────────────────────────────

_ACTION_SPACE_COMPACT = (
    "I. Action Space\n"
    'Allowed actions: [{"label":"Tap","value":"tap"},{"label":"Input Text","value":"text"},'
    '{"label":"Need Feedback","value":"need_feedback"},{"label":"Long Press","value":"long_press"},'
    '{"label":"Swipe","value":"swipe"},{"label":"Swipe (Two Points)","value":"swipe_two_points"},'
    '{"label":"Wait","value":"wait"},{"label":"Finish","value":"FINISH"},'
    '{"label":"Open App","value":"open_app"},{"label":"Capture Screen","value":"capture_screen"},'
    '{"label":"Home","value":"home"},{"label":"Back","value":"back"}]'
)

_ACTION_SPACE_FULL = """\
I. Action Space (use only the "value" field exactly as listed)
[
  { "label": "Tap",               "value": "tap" },
  { "label": "Input Text",        "value": "text" },
  { "label": "Need Feedback",     "value": "need_feedback" },
  { "label": "Long Press",        "value": "long_press" },
  { "label": "Swipe",             "value": "swipe" },
  { "label": "Swipe (Two Points)","value": "swipe_two_points" },
  { "label": "Wait",              "value": "wait" },
  { "label": "Finish",            "value": "FINISH" },
  { "label": "Open App",          "value": "open_app" },
  { "label": "Capture Screen",    "value": "capture_screen" },
  { "label": "Home",              "value": "home" },
  { "label": "Back",              "value": "back" }
]
Notes:
- Output exactly ONE action per response.
- Use "FINISH" only when the task is fully complete.
- If the screenshot is insufficient to decide, use "need_feedback"."""


# ─── II. Field Requirements & Decision Principles ────────────────────────────

def _decision_principles(coord_scale: int, compact: bool) -> str:
    if compact:
        return (
            "II. Field Requirements\n"
            f"1. action.action: String. Must be in Action Space.\n"
            f"2. action.x,y,x_end,y_end: Normalized coords 0–{coord_scale}. "
            f"(0,0)=Top-Left, ({coord_scale},{coord_scale})=Bottom-Right. "
            f"tap/long_press→(x,y); swipe_two_points→start(x,y)+end(x_end,y_end); unused=0.\n"
            f"3. action.value: Input text | feedback description | app name. Empty otherwise.\n"
            f"4. action.direction: \"up\"|\"down\"|\"left\"|\"right\" (swipe only).\n"
            f"5. action.distance: \"long\"|\"medium\"|\"short\" (swipe only).\n"
            "III. Decision Principles\n"
            "Visual Evidence: Only act on what you see. Use \"wait\" if loading.\n"
            f"Precision: Target UI element center. Use 0–{coord_scale} scale.\n"
            "Step-by-Step: ONE action per response."
        )
    else:
        return (
            "II. Field Requirements\n"
            "1. action.action — Required String. One of the values in Action Space.\n"
            f"2. action.x, action.y — Integer. Normalized 0–{coord_scale}. "
            f"(0,0)=Top-Left, ({coord_scale},{coord_scale})=Bottom-Right.\n"
            "   · tap / long_press: center of target element.\n"
            "   · swipe_two_points: start point. Set 0 for all other actions.\n"
            "3. action.value — String.\n"
            "   · text: exact text to enter.\n"
            "   · need_feedback: describe what info you need.\n"
            "   · open_app: app identifier from the allowed list.\n"
            "   · other actions: empty string \"\".\n"
            "4. action.direction — \"up\"|\"down\"|\"left\"|\"right\". Swipe only. \"\" otherwise.\n"
            "5. action.distance — \"long\"|\"medium\"|\"short\". Swipe only. \"\" otherwise.\n"
            "6. action.x_end, action.y_end — End coords. swipe_two_points only. 0 otherwise.\n"
            "III. Decision Principles\n"
            "· Visual Evidence: Only act on what you see. \"wait\" if page is loading.\n"
            "· Progress Check: Compare current screen with last history step; advance if prior action succeeded.\n"
            "· No Hallucination: Never output coordinates for elements not visible.\n"
            "· Precision: Aim at the center of the target UI element.\n"
            "· Step-by-Step: Output exactly ONE action per response."
        )


# ─── Version-specific sections ────────────────────────────────────────────────

_SUMMARY_SECTION = (
    "IV. Step Summary\n"
    "Output a concise one-sentence English summary of the current step's outcome (summary_en)."
)

_MILESTONE_SECTION = """\
IV. Milestone Anchors
Milestone anchors are sparse, high-value semantic summaries of key states or events \
that causally affect subsequent steps.

Categories:
  [subgoal]      Mid-term goal achieved
  [state_change] App state or mode switched
  [dependency]   Prerequisite established for future steps
  [exception]    Error or unexpected situation handled
  [context_info] Key parameter or user feedback captured
  [finish]       Overall task goal achieved

For each step, output a list of milestone anchors ([] if no significant event occurred).
Each anchor must contain:
  content_en    = "[Category] Concise event description"
  description_en = "Why this is vital and how it constrains next steps" """


# ─── V. Output Format ─────────────────────────────────────────────────────────

def _output_format(version: str) -> str:
    action_schema = (
        '"action": {'
        '"action": "...", "x": 0, "y": 0, "value": "", '
        '"x_end": 0, "y_end": 0, "direction": "", "distance": ""'
        "}"
    )
    base = f"V. Output Format\nReturn exactly one JSON object (no markdown, no extra text):\n"

    if version == "v1":
        return base + "{" + action_schema + "}"
    elif version == "v2":
        return base + "{" + action_schema + ', "summary_en": "..."}'
    else:  # v3
        milestone_schema = (
            '"milestones": ['
            '{"content_en": "[Category] ...", "description_en": "..."}'
            "]"
        )
        return base + "{" + action_schema + ", " + milestone_schema + "}"


# ─── Public API ───────────────────────────────────────────────────────────────

def get_sys_prompt(version: str, coord_scale: int = 1000, compact: bool = False) -> str:
    """
    生成系统 Prompt。
    Generate the system prompt.

    Args:
        version:     "v1" | "v2" | "v3"
        coord_scale: 归一化坐标系上限，默认 1000
        coord_scale: upper bound of the normalized coordinate system, default 1000.
        compact:     True=精简风格（API模型省 token），False=完整风格（本地模型）
        compact:     True for compact API-model prompts, False for full local-model prompts.

    Returns:
        完整的 system prompt 字符串
        The complete system prompt string.
    """
    assert version in ("v1", "v2", "v3"), f"version 必须为 v1/v2/v3，实际: {version}"

    action_space = _ACTION_SPACE_COMPACT if compact else _ACTION_SPACE_FULL
    principles   = _decision_principles(coord_scale, compact)
    fmt          = _output_format(version)

    if version == "v1":
        sections = [action_space, principles, fmt]
    elif version == "v2":
        sections = [action_space, principles, _SUMMARY_SECTION, fmt]
    else:
        sections = [action_space, principles, _MILESTONE_SECTION, fmt]

    return "Mobile GUI Assistant.\n" + "\n\n".join(sections)
