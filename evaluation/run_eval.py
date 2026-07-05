"""
run_eval.py — 统一评估入口
run_eval.py — unified evaluation entry point

用法：
Usage:
  python run_eval.py --backend gpt4o --version v1
  python run_eval.py --backend qwen  --version v3
  python run_eval.py --backend gpt4o --version v2 --workers 4 --input /path/to/data.jsonl
"""

import argparse
import sys
import os
import jsonlines
import concurrent.futures
from tqdm import tqdm

# 确保 eval_framework 根目录在 import 路径中
# Ensure the eval_framework root directory is on the import path.
sys.path.insert(0, os.path.dirname(__file__))

from backends import get_backend


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Mobile GUI Agent 统一评估框架",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--backend", required=True,
        choices=["gpt4o", "qwen"],
        help="评估后端：gpt4o（OpenAI 兼容闭源模型）或 qwen（本地 HF 开源模型）",
    )
    parser.add_argument(
        "--version", required=True,
        choices=["v1", "v2", "v3"],
        help=(
            "Prompt 版本：\n"
            "  v1  action only\n"
            "  v2  action + summary_en\n"
            "  v3  action + milestones"
        ),
    )
    # 可选覆盖项（优先级高于 config 文件）
    # Optional overrides with higher priority than config files.
    parser.add_argument("--input",   default=None, help="覆盖 input_file 路径")
    parser.add_argument("--output",  default=None, help="覆盖 output_dir 路径")
    parser.add_argument("--workers", default=None, type=int, help="覆盖 max_workers")
    return parser.parse_args()


# ─── 加载配置 ──────────────────────────────────────────────────────────────────
# ─── Load configuration ───────────────────────────────────────────────────────

def load_config(backend: str) -> dict:
    if backend == "gpt4o":
        from configs.gpt4o_cfg import CONFIG
    elif backend == "qwen":
        from configs.qwen_cfg import CONFIG
    else:
        raise ValueError(f"Unknown backend: {backend}")
    return dict(CONFIG)  # 返回副本，避免修改模块级常量
                         # Return a copy to avoid mutating module-level constants.


# ─── 主函数 ────────────────────────────────────────────────────────────────────
# ─── Main function ────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    # 1. 加载 & 合并配置
    # 1. Load and merge configuration.
    cfg = load_config(args.backend)
    cfg["version"] = args.version

    if args.input:
        cfg["input_file"] = args.input
    if args.output:
        cfg["output_dir"] = args.output
    if args.workers is not None:
        cfg["max_workers"] = args.workers

    # 2. 创建 evaluator（模型加载在此发生）
    # 2. Create the evaluator; model loading happens here.
    print(f"\n{'='*55}")
    print(f"  Backend : {args.backend}")
    print(f"  Version : {args.version}")
    print(f"  Input   : {cfg['input_file']}")
    print(f"  Workers : {cfg['max_workers']}")
    print(f"{'='*55}\n")

    evaluator = get_backend(args.backend, cfg)
    print(f"Output  : {evaluator.output_path}\n")

    # 3. 读取输入数据
    # 3. Read input data.
    if not os.path.exists(cfg["input_file"]):
        print(f"❌ Input file not found: {cfg['input_file']}")
        sys.exit(1)

    with jsonlines.open(cfg["input_file"]) as reader:
        all_tasks = list(reader)
    print(f"Loaded {len(all_tasks)} tasks. Starting evaluation...\n")

    # 4. 并发评估
    # 4. Run evaluation concurrently.
    max_workers = cfg["max_workers"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(tqdm(
            executor.map(evaluator.eval_task, all_tasks),
            total=len(all_tasks),
            desc=f"{args.backend}-{args.version}",
        ))

    print(f"\n✅ Done. Results: {evaluator.output_path}")


if __name__ == "__main__":
    main()
