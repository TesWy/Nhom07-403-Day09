# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Ngọc Khánh Duy  
**Vai trò trong nhóm:** Supervisor Owner  
**Ngày nộp:** 2026-04-14  

---

## 1. Tôi phụ trách phần nào?

Tôi chịu trách nhiệm toàn bộ Sprint 1 — thiết kế và implement Supervisor Orchestrator, là thành phần trung tâm điều phối toàn bộ hệ thống multi-agent.

**Module/file tôi chịu trách nhiệm:**
- File chính: `lab/graph.py`
- Functions tôi implement:
  - `AgentState` — TypedDict định nghĩa shared state xuyên suốt graph (15 fields)
  - `make_initial_state()` — khởi tạo state mới cho mỗi run với run_id timestamp
  - `supervisor_node()` — phân tích task, gắn route/risk/needs_tool vào state
  - `route_decision()` — conditional edge trả về tên worker tiếp theo
  - `human_review_node()` — HITL placeholder với auto-approve cho lab mode
  - `build_graph()` / `run_graph()` — Python orchestrator chạy toàn bộ pipeline
  - `save_trace()` — serialize AgentState ra file JSON

**Cách công việc của tôi kết nối với phần của thành viên khác:**

`AgentState` là contract dùng chung: retrieval worker ghi vào `retrieved_chunks`, policy worker ghi vào `policy_result`, synthesis worker đọc cả hai để tạo `final_answer`. Nếu tôi thay đổi tên field trong `AgentState`, toàn bộ các workers của các thành viên khác sẽ bị break ngay lập tức.

**Bằng chứng:**
- Commit `5e71fd8` ("update Sprint 1") — thêm keyword banks và sửa routing logic trong `graph.py` (+119 dòng, -47 dòng)

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Dùng keyword-based routing trong `supervisor_node()` thay vì gọi LLM để classify task.

Khi thiết kế `supervisor_node()`, tôi có hai lựa chọn:
- **Option A (tôi chọn):** Dùng keyword matching với 3 banks (policy_keywords, retrieval_keywords, risk_keywords) và priority order cố định.
- **Option B:** Gọi LLM để phân loại task thành các category, linh hoạt hơn nhưng chậm và tốn token.

Tôi chọn Option A vì domain của hệ thống này hẹp và có thể xác định rõ — chỉ có 3 loại câu hỏi (policy/refund, SLA/ticket, và unknown error). Keyword matching đủ chính xác cho 5 categories, không cần LLM overhead. Ngoài ra, với lab 4 giờ, tôi cần một routing layer ổn định sớm để các thành viên khác có thể implement workers song song.

**Lý do:** Tốc độ routing nhanh hơn ~800ms (LLM roundtrip) so với <1ms, đồng thời `route_reason` luôn explainable — trace ghi rõ keyword nào trigger route nào, dễ debug khi pipeline sai.

**Trade-off đã chấp nhận:** Routing sẽ fail với câu hỏi viết không dấu hoặc dùng từ đồng nghĩa không có trong keyword bank. Ví dụ: "Trả hàng" không match "hoàn tiền" → default route thay vì policy_tool_worker.

**Bằng chứng từ trace:**

```json
// run_20260414_161917.json — routing đúng sau khi có đủ keyword bank
{
  "task": "SLA xử lý ticket P1 là bao lâu?",
  "supervisor_route": "retrieval_worker",
  "route_reason": "task contains SLA/incident keyword: ['p1', 'sla', 'ticket']",
  "risk_high": false,
  "latency_ms": 4948
}
```

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Supervisor route toàn bộ câu hỏi P1/SLA vào "default route" thay vì "retrieval_worker" theo đúng logic.

**Symptom:**

Trace `run_20260414_151422` cho thấy query `"SLA xử lý ticket P1 là bao lâu?"` bị route với `route_reason = "default route"` — supervisor hoàn toàn bỏ qua keywords "sla", "p1", "ticket".

**Root cause:**

Trong version đầu của `supervisor_node()`, routing logic chỉ check một số từ khóa đơn giản bằng `if "p1" in task` nhưng so sánh với `state["task"]` (chưa lowercase) — trong khi task thực tế có chữ hoa "P1", "SLA". Ngoài ra, keyword bank chưa đầy đủ, thiếu từ "ticket" và "sla" trong retrieval group.

**Cách sửa:**

Thêm `.lower()` khi đọc task (`task = state["task"].lower()`), sau đó mở rộng keyword bank với `retrieval_keywords` đầy đủ. Đồng thời tái cấu trúc routing thành priority order rõ ràng (ERR-xxx → policy → retrieval → default) để tránh overlap.

**Bằng chứng trước/sau:**

```
# TRƯỚC (run_20260414_151422):
"task": "SLA xử lý ticket P1 là bao lâu?"
"supervisor_route": "retrieval_worker"
"route_reason": "default route"   ← SAI

# SAU (run_20260414_161917):
"task": "SLA xử lý ticket P1 là bao lâu?"
"supervisor_route": "retrieval_worker"
"route_reason": "task contains SLA/incident keyword: ['p1', 'sla', 'ticket']"   ← ĐÚNG
```

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế `AgentState` đủ hoàn chỉnh từ đầu (15 fields bao gồm trace fields như `worker_io_logs`, `run_id`, `latency_ms`) giúp các thành viên khác implement workers mà không cần sửa lại contract giữa chừng. Routing logic rõ ràng với priority order và `route_reason` explainable giúp debug dễ — khi pipeline sai, nhìn trace là biết ngay lỗi ở supervisor hay worker.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Keyword bank vẫn brittle với tiếng Việt không dấu. Query `"SLA xu ly ticket P1 la bao lau?"` (không dấu) sẽ fail vì `"ticket"` → match, nhưng `"p1"` → match, `"sla"` → match — may mắn vẫn đúng, nhưng `"hoan tien"` không match `"hoàn tiền"` → route sai. Tôi chưa xử lý normalization cho tiếng Việt không dấu.

**Nhóm phụ thuộc vào tôi ở đâu?**

Tất cả workers (retrieval, policy_tool, synthesis) đều depend vào `AgentState` và `build_graph()`. Nếu Sprint 1 chưa xong, các thành viên không có pipeline để test worker của mình trong context đầy đủ.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi cần `workers/retrieval.py`, `workers/policy_tool.py`, `workers/synthesis.py` đã implement để `graph.py` có thể import và chạy end-to-end. Trong Sprint 1, tôi dùng mock response tạm để test routing logic độc lập.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thêm Unicode normalization (bỏ dấu tiếng Việt) trước khi keyword matching trong `supervisor_node()`. Trace `run_20260414_151422` cho thấy khi query nhập không dấu (`"SLA xu ly ticket P1"`), routing vẫn chạy được may mắn do "p1" và "sla" vẫn match — nhưng `"hoan tien"` sẽ fail hoàn toàn. Với 15 test questions trong `data/test_questions.json`, có ít nhất 3-4 câu được gõ không dấu theo thực tế sử dụng nội bộ, sẽ ảnh hưởng trực tiếp đến accuracy routing.

---
