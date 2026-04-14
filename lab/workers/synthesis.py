"""
workers/synthesis.py — Synthesis Worker
Sprint 2: Tổng hợp câu trả lời từ retrieved_chunks và policy_result.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: evidence từ retrieval_worker
    - policy_result: kết quả từ policy_tool_worker

Output (vào AgentState):
    - final_answer: câu trả lời cuối với citation
    - sources: danh sách nguồn tài liệu được cite
    - confidence: mức độ tin cậy (0.0 - 1.0)

Gọi độc lập để test:
    python workers/synthesis.py
"""

import os
from dotenv import load_dotenv
load_dotenv()

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên môn IT Helpdesk cấp cao.
Nhiệm vụ: Trả lời câu hỏi dựa TRÊN TÀI LIỆU ĐƯỢC CUNG CẤP ở dưới.

Nguyên tắc bắt buộc:
1. Trích dẫn nguồn BẰNG TÊN FILE: VD `[sla-p1-2026.pdf]`. Chỉ sử dụng tên file được cung cấp trong [Source].
2. KHÔNG BAO GIỜ tự bịa thông tin. Nếu không có trong context, báo thẳng: "Tài liệu không cung cấp mã lỗi này / thông tin này".

Hướng dẫn tư duy nâng cao (Advanced Reasoning):
- KIỂM TRA HIỆU LỰC (Temporal Scoping): Chú ý đến "Effective Date" trong tài liệu. Nếu câu hỏi đề cập đến ngày tháng sự kiện xảy ra TRƯỚC ngày hiệu lực của tài liệu hiện có, BẠN PHẢI TỪ CHỐI TRẢ LỜI (VD: "Chính sách áp dụng là bản v3 nhưng tài liệu hiện tại chỉ có bản v4, vui lòng báo bộ phận liên quan"). Không tự động copy rập khuôn luật mới cho quá khứ.
- TỔNG HỢP TOÀN DIỆN (Multi-Section Extraction): Khi được hỏi "kênh nào", "ai nhận", "bao nhiêu người", BẠN PHẢI ĐỌC HẾT CÁC PHẦN của tài liệu (cả quy trình lẫn phần cấu hình công cụ cuối văn bản) để liệt kê không sót bất cứ kênh nào (Slack, Email, PagerDuty, v.v.).
- PHÂN ĐỊNH QUYỀN TRUY CẬP (Access Control Parsing): Không được trộn lẫn quy trình báo sự cố chung với quy trình cấp quyền. Nếu hỏi về quyền Level cụ thể, phải trả lời đúng các role (Line Manager, IT Admin, Security, Tech Lead) áp dụng ĐÚNG cho hạng mục Level đó, KHÔNG LẤY MÃ CẤP QUYỀN của Level 3 áp cho Level 2.

3. ƯU TIÊN CHÍNH SÁCH NGOẠI LỆ: Nếu thông tin có phần "POLICY EXCEPTIONS" (Ngoại lệ chính sách), bạn phải phân tích phần đó đầu tiên trước khi đưa ra kết luận.
4. TỪ CHỐI THÔNG MINH (ABSTAIN): Nếu không tìm thấy thông tin trong context, hãy xin lỗi nhẹ nhàng: "Rất tiếc, tôi chưa tìm thấy thông tin này trong tài liệu nội bộ hiện tại. Xin hãy liên hệ trực tiếp phòng IT để được hỗ trợ cụ thể nhé."
5. TRÌNH BÀY ĐẸP MẮT: Sử dụng Markdown (in đậm, in nghiêng, bullet points) để bài nói mạch lạc, dễ lưu ý các điểm quan trọng.
"""


def _call_llm(messages: list) -> str:
    """
    Gọi LLM để tổng hợp câu trả lời.
    TODO Sprint 2: Implement với OpenAI hoặc Gemini.
    """
    # Option A: OpenAI
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.1,  # Low temperature để grounded
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception:
        pass

    # Option B: Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        combined = "\n".join([m["content"] for m in messages])
        response = model.generate_content(combined)
        return response.text
    except Exception:
        pass

    # Fallback: trả về message báo lỗi (không hallucinate)
    return "[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env."


def _build_context(chunks: list, policy_result: dict, mcp_tools_used: list = None) -> str:
    """Xây dựng context string từ chunks, policy result và mcp_tools_used."""
    parts = []

    if mcp_tools_used:
        parts.append("=== MCP TOOLS OUTPUT (LIVE DATA) ===")
        for call in mcp_tools_used:
            tool = call.get("tool", "")
            out = call.get("output", {})
            parts.append(f"Tool {tool} returned: {out}")

    if chunks:
        parts.append("\n=== TÀI LIỆU THAM KHẢO ===")
        for chunk in chunks:
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            score = chunk.get("score", 0)
            parts.append(f"Nguồn: [{source}] (relevance: {score:.2f})\n{text}")

    if policy_result:
        if policy_result.get("exceptions_found"):
            parts.append("\n=== POLICY EXCEPTIONS ===")
            for ex in policy_result["exceptions_found"]:
                parts.append(f"- {ex.get('rule', '')}")
        if policy_result.get("policy_version_note"):
            parts.append(f"\n=== TEMPORAL SCOPING NOTE ===\n{policy_result.get('policy_version_note')}")

    if not parts:
        return "(Không có context)"

    return "\n".join(parts)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """
    Ước tính confidence dựa vào:
    - Số lượng và quality của chunks
    - Có exceptions không
    - Answer có abstain không

    TODO Sprint 2: Có thể dùng LLM-as-Judge để tính confidence chính xác hơn.
    """
    if not chunks:
        return 0.1  # Không có evidence → low confidence

    if "Không đủ thông tin" in answer or "không có trong tài liệu" in answer.lower():
        return 0.3  # Abstain → moderate-low

    # Weighted average của chunk scores
    if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
    else:
        avg_score = 0

    # Penalty nếu có exceptions (phức tạp hơn)
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))

    confidence = min(0.95, avg_score - exception_penalty)
    return round(max(0.1, confidence), 2)


def synthesize(task: str, chunks: list, policy_result: dict, mcp_tools_used: list = None) -> dict:
    """
    Tổng hợp câu trả lời từ chunks và policy context.

    Returns:
        {"answer": str, "sources": list, "confidence": float}
    """
    context = _build_context(chunks, policy_result, mcp_tools_used)

    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Câu hỏi: {task}

{context}

Hãy trả lời câu hỏi dựa vào tài liệu trên."""
        }
    ]

    answer = _call_llm(messages)
    sources = list({c.get("source", "unknown") for c in chunks})
    confidence = _estimate_confidence(chunks, answer, policy_result)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
    }


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})
    mcp_tools_used = state.get("mcp_tools_used", [])

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "has_policy": bool(policy_result),
        },
        "output": None,
        "error": None,
    }

    try:
        result = synthesize(task, chunks, policy_result, mcp_tools_used)
        state["final_answer"] = result["answer"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]

        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "confidence": result["confidence"],
        }
        state["history"].append(
            f"[{WORKER_NAME}] answer generated, confidence={result['confidence']}, "
            f"sources={result['sources']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["confidence"] = 0.0
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Synthesis Worker — Standalone Test")
    print("=" * 50)

    test_state = {
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [
            {
                "text": "Ticket P1: Phản hồi ban đầu 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục 4 giờ. Escalation: tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.",
                "source": "sla_p1_2026.txt",
                "score": 0.92,
            }
        ],
        "policy_result": {},
    }

    result = run(test_state.copy())
    print(f"\nAnswer:\n{result['final_answer']}")
    print(f"\nSources: {result['sources']}")
    print(f"Confidence: {result['confidence']}")

    print("\n--- Test 2: Exception case ---")
    test_state2 = {
        "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi nhà sản xuất.",
        "retrieved_chunks": [
            {
                "text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.",
                "source": "policy_refund_v4.txt",
                "score": 0.88,
            }
        ],
        "policy_result": {
            "policy_applies": False,
            "exceptions_found": [{"type": "flash_sale_exception", "rule": "Flash Sale không được hoàn tiền."}],
        },
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")

    print("\n✅ synthesis_worker test done.")
