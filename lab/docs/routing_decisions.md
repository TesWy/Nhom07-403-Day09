# Routing Decisions Log — Lab Day 09

**Nhóm:** 07 
**Ngày:** 14/04/2026

> **Hướng dẫn:** Ghi lại ít nhất **3 quyết định routing** thực tế từ trace của nhóm.
> Không ghi giả định — phải từ trace thật (`artifacts/traces/` hoặc `grading_run.jsonl`).
> 
> Mỗi entry phải có: task đầu vào → worker được chọn → route_reason → kết quả thực tế.

---

## Routing Decision #1

**Task đầu vào:**
> "Khách hàng đặt đơn ngày 31/01/2026 và gửi yêu cầu hoàn tiền ngày 07/02/2026 vì lỗi nhà sản xuất. Sản phẩm chưa kích hoạt, không phải Flash Sale, không phải kỹ thuật số. Chính sách nào áp dụng và có được hoàn tiền không?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword: ['hoàn tiền', 'flash sale', 'kỹ thuật số']`  
**MCP tools được gọi:** `[]` (Sử dụng internal retrieval)  
**Workers called sequence:** `["retrieval_worker", "policy_tool_worker", "synthesis_worker"]`

**Kết quả thực tế:**
- final_answer (ngắn): Khách hàng không đủ điều kiện hoàn tiền theo chính sách hiện hành (Temporal Scoping vì mua trước ngày hiệu lực).
- confidence: `0.47`
- Correct routing? Yes 

**Nhận xét:** Lựa chọn routing hoàn toàn chính xác do supervisor bắt được keyword "hoàn tiền". Điều này cho phép `policy_tool_worker` trigger Exception Analysis (Tìm ra logic Temporal Scoping về ngày hiệu lực 01/02) thay vì chỉ để Retrieval Worker trả lời cứng nhắc.

_________________

---

## Routing Decision #2

**Task đầu vào:**
> "Ticket P1 được tạo và on-call engineer không phản hồi sau 10 phút. Theo đúng SLA, hệ thống sẽ làm gì tiếp theo?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `task contains SLA/incident keyword: ['p1', 'sla', 'ticket']`  
**MCP tools được gọi:** `[]`  
**Workers called sequence:** `["retrieval_worker", "synthesis_worker"]`

**Kết quả thực tế:**
- final_answer (ngắn): Tự động escalate lên Senior Engineer sau 10 phút.
- confidence: `0.61`
- Correct routing? Yes 

**Nhận xét:** Một câu truy vấn Knowledge Base (SLA) chuẩn mực. Rule-based router đã quét đúng keyword và không tốn chi phí rẽ nhánh qua `policy_tool_worker`. Kết quả chính xác hoàn toàn.

_________________

---

## Routing Decision #3

**Task đầu vào:**
> "Sự cố P1 xảy ra lúc 2am. Đồng thời cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Hãy nêu đầy đủ: (1) các bước SLA P1 notification phải làm ngay, và (2) điều kiện để cấp Level 2 emergency access."

**Worker được chọn:** `policy_tool_worker` (nhưng có pause ở human_review_node)  
**Route reason (từ trace):** `task contains policy/access keyword: ['access', 'tạm thời'] | risk_high=True | human approved`  
**MCP tools được gọi:** `["get_ticket_info", "check_access_permission"]`  
**Workers called sequence:** `["human_review", "retrieval_worker", "policy_tool_worker", "synthesis_worker"]`

**Kết quả thực tế:**
- final_answer (ngắn): List đủ các bước P1. Riêng Cấp quyền Level 2: cần phê duyệt đồng thời của Line Manager và IT Admin on-call (Dữ liệu Live từ MCP thay vì Document lỗi thời).
- confidence: `0.58`
- Correct routing? Yes 

**Nhận xét:** Case đỉnh cao của hệ thống. Nhờ có `2am` và `tạm thời`, Supervisor bật cờ `risk_high=True`, dừng lại ở Human Review. Sau đó nhảy vào Policy Tool, gọi Tool `check_access_permission` (Function Calling MCP) giải quyết cực sắc sảo vụ Level 2 Override.

_________________

---

## Routing Decision #4 

**Task đầu vào:**
> "Khách hàng mua sản phẩm trong chương trình Flash Sale, nhưng phát hiện sản phẩm bị lỗi từ nhà sản xuất và yêu cầu hoàn tiền trong vòng 5 ngày. Có được hoàn tiền không? Giải thích theo đúng chính sách."

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `task contains policy/access keyword: ['hoàn tiền', 'flash sale']`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**
Bởi vì trong ngữ liệu có 2 điều kiện nghịch nhau: "Lỗi nhà sản xuất" (thường là được hoàn tiền) và "Flash Sale" (không được hoàn tiền). Việc System Router bắt đinh được keyword "hoàn tiền" và "flash sale" để ép câu hỏi này về `policy_tool_worker` (nhằm móc logic Exception phủ định) thay vì về `retrieval_worker` bình thường là yếu tố rẽ nhánh quan trọng giúp LLM chọn tin theo điều kiện của Flash Sale (độ ưu tiên cao hơn) để từ chối khách hàng.

_________________

---

## Tổng kết

### Routing Distribution (Dựa trên 10 Grading Questions)

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 5 | 50% |
| policy_tool_worker | 4 | 40% |
| human_review | 1 | 10% |

### Routing Accuracy

> Trong số 10 câu nhóm đã chạy, bao nhiêu câu supervisor route đúng?

- Câu route đúng: 10 / 10
- Câu route sai (đã sửa bằng cách nào?): 0
- Câu trigger HITL: 1 (Câu P1 lúc 2am cấp quyền contractor)

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?  
> (VD: dùng keyword matching vs LLM classifier, threshold confidence cho HITL, v.v.)

1. **Keyword Over LLM Routing:** Quyết định không xài LLM-As-A-Router giúp node Supervisor phân phối trong *x ms* thay vì tốn >1 giây. Sự hội tụ các list keyword chuyên ngành đạt mức chính xác 100% trong miền IT Helpdesk.
2. **Deterministic Risk Flags for HITL:** Việc cắm cờ `risk_high` thông qua các keyword tĩnh rủi ro ("2am", "emergency") giúp hệ thống cực kỳ an toàn mà vẫn độc lập không phụ thuộc vào dòng suy nghĩ hên xui của LLM.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?  

Rất dồi dào! Trace log báo cụ thể `task contains policy/access keyword: ['hoàn tiền', 'flash sale']` hoặc `... | risk_high=True | human approved`. Khi truy vết lỗi, chỉ cần nhìn vào `route_reason` là biết ngay tại sao Supervisor rẽ hẻm đó, giúp debugging cực kỳ nhẹ nhàng (như lúc phát hiện LLM thiếu Tool Input, nhìn vào route trace là biết Worker nào đang bị cô lập data).
