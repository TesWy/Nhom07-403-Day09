# So sánh Kiến trúc Single Agent vs. Multi-Agent Orchestration

Tài liệu này so sánh ưu/nhược điểm giữa việc triển khai RAG Chatbot bằng một **Single Agent (Monolithic Prompt)** so với cấu trúc **Multi-Agent Orchestration (DAG - Directed Acyclic Graph)** mà đồ án Day 09 đã thực hiện.

---

## 1. Single Agent (Monolithic)
**Mô tả:** Là dạng Agent "một cửa" truyền thống. Dùng duy nhất một LLM lớn kèm một System Prompt khổng lồ chứa MỌI hướng dẫn (từ Retrieval, Policy Exception, Tool Calling, đến Formatting).

### Ưu điểm:
- Dễ code, dễ triển khai (ví dụ: dùng hàm `agent.invoke()` duy nhất).
- Toàn bộ context nằm ở một chỗ (Mức độ liền mạch cao).
- Tốc độ phát triển POC (Proof of Concept) cực nhanh.

### Khuyết điểm:
- **Hội chứng "Bối rối Prompt"**: Khi System Prompt quá lớn, Agent có xu hướng quên instruction ở đầu dẫu nhắc nhiều lần ("Lost in the middle"). Ví dụ: Agent có thể làm tốt việc đánh giá Refund nhưng lại quên trích dẫn nguồn, hoặc mải trích dẫn nguồn lại quên trừ hao ngày hiệu lực.
- **Tiêu tốn Token/Tiền Tệ**: Mọi thao tác chat đều phải cõng một lượng Context và System Prompt khổng lồ.
- **Rủi ro đứt đoạn cao**: Nếu AI gặp lỗi ở nửa chừng suy nghĩ, nó sẽ làm sụp toàn bộ câu trả lời. Khó gài cờ "Dừng lại chờ người trực tiếp" rào chắn (HITL).

---

## 2. Multi-Agent Orchestration (Kiến trúc Graph/DAG)
**Mô tả:** Bài toán được băm nhỏ thành các Node con (Workers), được giám sát bởi 1 `Supervisor`. Ví dụ: `retrieval_worker` chuyên móc tài liệu, `policy_tool_worker` rà soát Exception / Call MCP Tool, `synthesis_worker` tổng hợp chữ và giọng điệu.

### Ưu điểm (Lý do dự án Day 09 tuân thủ):
- **Phân tách trách nhiệm (Separation of Concerns)**: Mỗi worker chuyên biệt bằng System Prompt nhỏ, giúp model tập trung xử lý cực kỳ sâu vào nhiệm vụ. (Ví dụ: Synthesis worker chỉ cần quan trọng Văn phong và Formatting, mà không phải đau đầu suy tính biến luồng tài liệu).
- **Function Calling chính xác hơn**: `policy_tool_worker` dễ trigger các Extenal Tools (Okta/Jira) hơn do prompt không bị loãng.
- **Kiểm soát quy trình mượt (Control Flow)**: Dễ dàng chèn các Node Approval như `human_review_node` vào sát sườn luồng xử lý trước khi thực sự tổng hợp văn bản xuất ra. 
- **Debug bằng Log**: Nhanh chóng nhận ra AI "ảo giác" ở đoạn nào (Lỗi lấy tài liệu ngu tại Retrieval hay Tổng hợp ngáo tại Synthesis) nhờ state machine có ghi traces từng chặng.

### Khuyết điểm:
- Yêu cầu cấu trúc Code (Data state) phức tạp, cần LangGraph hoặc state dict luân chuyển qua từng Node.
- Độ trễ (System Latency) tăng lên nếu như các Node gọi LLM liên tục (Thay vì 1 lần invoke tốn 3 giây, 2 Node LLM nối nhau tốn 6 giây). (Ở dự án này ta tối ưu bằng cách Supervisor chạy offline rule-based để bù tốc độ lại).

## Bài học chốt yếu
Đối với nghiệp vụ **IT Helpdesk Cấp Doanh Nghiệp** – nơi "Chính xác của Policy" và "Bảo mật ủy quyền" quan trọng hơn "trả lời lanh lẹ nhảm nhí" – thì **Multi-Agent Orchestration kết hợp Human In The Loop (HITL)** là thiết kế bắt buộc mang tính sinh tử.
