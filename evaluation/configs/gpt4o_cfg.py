"""
configs/gpt4o_cfg.py — GPT-4o（OpenAI 兼容闭源模型）配置
configs/gpt4o_cfg.py — GPT-4o closed-model configuration via an OpenAI-compatible API

output_filename 支持占位符：{version} {model_name}
output_filename supports placeholders: {version} {model_name}
"""

CONFIG = {
    # ── API ──────────────────────────────────────────────────────────────────
    "base_url":   "https://api.openai.com/v1",
    "api_keys":   [
        "sk-your-key-here",
    ],
    "keys_rpm":   100,           # 每个 key 的每分钟请求数上限
                                # Per-key requests-per-minute limit.
    "model_name": "gpt-4o",

    # ── I/O ──────────────────────────────────────────────────────────────────
    "input_file":       r"PATH/TO/EVALUATION_DATA.jsonl",
                        # Path to the input JSONL file. Each line should be one task.
    "output_dir":       r"PATH/TO/OUTPUT_DIR/gpt4o",
                        # Directory where prediction JSONL files will be written.
    "image_base_path":  r"PATH/TO/IMAGE_ROOT_DIR",
                        # Directory containing screenshot images referenced by image_name.
    # {version} / {model_name} 会在运行时由 BaseEvaluator.__init__ 自动替换
    # {version} / {model_name} are replaced by BaseEvaluator.__init__ at runtime.
    "output_filename":  "{model_name}_{version}.jsonl",

    # ── 运行参数 ──────────────────────────────────────────────────────────────
    # ── Runtime parameters ───────────────────────────────────────────────────
    "version":      "v1",        # 由 CLI --version 覆盖
                                # Overridden by CLI --version.
    "max_workers":  2,           # 建议 = len(api_keys) * 2
                                # Recommended value: len(api_keys) * 2.
    "max_retries":  3,
    "max_image_size": 1024,      # 图像缩放上限（像素）
                                # Maximum image resize dimension in pixels.

    # ── Prompt 与坐标 ─────────────────────────────────────────────────────────
    # ── Prompt and coordinates ───────────────────────────────────────────────
    "compact_prompt": True,      # API 模型使用精简 prompt 节省 token
                                # API models use compact prompts to save tokens.
    "coord_scale":    1000,

    # ── v3 专属 ───────────────────────────────────────────────────────────────
    # ── v3-specific settings ─────────────────────────────────────────────────
    "v3_max_milestones_in_prompt": 50,
}
