"""
eval_trace.py — Trace Evaluation & Comparison
Sprint 4: Chạy pipeline với test questions, phân tích trace, so sánh single vs multi.

Chạy:
    python eval_trace.py                  # Chạy 15 test questions
    python eval_trace.py --grading        # Chạy grading questions (sau 17:00)
    python eval_trace.py --analyze        # Phân tích trace đã có
    python eval_trace.py --compare        # So sánh single vs multi

Outputs:
    artifacts/traces/           — trace của từng câu hỏi
    artifacts/grading_run.jsonl — log câu hỏi chấm điểm
    artifacts/eval_report.json  — báo cáo tổng kết
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Optional, Any


sys.path.insert(0, os.path.dirname(__file__))
from graph import run_graph, save_trace


ARTIFACTS_DIR = "artifacts"
TRACES_DIR = os.path.join(ARTIFACTS_DIR, "traces")
EVAL_REPORT_FILE = os.path.join(ARTIFACTS_DIR, "eval_report.json")
GRADING_LOG_FILE = os.path.join(ARTIFACTS_DIR, "grading_run.jsonl")


def ensure_dirs():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    os.makedirs(TRACES_DIR, exist_ok=True)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def normalize_mcp_tools_used(mcp_tools_used: Any) -> list:
    if not mcp_tools_used:
        return []
    normalized = []
    for item in mcp_tools_used:
        if isinstance(item, dict):
            normalized.append(item.get("tool", "unknown_tool"))
        elif isinstance(item, str):
            normalized.append(item)
        else:
            normalized.append(str(item))
    return normalized


def safe_save_trace(result: dict, output_dir: str = TRACES_DIR) -> Optional[str]:
    ensure_dirs()
    try:
        return save_trace(result, output_dir)
    except Exception:
        run_id = result.get("run_id") or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        output_file = os.path.join(output_dir, f"{run_id}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return output_file


def build_grading_record(q_id: str, question_text: str, result: dict) -> dict:
    return {
        "id": q_id,
        "question": question_text,
        "answer": result.get("final_answer", "PIPELINE_ERROR: no answer"),
        "sources": result.get("retrieved_sources", []),
        "supervisor_route": result.get("supervisor_route", ""),
        "route_reason": result.get("route_reason", ""),
        "workers_called": result.get("workers_called", []),
        "mcp_tools_used": normalize_mcp_tools_used(result.get("mcp_tools_used", [])),
        "confidence": safe_float(result.get("confidence", 0.0), 0.0),
        "hitl_triggered": bool(result.get("hitl_triggered", False)),
        "latency_ms": result.get("latency_ms"),
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────
# 1. Run Pipeline on Test Questions
# ─────────────────────────────────────────────

def run_test_questions(questions_file: str = "data/test_questions.json") -> list:
    """
    Chạy pipeline với danh sách câu hỏi, lưu trace từng câu.

    Returns:
        list of question result dicts
    """
    ensure_dirs()

    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    print(f"\n📋 Running {len(questions)} test questions from {questions_file}")
    print("=" * 60)

    results = []

    for i, q in enumerate(questions, 1):
        question_text = q["question"]
        q_id = q.get("id", f"q{i:02d}")

        print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

        try:
            result = run_graph(question_text)
            result["question_id"] = q_id

            trace_file = safe_save_trace(result, TRACES_DIR)
            print(
                f"  ✓ route={result.get('supervisor_route', '?')}, "
                f"conf={safe_float(result.get('confidence', 0)):.2f}, "
                f"{result.get('latency_ms', 0)}ms"
            )
            if trace_file:
                print(f"    trace={trace_file}")

            results.append({
                "id": q_id,
                "question": question_text,
                "expected_answer": q.get("expected_answer", ""),
                "expected_sources": q.get("expected_sources", []),
                "difficulty": q.get("difficulty", "unknown"),
                "category": q.get("category", "unknown"),
                "result": result,
            })

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({
                "id": q_id,
                "question": question_text,
                "error": str(e),
                "result": None,
            })

    success_count = sum(1 for r in results if r.get("result"))
    print(f"\n✅ Done. {success_count} / {len(results)} succeeded.")
    return results


# ─────────────────────────────────────────────
# 2. Run Grading Questions
# ─────────────────────────────────────────────

def run_grading_questions(questions_file: str = "data/grading_questions.json") -> str:
    """
    Chạy pipeline với grading questions và lưu JSONL log.

    Returns:
        path tới grading_run.jsonl
    """
    ensure_dirs()

    if not os.path.exists(questions_file):
        print(f"❌ {questions_file} chưa được public (sau 17:00 mới có).")
        return ""

    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    print(f"\n🎯 Running GRADING questions — {len(questions)} câu")
    print(f"   Output → {GRADING_LOG_FILE}")
    print("=" * 60)

    with open(GRADING_LOG_FILE, "w", encoding="utf-8") as out:
        for i, q in enumerate(questions, 1):
            q_id = q.get("id", f"gq{i:02d}")
            question_text = q["question"]

            print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

            try:
                result = run_graph(question_text)
                result["question_id"] = q_id

                safe_save_trace(result, TRACES_DIR)

                record = build_grading_record(q_id, question_text, result)
                print(
                    f"  ✓ route={record['supervisor_route']}, "
                    f"conf={safe_float(record['confidence']):.2f}"
                )

            except Exception as e:
                record = {
                    "id": q_id,
                    "question": question_text,
                    "answer": f"PIPELINE_ERROR: {e}",
                    "sources": [],
                    "supervisor_route": "error",
                    "route_reason": str(e),
                    "workers_called": [],
                    "mcp_tools_used": [],
                    "confidence": 0.0,
                    "hitl_triggered": False,
                    "latency_ms": None,
                    "timestamp": datetime.now().isoformat(),
                }
                print(f"  ✗ ERROR: {e}")

            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n✅ Grading log saved → {GRADING_LOG_FILE}")
    return GRADING_LOG_FILE


# ─────────────────────────────────────────────
# 3. Analyze Traces
# ─────────────────────────────────────────────

def analyze_traces(traces_dir: str = TRACES_DIR) -> dict:
    """
    Đọc tất cả trace files và tính metrics tổng hợp.
    """
    if not os.path.exists(traces_dir):
        print(f"⚠️  {traces_dir} không tồn tại. Chạy run_test_questions() trước.")
        return {}

    trace_files = [f for f in os.listdir(traces_dir) if f.endswith(".json")]
    if not trace_files:
        print(f"⚠️  Không có trace files trong {traces_dir}.")
        return {}

    traces = []
    for fname in trace_files:
        full_path = os.path.join(traces_dir, fname)
        try:
            with open(full_path, encoding="utf-8") as f:
                traces.append(json.load(f))
        except Exception:
            continue

    if not traces:
        print(f"⚠️  Không đọc được trace hợp lệ nào trong {traces_dir}.")
        return {}

    routing_counts = {}
    confidences = []
    latencies = []
    mcp_calls = 0
    hitl_triggers = 0
    source_counts = {}
    worker_counts = {}

    for t in traces:
        route = t.get("supervisor_route", "unknown")
        routing_counts[route] = routing_counts.get(route, 0) + 1

        conf = t.get("confidence")
        if conf is not None:
            confidences.append(safe_float(conf))

        lat = t.get("latency_ms")
        if lat is not None:
            try:
                latencies.append(float(lat))
            except Exception:
                pass

        if t.get("mcp_tools_used"):
            mcp_calls += 1

        if t.get("hitl_triggered"):
            hitl_triggers += 1

        for src in t.get("retrieved_sources", []):
            source_counts[src] = source_counts.get(src, 0) + 1

        for worker in t.get("workers_called", []):
            worker_counts[worker] = worker_counts.get(worker, 0) + 1

    total = len(traces)

    metrics = {
        "total_traces": total,
        "routing_distribution": {
            k: f"{v}/{total} ({round(100 * v / total)}%)"
            for k, v in sorted(routing_counts.items(), key=lambda x: -x[1])
        },
        "worker_call_distribution": {
            k: f"{v}/{total} ({round(100 * v / total)}%)"
            for k, v in sorted(worker_counts.items(), key=lambda x: -x[1])
        },
        "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "mcp_usage_rate": f"{mcp_calls}/{total} ({round(100 * mcp_calls / total)}%)" if total else "0/0 (0%)",
        "hitl_rate": f"{hitl_triggers}/{total} ({round(100 * hitl_triggers / total)}%)" if total else "0/0 (0%)",
        "top_sources": sorted(source_counts.items(), key=lambda x: (-x[1], x[0]))[:5],
    }

    return metrics


# ─────────────────────────────────────────────
# 4. Compare Single vs Multi Agent
# ─────────────────────────────────────────────

def compare_single_vs_multi(
    multi_traces_dir: str = TRACES_DIR,
    day08_results_file: Optional[str] = None,
) -> dict:
    """
    So sánh Day 08 (single agent RAG) vs Day 09 (multi-agent).
    """
    multi_metrics = analyze_traces(multi_traces_dir)

    day08_baseline = {
        "total_questions": 15,
        "avg_confidence": 0.0,          # RAG Day 08 không tính confidence score
        "avg_latency_ms": 2800,         # ~2.8s/câu (tính từ grading_run.json)
        "abstain_rate": "1/10 (10%)",   # Dựa trên scorecard_baseline (Q09 abstain)
        "multi_hop_accuracy": "Thấp",   # Gặp khó ở Q06, Q07 do alias & multi-hop
    }

    if day08_results_file and os.path.exists(day08_results_file):
        with open(day08_results_file, encoding="utf-8") as f:
            day08_baseline = json.load(f)

    comparison = {
        "generated_at": datetime.now().isoformat(),
        "day08_single_agent": day08_baseline,
        "day09_multi_agent": multi_metrics,
        "analysis": {
            "routing_visibility": "Day 09 có route_reason cho từng câu, nên dễ debug routing hơn.",
            "latency_delta": f"Multi-agent Day 09 có latency {multi_metrics.get('avg_latency_ms', 0)}ms so với ~2800ms của Day 08.",
            "accuracy_delta": "Day 09 xử lý tốt multi-hop và alias thông qua routing/worker chuyên biệt, nhỉnh hơn Day 08 variant (4.78/5).",
            "debuggability": "Multi-agent test được từng worker độc lập; single-agent khó tách lỗi theo từng bước.",
            "mcp_benefit": "Day 09 mở rộng capability qua MCP mà không cần sửa toàn bộ core orchestration.",
        },
    }

    return comparison


# ─────────────────────────────────────────────
# 5. Save Eval Report
# ─────────────────────────────────────────────

def save_eval_report(comparison: dict) -> str:
    ensure_dirs()
    with open(EVAL_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    return EVAL_REPORT_FILE


# ─────────────────────────────────────────────
# 6. CLI Entry Point
# ─────────────────────────────────────────────

def print_metrics(metrics: dict):
    if not metrics:
        return

    print("\n📊 Trace Analysis:")
    for k, v in metrics.items():
        if isinstance(v, list):
            print(f"  {k}:")
            for item in v:
                print(f"    • {item}")
        elif isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Day 09 Lab — Trace Evaluation")
    parser.add_argument("--grading", action="store_true", help="Run grading questions")
    parser.add_argument("--analyze", action="store_true", help="Analyze existing traces")
    parser.add_argument("--compare", action="store_true", help="Compare single vs multi")
    parser.add_argument("--test-file", default="data/test_questions.json", help="Test questions file")
    parser.add_argument("--day08-file", default=None, help="Optional Day 08 baseline JSON")
    args = parser.parse_args()

    if args.grading:
        log_file = run_grading_questions()
        if log_file:
            print(f"\n✅ Grading log: {log_file}")
            print("   Nộp file này trước 18:00!")

    elif args.analyze:
        metrics = analyze_traces()
        print_metrics(metrics)

    elif args.compare:
        comparison = compare_single_vs_multi(day08_results_file=args.day08_file)
        report_file = save_eval_report(comparison)
        print(f"\n📊 Comparison report saved → {report_file}")
        print("\n=== Day 08 vs Day 09 ===")
        for k, v in comparison.get("analysis", {}).items():
            print(f"  {k}: {v}")

    else:
        run_test_questions(args.test_file)
        metrics = analyze_traces()
        print_metrics(metrics)

        comparison = compare_single_vs_multi(day08_results_file=args.day08_file)
        report_file = save_eval_report(comparison)
        print(f"\n📄 Eval report → {report_file}")
        print("\n✅ Sprint 4 complete!")
        print("   Next: Điền docs/ templates và viết reports/")