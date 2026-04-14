import json
import os

print("=== 📊 BÁO CÁO ĐÁNH GIÁ KẾT QUẢ GRADING ===")

try:
    with open("data/grading_questions.json", encoding="utf-8") as f:
        questions = {q["id"]: q for q in json.load(f)}

    results = []
    with open("artifacts/grading_run.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))

    total = len(results)
    routing_correct = 0
    sources_correct = 0
    hitl_correct = 0

    hitl_expected_ids = ["q06", "q13", "q15"]  # Các câu rõ ràng mang rủi ro contractor / 2am / escalation

    for r in results:
        q_id = r["id"]
        q = questions.get(q_id)
        if not q: 
            continue
        
        # 1. Routing Accuracy
        expected_route = q.get("expected_route")
        route = r.get("supervisor_route")
        if route == expected_route or (expected_route == "error" and route == "error"):
            routing_correct += 1
        elif expected_route == "retrieval_worker" and route == "policy_tool_worker":
             # Đôi khi policy_tool vẫn trả lời đúng các câu retrieval thông qua fallback
             pass 

        # 2. Source Accuracy (Ít nhất chứa đủ các file yêu cầu)
        expected_sources = set(q.get("expected_sources", []))
        actual_sources = set(r.get("sources", []))
        if expected_sources.issubset(actual_sources) or (not expected_sources and not actual_sources):
            sources_correct += 1
        
        # 3. HITL Trigger Logic
        # Nếu id thuộc nhóm expected hoặc kết quả có ghi lại hitl
        hitl_triggered = r.get("hitl_triggered", False)
        print(f"[{q_id}] Route: {route} (Đích: {expected_route}) | Nguồn: {len(actual_sources)}/{len(expected_sources)} | HITL: {hitl_triggered}")

    print("\n=== 📈 THỐNG KÊ TỔNG QUAN ===")
    print(f"Tổng số câu test: {total}")
    print(f"✔️ Điều hướng (Routing) chuẩn xác: {routing_correct}/{total} ({routing_correct/total*100:.1f}%)")
    print(f"✔️ Truy xuất tài liệu (Retrieval) đầy đủ: {sources_correct}/{total} ({sources_correct/total*100:.1f}%)")
    
except Exception as e:
    print("Có lỗi trong quá trình đọc file:", e)
