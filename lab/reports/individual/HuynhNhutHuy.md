# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Huỳnh Nhựt Huy 
**Vai trò trong nhóm:** Trace & Docs Owner / Evaluator / UI Developer  
**Ngày nộp:** 14/04/2026  

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `chat_ui.py`, `run_grading.py`, `evaluate_run.py`, `artifacts/grading_evaluation_report.md`
- Tuning các file râu ria sau khi review trace: `workers/synthesis.py`, `workers/retrieval.py`, `workers/policy_tool.py`.
- Functions tôi implement: Logic parse State Object thành UI Chat Streamlit có Expander (`chat_ui.py`), và Script Extract Data `run_grading.py` để sinh logs tự động, và phần mcp advanced thêm.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Tôi đóng vai trò audit toàn bộ hệ thống Multi-Agent do các bạn Worker/Supervisor Owners xây dựng. Khi các bạn hoàn thiện Node và Graph, tôi là người cắm script `run_grading.py` để ép luồng chạy 10 test case khó nhất, lôi State Object (chứa trace, tool calls, context) ra và đúc thành mảng JSONL `artifacts/grading_run.jsonl`. Khâu đánh giá điểm của tôi giúp nhóm biết State Machine đang gãy ở điểm nào để vá sao đó tiến hành optimize lại, cụ thể dễ thấy nhất là case thứ 2 trong test ẩn (optimize prompt)

**Bằng chứng:** 
Commit Hash có chứa file `lab/artifacts/grading_run.jsonl` và giao diện `chat_ui.py` ....(TesWy).

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Nâng cấp tham số `DEFAULT_TOP_K = 5` (trong `retrieval.py`) và Injection dữ liệu MCP Tools trực tiếp vào System Prompt của hàm `_build_context()` (trong `synthesis.py`).

**Lý do:**
Chương trình chấm điểm 10 câu khắt khe có bẫy về *Cross-document Multi-hop* và *Multi-section completeness* . Ban đầu, tôi định dùng Langchain Agent ReAct LLM phức tạp để AI tự suy nghĩ lấy chừng nào đủ tài liệu thì thôi. Tuy nhiên, để tối ưu tốc độ và không phá ngang kiến trúc Graph tĩnh của các bạn Worker Owner, tôi đề xuất việc thay đổi nhỏ lẻ gọn gàng: Mở độ rộng phễu lấy Document (Top_K=5 để không trượt phần mô tả PagerDuty ở đáy file SLA) và nối chuỗi Object `mcp_tools_used` vào chuỗi Text Prompt để LLM nhìn thấy kết quả Live JSON từ hệ thống IT thay vì bị "mù" do đứt gãy luồng State.

**Trade-off đã chấp nhận:**
Tốn thêm khoảng 500-1000 tokens cho Context LLM (Vì nhét cả JSON Node Tools và mở rộng lượng Chunks), làm tăng Latency thêm ~1.5s và hao chi phí token.

**Bằng chứng từ trace/code:**
File `synthesis.py` (Line 80+):
```python
def _build_context(chunks: list, policy_result: dict, mcp_tools_used: list = None) -> str:
    parts = []
    if mcp_tools_used:
        parts.append("=== MCP TOOLS OUTPUT (LIVE DATA) ===")
        for call in mcp_tools_used:
            parts.append(f"Tool {call.get('tool')} returned: {call.get('output')}")
    # ...
```
Trace `GQ09` trong `grading_run.jsonl` đạt 16/16 điểm sau khi áp dụng quyết định.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Tư duy "Temporal Scoping" gãy vỡ (Ảo giác thời gian). 

**Symptom (pipeline làm gì sai?):**
Trong Test GQ02: "Đơn hàng ngày 31/01/2026, hỏi chính sách v3 hoàn tiền được không". LLM đã trả lời một cách tự tin: *"Được hoàn tiền theo quy định v4"* hoặc *"Không đủ điều kiện hoàn tiền do trái với v4"* mà tảng lờ đi dữ kiện ngày tháng hiệu lực của tài liệu (Effective Date: 01/02). 

**Root cause (lỗi nằm ở đâu):**
Lỗi nằm ở sự hồn nhiên của `synthesis_worker`. Nó chỉ tìm cách match Text với câu hỏi, không hề có quy tắc "Ngừng lại suy ngẫm về Meta-data thời gian".

**Cách sửa:**
Tôi viết lại System Prompt của `synthesis.py` thay vì can thiệp Logic Code phức tạp. Thêm quy định Advanced Reasoning:
*"KIỂM TRA HIỆU LỰC (Temporal Scoping): Chú ý đến Effective Date trong tài liệu. Nếu câu hỏi đề cập đến sự kiện xảy ra TRƯỚC ngày hiệu lực... BẠN PHẢI TỪ CHỐI TRẢ LỜI (Abstain). Không tự động copy rập khuôn luật tương lai cho quá khứ."*

**Bằng chứng trước/sau:**
*Trace GQ02 (Trước):* 
> `"answer": "Khách hàng đủ điều kiện hoàn tiền vì không thuộc danh mục kỹ thuật số..."` (Sai luật v3)
*Trace GQ02 (Sau):* 
> `"answer": "Đơn hàng được đặt vào 31/01/2026... trước ngày hiệu lực của v4... chính sách phiên bản 3 không có thông tin... Rất tiếc, tôi không thể cung cấp thêm thông tin... Xin liên hệ phòng IT."` (Hoàn hảo).

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Khả năng "nhảy số" khi đọc Trace JSONL. Tôi dễ dàng track ngược lại từ Final Answer rác (Hallucination) về từng Node trong Graph để vạch mặt Node nào đang làm rớt context (Như pha tìm ra Worker bỏ quên MCP Tools Output). Làm UI có Expanders tiện lợi cho các bạn khác review State trực quan.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Vì chủ yếu làm về Blackbox Prompting Engineering để chữa cháy (ví dụ chỉnh Prompt Temporal Scoping), đôi khi cách fix của tôi vẫn phụ thuộc vào xác suất độ hên xui của LLM (nhiệt độ temperature), chưa biến nó thành Rule-based Python Filter Code cứng cáp được như bạn Policy_Tool Owner.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nếu tôi không chạy eval và đánh giá thì nhóm không có output, cũng như là không đánh giá được hệ thống đag yếu chổ nào để cải thiện.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc phần như là toàn bộ các phần của member khác khi mà dựa chủ yếu trên các infra mà team mmeber xây dựng

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Nếu có thêm 2 giờ, tôi sẽ **tích hợp Few-Shot Prompting Dataset vào Synthesis Worker**. 
Lý do: Hiện tại cấu trúc câu trả lời của AI dù đúng nội dung (Grounded) nhưng vẫn chưa thống nhất format văn bản IT do chỉ dùng Zero-Shot Prompting. Dựa trên trace của câu GQ01, AI hay bị đánh rớt các ý nhỏ lẻ ở cuối File (như PagerDuty). Việc cho AI xem 2-3 ví dụ Few-Shot Extraction đa luồng trong bộ nhớ sẽ triệt tiêu hoàn toàn Hallucination bỏ sót ý, đảm bảo Rate Perfect 100% trong mọi Trace.
