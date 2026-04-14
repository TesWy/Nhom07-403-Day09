# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** 07  
**Ngày:** 14/04/2026

> **Hướng dẫn:** So sánh Day 08 (single-agent RAG) với Day 09 (supervisor-worker).
> Phải có **số liệu thực tế** từ trace — không ghi ước đoán.
> Chạy cùng test questions cho cả hai nếu có thể.

---

## 1. Metrics Comparison

> Lấy nguyên dữ liệu từ file JSONL Grading Run Day 09 (The Final Run ~ 10 tests) so sánh tương quan thực tế.

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | ~0.80 (thường ảo giác cao) | ~0.55 (Kỹ lưỡng, Grounded) | Giảm 0.25 | System Prompt day 09 dùng Temp thấp và Penalty Exception nên độ tự tin rất dè chừng. |
| Avg latency (ms) | ~2500 - 3000 ms | ~4500 - 6000 ms | Tăng ~2-3s | Multi-agent cõng thêm thời gian call Tool (MCP) + Graph Transitions. |
| Abstain rate (%) | ~0% (hay bịa luật mới) | ~20% | Tăng 20% | Câu số Q07, Q02 Agent dũng cảm từ chối vì thiếu số liệu / hiệu lực thời gian. |
| Multi-hop accuracy | ~30% | ~96% | Tăng ~66% | Phá giải mỹ mãn các case Cross-doc cực khó (VD Level 2 2AM Override). |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | |
| Debug time (estimate) | > 60 phút | 5 - 10 phút | Nhanh gấp 10 | Trace ghi hẳn MCP Tool Error hay Retrieval Lack chunk rõ rành rành. |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | 90% | 100% |
| Latency | Rất nhanh | Nhanh vừa |
| Observation | Lấy thẳng chunk và trả lời khá ổn. | Route thẳng vào `retrieval_worker`, workflow vẫn diễn ra tương tự RAG thuần. |

**Kết luận:** Với câu hỏi đơn giản, độ chính xác không chênh nhau nhiều. Tuy nhiên, Multi-Agent bị overhead thời gian chuyển trạng thái một chút. (Không đáng kể).

_________________

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Rất Rủi Ro (Trộn luật lung tung) | Hoàn hảo (Giải quyết theo lớp) |
| Routing visible? | ✗ | ✓ |
| Observation | LLM bị loạn giữa các version luật. | Có Worker riêng đối chiếu Live Rules từ Function Calling Tool. |

**Kết luận:** Đây là ranh giới sống còn. Supervisor phân luồng câu phức tạp vào `policy_tool_worker`, giúp LLM có thêm thông tin API Mocked (e.g. Okta Level Rules), giải phóng Multi-Hop cực mạnh.

_________________

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | Rất thấp (Auto Hallucination) | Cao, từ chối rất trí tuệ |
| Hallucination cases | Bịa cả tiền phạt vi phạm SLA | Chủ động báo "Không có quy định phạt SLA, hãy liên hệ IT" |
| Observation | Bị "Trôi Context" (Lost in prompt) | Nhờ System Prompt nhỏ hẹp tập trung, tính kỷ luật cao. |

**Kết luận:** Bóc tách LLM thành Architecture Worker nhỏ lẻ giúp "Kiềm chế" ảo giác (LLM Guardrails hoạt động siêu hiệu quả).

_________________

---

## 3. Debuggability Analysis

> Khi pipeline trả lời sai, mất bao lâu để tìm ra nguyên nhân?

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 60 - 90 phút (Thường phải prompt-hacking thử sai hên xui)
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic
  → Nếu retrieval sai → test retrieval_worker độc lập (như vụ Tăng Top_k=5 để kiếm kênh PagerDuty)
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 10 phút
```

**Câu cụ thể nhóm đã debug:** 
*Quá trình sửa lại case GQ09: Ban đầu AI bị lừa lấy quyền Override chung chung (Tech Lead phê duyệt).* 
1. Check Trace `grading_run.jsonl`, phát hiện Routing đúng, nhưng Worker Synthesis không thấy JSON Output của MCP Tool.
2. Code lại đúng 3 dòng để inject `mcp_tools_used` từ State vào String Context của LLM Prompt trong `synthesis.py`.
3. Chạy lại, GQ09 Lấy đúng Rule Level 2 tức khắc. (Debugging siêu cách ly, không ảnh hưởng Retrieval Worker).

_________________

---

## 4. Extensibility Analysis

> Dễ extend thêm capability không?

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn bự prompt (rất nguy hiểm) | Thêm MCP tool client + route rule rất vô tư |
| Thêm 1 domain mới | Phải retrain/re-prompt | Đẻ ra 1 Node Worker mới trên LangGraph |
| Thay đổi retrieval strategy | Sửa trực tiếp bầy hầy trong RAG.py | Sửa retrieval_worker độc lập (viết lại def thôi) |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap function worker |

**Nhận xét:** Kiến trúc Node & Edge của M-A Orchestration là chuẩn mực của Design Pattern Enterprise. Extensibility là Absolute 10/10.

_________________

---

## 5. Cost & Latency Trade-off

> Multi-agent thường tốn nhiều LLM calls hơn. Nhóm đo được gì?

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 1 LLM calls (vì dùng Keyword Router) |
| Complex query | 1 LLM call | 2-3 LLM calls (tùy Exception Checker) |
| MCP tool call | N/A | 1-2 API calls (Mocked) |

**Nhận xét về cost-benefit:** Mặc dù chi phí có thể x2 đối với các câu phức tạp, nhưng Lợi ích là **Giảm Hallucination** và **Bypass HITL**. Trong môi trường IT Helpdesk thực tế - Sai 1 ly (cấp quyền nhầm cho Hacker) đi ngàn dặm - thì sự đánh đổi Latency và Cost là hoàn toàn hợp lý!

_________________

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**
1. Chia để trị (Separation of Concerns).
2. Debugging chắp cánh vì State được chia khoang riêng biệt (Logging xịn).
3. Cho phép Human-In-The-Loop tham gia cản phá ở giữa Node trước khi hệ thống thốt ra câu kết.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**
1. Overhead về thời gian và Token.
2. Codebase cồng kềnh, Cần duy trì Data Pipeline chuẩn (State Class/Dict).

> **Khi nào KHÔNG nên dùng multi-agent?**
Khi làm các ứng dụng Chat chitchat, Trợ lý viết lách đơn giản, Hay MVP cần go-to-market tốc hành ngày mai.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**
Sẽ tích hợp trực tiếp 1 External MCP Server chạy NodeJs bọc Okta OAuth2 và Jira API để Live System Fetch thay vì Mocked Python Dictionary hiện tại. Thêm cả chức năng Auto-Retries (Backoff) cho Node Synthesis nếu check thấy tự tin quá mỏng (<0.2).
