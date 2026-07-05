import json
import glob
import os

# ── 配置区 ──────────────────────────────────────────────
INPUT_JSON_PATTERN = r"D:\Data\process_class\json_new_swipe_two_points_sam2_class_id_link_en_new\*.json"
OUTPUT_JSONL_PATH  = r"D:\Data\process_class\merged_final.jsonl"
SKIP_SUFFIX        = "_resize.json"
# ────────────────────────────────────────────────────────

print("📂 正在合并 JSON 文件...")
os.makedirs(os.path.dirname(OUTPUT_JSONL_PATH), exist_ok=True)

stats = {
    "files"   : 0,
    "records" : 0,
    "skipped" : 0,
    "errors"  : 0,
}

with open(OUTPUT_JSONL_PATH, "w", encoding="utf-8") as out_f:
    for file_path in sorted(glob.glob(INPUT_JSON_PATTERN)):
        if os.path.basename(file_path).endswith(SKIP_SUFFIX):
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                print(f"⚠️  跳过非列表结构文件: {file_path}")
                stats["skipped"] += 1
                continue

            for record in data:
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                stats["records"] += 1

            stats["files"] += 1
            print(f"  ✅ {os.path.basename(file_path)}（{len(data)} 条）")

        except json.JSONDecodeError as e:
            print(f"  ❌ 解析失败: {file_path} → {e}")
            stats["errors"] += 1
        except Exception as e:
            print(f"  ❌ 处理异常: {file_path} → {e}")
            stats["errors"] += 1

print(f"""
{'='*50}
✅ 合并完成
{'='*50}
  处理文件数:  {stats['files']}
  跳过文件数:  {stats['skipped']}
  失败文件数:  {stats['errors']}
  总记录数:    {stats['records']}
  输出文件:    {OUTPUT_JSONL_PATH}
""")
