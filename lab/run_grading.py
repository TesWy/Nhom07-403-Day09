import json
from datetime import datetime
from graph import build_graph, make_initial_state
import os
from dotenv import load_dotenv

load_dotenv()

run_graph = build_graph()

print("Bắt đầu chạy Grading Questions...")

with open("data/grading_questions.json", encoding="utf-8") as f:
    questions = json.load(f)

# Đảm bảo thư mục artifacts tồn tại
os.makedirs("artifacts", exist_ok=True)

with open("artifacts/grading_run.jsonl", "w", encoding="utf-8") as out:
    for q in questions:
        state = make_initial_state(q["question"])
        state["hitl_mode"] = "auto" # Đảm bảo chạy một lèo không dừng UI
        
        result = run_graph(state)
        
        record = {
            "id": q["id"],
            "question": q["question"],
            "answer": result.get("final_answer", ""),
            "sources": result.get("sources", []),
            "supervisor_route": result.get("supervisor_route"),
            "route_reason": result.get("route_reason"),
            "workers_called": result.get("workers_called", []),
            "mcp_tools_used": result.get("mcp_tools_used", []),
            "confidence": result.get("confidence"),
            "hitl_triggered": result.get("hitl_triggered", False),
            "timestamp": datetime.now().isoformat(),
        }
        
        out.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"✓ {q['id']}: {q['question'][:60]}...")

print("\nĐã chạy xong. Dữ liệu traces được lưu tại: artifacts/grading_run.jsonl")
