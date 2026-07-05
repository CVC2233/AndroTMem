"""
evaluate_predictions.py — 推理结果评测脚本
evaluate_predictions.py — evaluation script for inference outputs

用法：
Usage:
  python evaluate_predictions.py --pred PATH/TO/PREDICTIONS.jsonl --gt PATH/TO/GT.jsonl
"""

import argparse
import json
from collections import defaultdict


# ================= 判定逻辑 =================
# ================= Scoring Logic =================

def is_within_expanded_bbox(px, py, bbox, expansion_rate=0.14):
    """
    坐标落点判定：原始 BBox 向四周扩大指定比例。
    Point-hit check: expand the original bbox on all sides by the given ratio.
    """
    if not bbox or len(bbox) < 4:
        return False

    try:
        px = float(px)
        py = float(py)
        x_min, y_min, x_max, y_max = [float(v) for v in bbox[:4]]
    except Exception:
        return False

    width = abs(x_max - x_min)
    height = abs(y_max - y_min)
    new_x_min = x_min - expansion_rate * width
    new_x_max = x_max + expansion_rate * width
    new_y_min = y_min - expansion_rate * height
    new_y_max = y_max + expansion_rate * height
    return new_x_min <= px <= new_x_max and new_y_min <= py <= new_y_max


def normalize_action_type(action_type: str) -> str:
    """
    归一化常见动作别名。
    Normalize common action aliases.
    """
    action_type = str(action_type).lower().strip()
    aliases = {
        "click": "tap",
        "input_text": "text",
        "type": "text",
        "terminate": "finish",
        "finish": "finish",
        "finish_task": "finish",
    }
    return aliases.get(action_type, action_type)


def calculate_step_score(pred_action, gt_step):
    """
    单步得分计算。
    Calculate the score for one step.
    """
    if not pred_action:
        return 0.0

    # 缺图 AUTO_PASS：推理脚本已明确标记为自动判对。
    # Missing-image AUTO_PASS: the inference script explicitly credits it as correct.
    if isinstance(pred_action, dict) and pred_action.get("_credited_as_correct") is True:
        return 1.0

    # 防御：如果 pred_action 是字符串，就把它当成 action 类型。
    # Defensive fallback: if pred_action is a string, treat it as the action type.
    if isinstance(pred_action, str):
        pred_action = {"action": pred_action}

    # 防御：如果是别的类型，直接 0。
    # Defensive fallback: unsupported prediction types score 0.
    if not isinstance(pred_action, dict):
        return 0.0

    gt_action_form = gt_step.get("actionForm", {})

    # 归一化预测动作类型。
    # Normalize predicted action type.
    p_type = normalize_action_type(pred_action.get("action", ""))
    g_type = normalize_action_type(gt_action_form.get("action", ""))

    # 1. 类型不匹配。
    # 1. Action type mismatch.
    if p_type != g_type:
        return 0.0

    # 2. 文本输入。
    # 2. Text input.
    if g_type in ["text", "need_feedback"]:
        pv = str(pred_action.get("value", "")).strip().lower()
        gv = str(gt_action_form.get("value", "")).strip().lower()
        return 1.0 if pv == gv else 0.0

    # 3. 点击/长按：坐标落在扩展 BBox 内。
    # 3. Tap/long press: point must fall within the expanded bbox.
    if g_type in ["tap", "long_press"]:
        px, py = pred_action.get("x"), pred_action.get("y")
        bbox = gt_action_form.get("bbox", [])
        if px is not None and py is not None and bbox:
            return 1.0 if is_within_expanded_bbox(px, py, bbox, 0.14) else 0.0
        return 0.0

    # 4. 滑动：只判定方向。
    # 4. Swipe: compare direction only.
    if g_type in ["swipe", "swipe_two_points"]:
        pd = str(pred_action.get("direction", "")).strip().lower()
        gd = str(gt_action_form.get("direction", "")).strip().lower()
        return 1.0 if pd == gd and pd != "" else 0.0

    # 5. 无参动作：类型匹配即正确。
    # 5. Parameter-free actions: matching action type is enough.
    if g_type in ["open_app", "wait", "finish", "home", "back", "capture_screen"]:
        return 1.0

    return 0.0


def load_predictions(pred_file):
    """
    加载预测文件，并保留 AUTO_PASS / 执行状态统计信息。
    Load predictions while preserving AUTO_PASS and execution-status statistics.
    """
    pred_data = defaultdict(dict)
    stats = {
        "records": 0,
        "execution_success": 0,
        "execution_error": 0,
        "auto_pass": 0,
        "parse_errors": 0,
    }

    with open(pred_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                tid = str(record["task_id"])
                sid = str(record["step_index"])
                stats["records"] += 1

                execution_status = record.get("execution_status")
                if execution_status == "success":
                    stats["execution_success"] += 1
                elif execution_status == "error":
                    stats["execution_error"] += 1

                inner = record.get("prediction", {})
                act_obj = inner.get("action", inner) if isinstance(inner, dict) else {"action": "ERROR"}

                if record.get("credited_as_correct") is True:
                    stats["auto_pass"] += 1
                    act_obj = dict(act_obj) if isinstance(act_obj, dict) else {"action": "AUTO_PASS"}
                    act_obj["_credited_as_correct"] = True
                    act_obj["_execution_status"] = execution_status
                    act_obj["_execution_message"] = record.get("execution_message", "")

                pred_data[tid][sid] = {
                    "action": act_obj,
                    "metrics": record.get("metrics", {}) if isinstance(record.get("metrics", {}), dict) else {},
                }
            except Exception:
                stats["parse_errors"] += 1

    return pred_data, stats


def empty_metrics_stats():
    """
    创建 token 和时间统计容器。
    Create a token/time metrics statistics container.
    """
    return {
        "metrics_records": 0,
        "e2e_sec_sum": 0.0,
        "ttft_sec_sum": 0.0,
        "tpot_sec_sum": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }


def update_metrics_stats(target, metrics):
    """
    累计单条预测的 token 和时间指标。
    Accumulate token/time metrics from one prediction record.
    """
    if not isinstance(metrics, dict) or not metrics:
        return

    try:
        target["metrics_records"] += 1
        target["e2e_sec_sum"] += float(metrics.get("e2e_sec", 0) or 0)
        target["ttft_sec_sum"] += float(metrics.get("ttft_sec", 0) or 0)
        target["tpot_sec_sum"] += float(metrics.get("tpot_sec", 0) or 0)
        target["prompt_tokens"] += int(metrics.get("prompt_tokens", 0) or 0)
        target["completion_tokens"] += int(metrics.get("completion_tokens", 0) or 0)
    except Exception:
        return


def load_ground_truth(gt_file):
    """
    加载 GT 文件，支持 JSON 数组或 JSONL。
    Load the GT file, supporting either a JSON array or JSONL.
    """
    with open(gt_file, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return []

    if content.startswith("["):
        return json.loads(content)

    tasks = []
    for line in content.splitlines():
        if line.strip():
            tasks.append(json.loads(line))
    return tasks


def get_step_uid(step):
    """
    获取 step 的主 ID，找不到显式 ID 时退回 step_index。
    Get the primary step ID, falling back to step_index when no explicit ID exists.
    """
    for key in ("step_id", "id", "uuid", "uid", "node_id"):
        value = step.get(key)
        if value is not None:
            return str(value)
    return str(step.get("step_index"))


def iter_step_aliases(step):
    """
    收集可用于 links.source 匹配的 step 别名。
    Collect step aliases that can be matched by links.source.
    """
    aliases = {get_step_uid(step), str(step.get("step_index"))}
    for key in ("step_id", "id", "uuid", "uid", "node_id"):
        value = step.get(key)
        if value is not None:
            aliases.add(str(value))

    for status in step.get("extra_info", {}).get("status", []):
        for key in ("id", "uuid", "status_id", "anchor_id", "node_id"):
            value = status.get(key)
            if value is not None:
                aliases.add(str(value))

    return aliases


def build_step_indexes(steps):
    """
    构建 step ID/别名索引。
    Build indexes for step IDs and aliases.
    """
    uid_to_step = {}
    index_to_uid = {}
    for step in steps:
        primary_uid = get_step_uid(step)
        index_to_uid[str(step.get("step_index"))] = primary_uid
        for alias in iter_step_aliases(step):
            uid_to_step[alias] = step
    return uid_to_step, index_to_uid


def is_finish_anchor(step):
    """
    判断一个 step 是否是最终完成锚点。
    Decide whether a step is the final completion anchor.
    """
    for status in step.get("extra_info", {}).get("status", []):
        text = (str(status.get("content", "")) + " " + str(status.get("content_en", ""))).lower()
        if "finish" in text or "[finish]" in text:
            return True

    action = normalize_action_type(step.get("actionForm", {}).get("action", ""))
    return action == "finish"


def find_final_anchor_step(steps):
    """
    查找最终完成锚点；找不到时退回最后一步。
    Find the final completion anchor; fall back to the last step when absent.
    """
    for step in reversed(steps):
        if is_finish_anchor(step):
            return step
    return steps[-1] if steps else None


def get_step_links(step):
    """
    读取 step 上的 links，兼容顶层 links 和 extra_info.links。
    Read links from a step, supporting top-level links and extra_info.links.
    """
    links = step.get("links")
    if links is None:
        links = step.get("extra_info", {}).get("links", [])
    return links if isinstance(links, list) else []


def collect_required_step_uids(final_uid, uid_to_step):
    """
    从最终锚点递归收集关键依赖 step。
    Recursively collect critical dependency steps from the final anchor.
    """
    required = set()
    missing_sources = set()
    stack = [str(final_uid)]

    while stack:
        uid = str(stack.pop())
        step = uid_to_step.get(uid)
        if not step:
            missing_sources.add(uid)
            continue

        canonical_uid = get_step_uid(step)
        if canonical_uid in required:
            continue
        required.add(canonical_uid)

        for link in get_step_links(step):
            if link.get("is_critical") is not True:
                continue
            source = link.get("source")
            if source is None:
                continue
            source_uid = str(source)
            source_step = uid_to_step.get(source_uid)
            if source_step is None:
                missing_sources.add(source_uid)
                continue
            source_uid = get_step_uid(source_step)
            stack.append(source_uid)

    return required, missing_sources


def calculate_task_tcr_success(steps, step_scores):
    """
    任务级 TCR：最终完成锚点及其递归关键依赖全部正确。
    Task-level TCR: final anchor and recursive critical dependencies must all be correct.
    """
    if not steps:
        return False, set(), set(), set()

    uid_to_step, _ = build_step_indexes(steps)
    final_step = find_final_anchor_step(steps)
    final_uid = get_step_uid(final_step)
    required_uids, missing_sources = collect_required_step_uids(final_uid, uid_to_step)

    failed_required = set(missing_sources)
    for uid in required_uids:
        step = uid_to_step.get(uid)
        if not step:
            failed_required.add(uid)
            continue

        sid = str(step.get("step_index"))
        if step_scores.get(sid, 0.0) < 1.0:
            failed_required.add(uid)

    return len(failed_required) == 0, required_uids, failed_required, missing_sources


def create_group_stats():
    """
    创建 AMS/TCR 分组统计容器。
    Create a grouped statistics container for AMS/TCR.
    """
    stats = {
        "tasks": 0,
        "tcr_success": 0,
        "steps": 0,
        "ams_sum": 0.0,
        "required_steps": 0,
        "failed_required_steps": 0,
        "missing_link_sources": 0,
    }
    stats.update(empty_metrics_stats())
    return stats


def update_group_stats(
    group_dict,
    key,
    step_count,
    task_ams_sum,
    tcr_ok,
    required_uids,
    failed_required,
    missing_sources,
):
    """
    更新一个 AMS/TCR 分组。
    Update one AMS/TCR group.
    """
    target = group_dict[key]
    target["tasks"] += 1
    if tcr_ok:
        target["tcr_success"] += 1
    target["steps"] += step_count
    target["ams_sum"] += task_ams_sum
    target["required_steps"] += len(required_uids)
    target["failed_required_steps"] += len(failed_required)
    target["missing_link_sources"] += len(missing_sources)


def merge_metrics_stats(target, source):
    """
    合并 token 和时间统计。
    Merge token/time metrics statistics.
    """
    for key in empty_metrics_stats():
        target[key] += source.get(key, 0)


def print_group_table(title, group_dict, sort_key=None, show_title=True):
    """
    打印分组统计表。
    Print a grouped statistics table.
    """
    if show_title:
        print("\n" + "=" * 25 + f" {title} " + "=" * 25)
    header = (
        f"{'Group':<25} | {'Tasks':<6} | {'TCR (%)':<8} | {'AMS':<8} | "
        f"{'AvgE2E':<8} | {'AvgInTok':<8} | {'AvgOutTok':<9} | {'FailedReq':<9} | {'MissingSrc':<10}"
    )
    print(header)
    print("-" * len(header))

    keys = list(group_dict.keys())
    if sort_key:
        keys = sorted(keys, key=sort_key)
    else:
        keys = sorted(keys, key=lambda x: group_dict[x]["tasks"], reverse=True)

    for key in keys:
        value = group_dict[key]
        tcr = (value["tcr_success"] / value["tasks"]) * 100 if value["tasks"] else 0
        ams = (value["ams_sum"] / value["steps"]) if value["steps"] else 0
        metric_count = value["metrics_records"]
        avg_e2e = (value["e2e_sec_sum"] / metric_count) if metric_count else 0
        avg_prompt_tokens = (value["prompt_tokens"] / metric_count) if metric_count else 0
        avg_completion_tokens = (value["completion_tokens"] / metric_count) if metric_count else 0
        print(
            f"{str(key)[:25]:<25} | "
            f"{value['tasks']:<6} | "
            f"{tcr:>8.2f} | "
            f"{ams:>8.4f} | "
            f"{avg_e2e:>8.3f} | "
            f"{avg_prompt_tokens:>8.1f} | "
            f"{avg_completion_tokens:>9.1f} | "
            f"{value['failed_required_steps']:>9} | "
            f"{value['missing_link_sources']:>10}"
        )


def evaluate_agent(pred_file, gt_file):
    """
    执行完整评测并打印报告。
    Run the full evaluation and print the report.
    """
    print(f"\n>>> Loading predictions: {pred_file}")
    pred_data, pred_stats = load_predictions(pred_file)
    evaluated_tids = set(pred_data.keys())

    print(f">>> Prediction records:        {pred_stats['records']}")
    print(f">>> Prediction parse errors:   {pred_stats['parse_errors']}")
    print(f">>> Execution success records: {pred_stats['execution_success']}")
    print(f">>> Execution error records:   {pred_stats['execution_error']}")
    print(f">>> AUTO_PASS records:         {pred_stats['auto_pass']}")
    print(f">>> Evaluated task IDs:        {len(evaluated_tids)}")

    print(f">>> Loading ground truth: {gt_file}")
    gt_tasks = load_ground_truth(gt_file)

    g_tasks = 0
    g_steps = 0
    g_ams_sum = 0.0
    g_tcr_success = 0
    g_required_steps = 0
    g_failed_required_steps = 0
    g_missing_link_sources = 0
    g_metrics = empty_metrics_stats()
    intent_groups = defaultdict(create_group_stats)
    length_groups = defaultdict(create_group_stats)
    length_intent_groups = defaultdict(lambda: defaultdict(create_group_stats))

    print(">>> Evaluating tasks that appear in the prediction file...")

    for task in gt_tasks:
        tid = str(task["task_id"])
        if tid not in evaluated_tids:
            continue

        steps = task.get("steps", [])
        if not steps:
            continue

        intent = task.get("primary_intent", "Unknown")
        step_count = len(steps)
        range_start = (step_count // 10) * 10
        length_range = f"{range_start}-{range_start + 9}"
        step_scores = {}
        task_ams_sum = 0.0
        task_metrics = empty_metrics_stats()

        for gt_step in steps:
            sid = str(gt_step["step_index"])
            pred_record = pred_data.get(tid, {}).get(sid, {})
            pred_action = pred_record.get("action") if isinstance(pred_record, dict) else pred_record
            pred_metrics = pred_record.get("metrics", {}) if isinstance(pred_record, dict) else {}
            score = calculate_step_score(pred_action, gt_step)
            step_scores[sid] = score

            update_metrics_stats(task_metrics, pred_metrics)
            update_metrics_stats(g_metrics, pred_metrics)
            task_ams_sum += score
            g_ams_sum += score
            g_steps += 1

        tcr_ok, required_uids, failed_required, missing_sources = calculate_task_tcr_success(steps, step_scores)

        g_tasks += 1
        if tcr_ok:
            g_tcr_success += 1
        g_required_steps += len(required_uids)
        g_failed_required_steps += len(failed_required)
        g_missing_link_sources += len(missing_sources)

        group_args = (
            step_count,
            task_ams_sum,
            tcr_ok,
            required_uids,
            failed_required,
            missing_sources,
        )
        update_group_stats(intent_groups, intent, *group_args)
        update_group_stats(length_groups, length_range, *group_args)
        update_group_stats(length_intent_groups[length_range], intent, *group_args)
        merge_metrics_stats(intent_groups[intent], task_metrics)
        merge_metrics_stats(length_groups[length_range], task_metrics)
        merge_metrics_stats(length_intent_groups[length_range][intent], task_metrics)

    print("\n" + "=" * 30 + " Global Summary " + "=" * 30)
    print(f"Evaluated Tasks:       {g_tasks}")
    print(f"Evaluated Steps:       {g_steps}")
    print(f"AMS (Action Match):    {(g_ams_sum / g_steps) if g_steps else 0:.4f}")
    print(f"TCR (Task Completion): {(g_tcr_success / g_tasks) * 100 if g_tasks else 0:.2f}%")
    print(f"TCR Success Tasks:     {g_tcr_success}")
    print(f"Required TCR Steps:    {g_required_steps}")
    print(f"Failed Required Steps: {g_failed_required_steps}")
    print(f"Missing Link Sources:  {g_missing_link_sources}")
    print(f"Metrics Records:       {g_metrics['metrics_records']}")
    print(f"Total Prompt Tokens:   {g_metrics['prompt_tokens']}")
    print(f"Total Completion Tok.: {g_metrics['completion_tokens']}")
    print(f"Avg Prompt Tokens:     {(g_metrics['prompt_tokens'] / g_metrics['metrics_records']) if g_metrics['metrics_records'] else 0:.1f}")
    print(f"Avg Completion Tokens: {(g_metrics['completion_tokens'] / g_metrics['metrics_records']) if g_metrics['metrics_records'] else 0:.1f}")
    print(f"Avg E2E Time (sec):    {(g_metrics['e2e_sec_sum'] / g_metrics['metrics_records']) if g_metrics['metrics_records'] else 0:.3f}")
    print(f"Avg TTFT (sec):        {(g_metrics['ttft_sec_sum'] / g_metrics['metrics_records']) if g_metrics['metrics_records'] else 0:.3f}")
    print(f"Avg TPOT (sec):        {(g_metrics['tpot_sec_sum'] / g_metrics['metrics_records']) if g_metrics['metrics_records'] else 0:.4f}")

    print_group_table("By Intent (primary_intent)", intent_groups)
    print_group_table(
        "By Task Length",
        length_groups,
        sort_key=lambda x: int(str(x).split("-")[0]),
    )

    print("\n" + "=" * 20 + " Task Length x Intent " + "=" * 20)
    sorted_ranges = sorted(length_groups.keys(), key=lambda x: int(str(x).split("-")[0]))
    global_intent_order = sorted(intent_groups.keys(), key=lambda x: intent_groups[x]["tasks"], reverse=True)
    for length_range in sorted_ranges:
        print("\n" + "-" * 10 + f" Steps Range: {length_range} " + "-" * 10)
        sub = length_intent_groups.get(length_range, {})
        ordered_sub = {}
        for intent in global_intent_order:
            if intent in sub:
                ordered_sub[intent] = sub[intent]
        for intent, value in sub.items():
            if intent not in ordered_sub:
                ordered_sub[intent] = value
        print_group_table("Task Length x Intent", ordered_sub, show_title=False)


def parse_args():
    """
    解析命令行参数。
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Evaluate Mobile GUI Agent prediction JSONL files.")
    parser.add_argument("--pred", required=True, help="Path to prediction JSONL file.")
    parser.add_argument("--gt", required=True, help="Path to ground-truth JSON or JSONL file.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate_agent(args.pred, args.gt)
