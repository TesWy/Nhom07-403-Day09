# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Huỳnh Lê Xuân Ánh  
**Vai trò trong nhóm:** MCP Owner, Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong dự án Lab Day 09, tôi chịu trách nhiệm chính trong việc thiết kế và triển khai **Mock MCP Server**, giúp hệ thống có khả năng gọi công cụ một cách linh hoạt. Bên cạnh đó, tôi cũng đảm nhận vai trò Docs Owner, chịu trách nhiệm ghi nhận kiến trúc hệ thống để đảm bảo tính đồng bộ giữa thiết kế và thực thi.

**Các nhiệm vụ cụ thể tôi đã thực hiện:**
- **Implement Mock MCP Server**: Xây dựng máy chủ công cụ với 3 tools quan trọng:
  - `search_kb(query, top_k)`: Tìm kiếm trong Knowledge Base bằng cách tích hợp với ChromaDB thông qua `retrieval_worker`.
  - `get_ticket_info(ticket_id)`: Tra cứu thông tin ticket thời gian thực dựa trên bộ mock data Jira.
  - `check_access_permission`: Kiểm tra quyền truy cập Live từ hệ thống giả lập (Okta/Jira logic).
- **Integration**: Chỉnh sửa logic trong `workers/policy_tool.py` để worker này gọi MCP client lấy kết quả thay vì truy cập ChromaDB trực tiếp, giúp kiến trúc trở nên module hóa hơn.
- **Observability**: Triển khai cơ chế ghi nhận chi tiết `mcp_tool_called` và `mcp_result` vào trace để phục vụ việc giám sát luồng điều phối.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Đóng gói logic truy vấn Vector Database (ChromaDB) vào nội hàm của MCP Tool thay vì để Worker gọi trực tiếp.

**Lý do:**
Việc để các Worker (như Policy hay Retrieval) tự ý kết nối và truy vấn ChromaDB làm cho mã nguồn bị phân tán và khó bảo trì. Bằng cách định nghĩa tool `search_kb` trên MCP Server, tôi đã tạo ra một lớp trừu tượng mới. Giờ đây, các Worker chỉ cần biết "tên tool" và "tham số đầu vào", còn việc dữ liệu được lưu ở ChromaDB, Elasticsearch hay SQL là trách nhiệm của MCP Server. Điều này giúp kiến trúc của nhóm trở nên cực kỳ modular và dễ dàng thay thế công nghệ lưu trữ trong tương lai mà không ảnh hưởng đến logic điều phối (Orchestration).

**Trade-off đã chấp nhận:**
Hệ thống sẽ có thêm một chút overhead khi phải đi qua lớp Dispatcher của MCP. Tuy nhiên, sự đánh đổi này mang lại tính chuẩn hóa và khả năng tái sử dụng tool call rất cao giữa các Agent khác nhau trong tương lai.

**Bằng chứng từ trace/code:**
Trong `workers/policy_tool.py`, mã nguồn đã được đơn giản hóa để hướng tới chuẩn MCP:
```python
# Gọi MCP client để lấy kết quả thay vì truy cập ChromaDB trực tiếp
if not chunks and needs_tool:
    mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
    state["mcp_tools_used"].append(mcp_result) # Ghi nhận vào trace
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Trace hệ thống bị thiếu thông tin hoặc sai lệch khi MCP Tool trả về định dạng không tương thích (Schema Mismatch).

**Symptom:**
Trong giai đoạn đầu tích hợp, khi `policy_tool.py` gọi tool nhưng MCP server trả về lỗi hoặc kết quả trống, biến `mcp_result` bị ghi vào trace một cách không nhất quán (đôi khi là chuỗi error, đôi khi là None). Điều này khiến cho việc phân tích hậu kiểm (Post-mortem analysis) của Docs Owner trở nên khó khăn vì không thể tái lập được bối cảnh lỗi.

**Root cause:**
Hàm xử lý gọi tool tại worker chưa có cơ chế đóng gói (wrapping) kết quả thống nhất. Khi tool execution gặp Exception, state không được cập nhật đúng cách khiến trace bị đứt đoạn.

**Cách sửa:**
Tôi đã xây dựng một hàm wrapper chuẩn hóa trong `policy_tool.py` để đảm bảo luôn ghi nhận `mcp_tool_called` (thông qua property `tool`) và `mcp_result` (thông qua property `output`) dưới dạng một object có cấu trúc ổn định, ngay cả khi phát sinh lỗi.
```python
def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    try:
        from mcp_dispatch import dispatch_tool
        result = dispatch_tool(tool_name, tool_input)
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # Đảm bảo trace vẫn ghi nhận được tool call ngay cả khi fail
```
**Bằng chứng:** Sau khi cập nhật, file `grading_run.jsonl` đã ghi lại chi tiết mọi lần gọi tool thành công/thất bại, giúp nhóm dễ dàng đối chiếu lý do AI đưa ra câu trả lời dựa trên `mcp_result`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tôi đã hiện thực hóa thành công mô hình Multi-Agent Orchestration đúng nghĩa bằng cách đưa MCP vào trung tâm xử lý dữ liệu. Việc tách biệt dữ liệu khỏi logic worker giúp hệ thống chuyên nghiệp và sát với thực tế doanh nghiệp hơn. Tôi cũng hoàn thành tốt vai trò Docs Owner khi tài liệu kiến trúc luôn phản ánh đúng 100% tình trạng của code.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tôi vẫn còn dựa nhiều vào Mock Server trong cùng process. Lẽ ra tôi nên triển khai một mô hình client-server thực thụ qua HTTP/gRPC để tối ưu hóa tính độc lập của dịch vụ.

**Nhóm phụ thuộc vào tôi ở đâu?**
Nhóm thực sự phụ thuộc vào tôi để có được dữ liệu "Live". Nếu không có MCP Server, Agent sẽ không thể tra cứu thông tin ticket hay kiểm tra quyền truy cập một cách chính xác.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ tích hợp thêm một cơ chế validation schema chặt chẽ hơn tại MCP Server bằng cách sử dụng Pydantic. Điều này sẽ giúp bắt lỗi ngay từ bước `mcp_tool_called`, giúp hệ thống ổn định tuyệt đối và tạo ra các thông báo lỗi dễ hiểu hơn cho trace log, giảm thiểu thời gian debug cho cả nhóm.

---

