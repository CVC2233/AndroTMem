"""
configs/qwen_cfg.py — Qwen2.5-VL（本地 HF 开源模型）配置
configs/qwen_cfg.py — Qwen2.5-VL local open-source HF model configuration
"""

CONFIG = {
    # ── HF 模型 ───────────────────────────────────────────────────────────────
    # ── HF model ─────────────────────────────────────────────────────────────
    "hf_model_id": "Qwen/Qwen2.5-VL-7B-Instruct",

    # ── I/O ──────────────────────────────────────────────────────────────────
    "input_file":      r"PATH/TO/EVALUATION_DATA.jsonl",
                       # Path to the input JSONL file. Each line should be one task.
    "output_dir":      r"PATH/TO/OUTPUT_DIR/qwen_2_5_vl",
                       # Directory where prediction JSONL files will be written.
    "image_base_path": r"PATH/TO/IMAGE_ROOT_DIR",
                       # Directory containing screenshot images referenced by image_name.
    "output_filename": "qwen-2.5-vl_{version}.jsonl",

    # ── 运行参数 ──────────────────────────────────────────────────────────────
    # ── Runtime parameters ───────────────────────────────────────────────────
    "version":       "v1",       # 由 CLI --version 覆盖
                                # Overridden by CLI --version.
    "max_workers":   1,          # 单卡推理必须为 1，并发 generate 易 OOM
                                # Single-GPU inference must use 1 worker; concurrent generate can OOM.
    "max_retries":   3,
    "retry_backoff": 2,          # 指数退避基数（秒）
                                # Exponential backoff base in seconds.
    "max_new_tokens": 512,
    "temperature":   0.0,

    # ── 模型加载 ──────────────────────────────────────────────────────────────
    # ── Model loading ────────────────────────────────────────────────────────
    # "bfloat16"（A100/H100）/ "float16"（消费级显卡）/ "float32"（CPU fallback）
    # "bfloat16" for A100/H100, "float16" for consumer GPUs, "float32" for CPU fallback.
    "dtype":          "float16",
    "use_flash_attn": False,     # 需要安装 flash-attn 才能开启
                                # Enable only after flash-attn is installed.
    "max_image_pixels": 5600 * 28 * 28,

    # ── Prompt 与坐标 ─────────────────────────────────────────────────────────
    # ── Prompt and coordinates ───────────────────────────────────────────────
    "compact_prompt": False,     # 本地模型使用完整 prompt
                                # Local models use the full prompt.
    "coord_scale":    1000,

    # ── v3 专属 ───────────────────────────────────────────────────────────────
    # ── v3-specific settings ─────────────────────────────────────────────────
    "v3_max_milestones_in_prompt": 50,
}
