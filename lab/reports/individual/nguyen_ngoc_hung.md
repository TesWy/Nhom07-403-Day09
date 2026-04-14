# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Ngọc Hưng  
**Vai trò trong nhóm:** Worker Owner (Sprint 2 Lead)  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ  

---

## 1. Tôi phụ trách phần nào? (150 từ)

Trong dự án Multi-Agent Orchestration hôm nay, tôi chịu trách nhiệm chính về **Sprint 2: Build Workers**. Cụ thể, tôi đã thiết kế và lập trình toàn bộ logic xử lý cho 3 module worker nòng cốt của hệ thống:

- **Retrieval Worker (`workers/retrieval.py`)**: Implement hàm `retrieve_dense` để nhúng query và truy vấn vector DB (ChromaDB), đảm bảo trả về các đoạn văn bản (chunks) có độ tương đồng cao nhất cùng với metadata nguồn.
- **Policy Tool Worker (`workers/policy_tool.py`)**: Xây dựng bộ lọc chính sách (Policy Analysis) để phát hiện các ngoại lệ như Flash Sale, sản phẩm kỹ thuật số, hoặc quy trình cấp quyền tạm thời. Tôi cũng tích hợp phần gọi MCP tools (`search_kb`, `get_ticket_info`) vào worker này.
- **Synthesis Worker (`workers/synthesis.py`)**: Thiết kế prompt hệ thống và logic tổng hợp kết quả (grounded response), đảm bảo câu trả lời cuối cùng có trích dẫn nguồn `[1], [2]` và tính toán được chỉ số tin cậy (confidence score).

Công việc của tôi đóng vai trò là "trung tâm xử lý" của Graph. Supervisor (của bạn Supervisor Owner) sẽ gửi task cho tôi thông qua `AgentState`, và kết quả từ các worker tôi làm sẽ là đầu vào để hệ thống đưa ra phản hồi cuối cùng cho người dùng.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (200 từ)

**Quyết định:** Tôi chọn triển khai cơ chế **Hybrid Policy Analysis** (kết hợp Rule-based và LLM) trong `workers/policy_tool.py` thay vì chỉ phụ thuộc hoàn toàn vào LLM để phân tích chính sách.

**Lý do:** Qua thử nghiệm với các câu hỏi về "Hoàn tiền Flash Sale", tôi nhận thấy LLM đôi khi bị "hallucinate" hoặc bỏ sót các điều khoản loại trừ cứng nhắc trong tài liệu nếu prompt không cực kỳ chi tiết. Trong khi đó, các quy định như "Flash Sale không hoàn tiền" hay "Sản phẩm đã kích hoạt không đổi trả" là các quy tắc kinh doanh (Business Rules) bất biến. 
Việc dùng regex và keyword matching (Rule-based) giúp hệ thống:
1. Đảm bảo độ chính xác 100% đối với các trường hợp ngoại lệ đã biết.
2. Giảm latency (phản hồi mất < 1ms so với ~1-2s nếu gọi LLM).
3. LLM chỉ đóng vai trò "Refinement" để viết lại giải thích (explanation) cho người dùng một cách tự nhiên hơn.

**Bằng chứng từ code:**
Trong file `policy_tool.py`, tôi đã viết logic kiểm tra ngoại lệ trước khi gọi LLM:
```python
# Rule-based exception detection (Line 76-99)
if "flash sale" in task_lower or "flash sale" in context_text:
    exceptions_found.append({
        "type": "flash_sale_exception",
        "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3, chính sách v4).",
        "source": "policy_refund_v4.txt",
    })
```
Kết quả trong trace `run_20260414_163133.json` cho thấy khi gặp task về "cấp quyền tạm thời", logic rule-based đã xác định đúng `policy_name="access_control_sop"` trước khi LLM thực hiện phân tích chi tiết.

---

## 3. Tôi đã sửa một lỗi gì? (150 từ)

**Lỗi:** `KeyError: 'history'` và `KeyError: 'worker_io_logs'` khi chạy Graph end-to-end.

**Symptom:** Khi Supervisor gọi các worker lần đầu tiên, chương trình bị crash ngay lập tức vì worker cố gắng thực hiện `state["history"].append(...)` trong khi key này chưa tồn tại trong dictionary `AgentState`.

**Root cause:** Do sự thiếu đồng nhất trong việc khởi tạo `AgentState` ở `graph.py` (Sprint 1). Supervisor Owner chỉ khởi tạo các field cơ bản như `task`, nhưng các field lưu vết (trace) lại để trống, dẫn đến các worker bị "gãy" khi cố gắng ghi log.

**Cách sửa:** Thay vì yêu cầu Supervisor phải khởi tạo đủ toàn bộ keys (dễ gây lỗi nếu sau này thêm worker mới), tôi đã áp dụng cơ chế **Self-Healing State** trong tất cả các hàm `run()` của worker bằng cách sử dụng `setdefault`.

**Bằng chứng sau khi sửa (`retrieval.py`):**
```python
def run(state: dict) -> dict:
    # Đảm bảo state luôn có đủ các field cần thiết để ghi log
    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("worker_io_logs", [])
    
    state["workers_called"].append(WORKER_NAME)
    # ... logic xử lý tiếp theo ...
```
Sau khi áp dụng thay đổi này, toàn bộ 15 câu hỏi trong `test_questions.json` đã chạy mượt mà mà không gặp bất kỳ lỗi runtime nào về cấu trúc state.

---

## 4. Tôi tự đánh giá đóng góp của mình (100 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã xây dựng được bộ Worker có tính module hóa cao. Mỗi worker (`retrieval`, `policy`, `synthesis`) đều có thể chạy độc lập (Standalone Test) giúp việc debug cực kỳ nhanh chóng mà không cần khởi động toàn bộ Graph phức tạp.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi cảm thấy phần tính toán `confidence score` trong `synthesis.py` còn hơi cảm tính (dựa trên trung bình cộng score của chunks). Lẽ ra tôi nên dùng LLM-as-a-judge để đánh giá độ khớp giữa Answer và Context thì điểm số này sẽ có giá trị tham chiếu cao hơn.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm phụ thuộc vào tôi để đảm bảo thông tin phản hồi có tính "grounded" (không bịa đặt). Nếu Synthesis Worker của tôi không trích dẫn đúng nguồn, cả hệ thống sẽ mất uy tín với người dùng IT Helpdesk.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc hoàn toàn vào Supervisor Owner để nhận đúng task type. Nếu Supervisor route nhầm một câu hỏi "Refund" sang Retrieval thay vì Policy Tool, hệ thống của tôi sẽ không thể phát hiện ra các ngoại lệ Flash Sale.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (100 từ)

Tôi sẽ triển khai thêm bước **Re-ranking** (Sử dụng Cross-Encoder) trong `retrieval.py`. 
**Lý do:** Trong trace của câu hỏi `q15` (Ticket P1/Access Control), mặc dù các văn bản đúng đã được lấy ra, nhưng điểm cosine similarity chỉ đạt khoảng 0.62. Điều này cho thấy mật độ từ khóa giữa query và tài liệu chuyên môn không cao. Nếu có thêm Re-ranking, tôi có thể lọc lại top 10 kết quả sơ bộ để lấy ra đúng 3 đoạn văn bản "đắt" nhất, từ đó giúp Synthesis Worker tạo ra câu trả lời sắc bén hơn và tăng điểm confidence lên trên 0.8.

---
*Lưu file này với tên: `reports/individual/nguyen_ngoc_hung.md`*  
