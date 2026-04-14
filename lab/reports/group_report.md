# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** 7
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Huỳnh Lê Xuân Ánh | MCP Owner, Docs Owner | huynhlexuananh2002@gmail.com |
| Huỳnh Nhựt Huy | MCP Owner, Trace & Docs Owner | huy40580@gmail.com |
| Nguyễn Ngọc Khánh Duy | Supervisor Owner | nguyenngockhanhduy1@gmail.com |
| Nguyễn Ngọc Hưng | Worker Owner | hungnguyenngoc714@gmail.com |

**Ngày nộp:** 14/04/2026  
**Repo:** https://github.com/TesWy/Nhom07-403-Day09.git
**Độ dài khuyến nghị:** 600–1000 từ

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

**Hệ thống tổng quan:**
Nhóm đã triển khai kiến trúc **Supervisor-Worker** linh hoạt với 3 worker chuyên biệt: **Retrieval Worker** (truy xuất semantic), **Policy Tool Worker** (xử lý logic chính sách & MCP), và **Synthesis Worker** (tổng hợp câu trả lời). Hệ thống sử dụng Shared State để duy trì dấu vết xử lý xuyên suốt graph. Điểm nổi bật là khả năng tích hợp **Human-in-the-loop (HITL)** thông qua cờ `risk_high` giúp chặn các yêu cầu nhạy cảm (như cấp quyền Admin vào rạng sáng) để chờ phê duyệt thủ công.

**Routing logic cốt lõi:**
Supervisor sử dụng cơ chế **Keyword Matching** kết hợp với **Regex** (để bắt mã lỗi `ERR-xxx`). Logic này phân loại task vào 3 luồng chính:
1. Luồng SLA/Incident (Retrieval).
2. Luồng Refund/Access Policy (Policy Tool + MCP).
3. Luồng rủi ro cao/lỗi lạ (Human Review).
Việc dùng keyword giúp tốn rất ít latency (<10ms) nhưng đạt độ chính xác routing 100% trong miền IT Helpdesk của Lab.

**MCP tools đã tích hợp:**
- `search_kb`: Tìm kiếm sâu trong Knowledge Base với tham số `top_k`.
- `get_ticket_info`: Truy xuất thông tin Live của ticket (SLA status, priority).
- `check_access_permission`: Kiểm tra quyền truy cập Live từ hệ thống giả lập (Okta/Jira logic).

*Ví dụ trace gọi MCP tool (GQ09):*
```json
"mcp_tools_used": [
  {
    "tool": "check_access_permission",
    "input": {"access_level": 2, "requester_role": "contractor", "is_emergency": true},
    "output": {
      "can_grant": true,
      "required_approvers": ["Line Manager", "IT Admin"],
      "emergency_override": true,
      "notes": ["Level 2 có thể cấp tạm thời với approval đồng thời của Line Manager và IT Admin on-call."]
    }
  }
]
```

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Sử dụng **Keyword-based Router** thay vì **LLM-based Classifier** cho Node Supervisor.

**Bối cảnh vấn đề:**
Trong các phiên thử nghiệm đầu tiên, việc gọi một LLM (gpt-4o-mini) chỉ để chọn worker tiếp theo khiến hệ thống mất thêm ~1.2 giây cho mỗi request. Ngoài ra, LLM thi thoảng bị "ảo giác" khi gặp các câu hỏi mập mờ, dẫn đến việc route sai (ví dụ: câu hỏi về P1 SLA nhưng lại bị route vào Policy Tool do có từ "phê duyệt").

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| **LLM Classifier** | Hiểu được ngữ cảnh phức tạp, linh hoạt. | Latency cao, tốn token, khó kiểm soát 100% logic. |
| **Keyword/Regex (Chọn)** | Tốc độ cực nhanh (<10ms), deterministic (biết chắc tại sao nó route vậy), dễ debug. | Cần bộ từ điển keyword tốt, kém linh hoạt với từ đồng nghĩa. |

**Phương án đã chọn và lý do:**
Nhóm chọn **Keyword/Regex** kết hợp với bộ ngân hàng từ khoá (Keyword Banks) được phân loại kỹ. Lý do chính là tốc độ và sự minh bạch. Trong môi trường IT Helpdesk, các khái niệm thường đi kèm thuật ngữ cố định (SLA, P1, Refund, Flash Sale). Việc này giúp team debug cực nhanh thông qua `route_reason` mà không phải đoán "tâm trạng" của LLM.

**Bằng chứng từ trace/code:**
Trong file `graph.py`, Supervisor sử dụng bộ từ khóa và rẽ nhánh dựa trên kết quả so khớp:
```python
# graph.py literal
policy_keywords = [
    "hoàn tiền", "refund", "flash sale", "license", "license key",
    "cấp quyền", "access", "level 3", "admin access", "quyền truy cập",
    "subscription", "kỹ thuật số", "tạm thời", "quy trình tạm thời",
]
# ...
elif any(kw in task for kw in policy_keywords):
    route = "policy_tool_worker"
    matched = [kw for kw in policy_keywords if kw in task]
    route_reason = f"task contains policy/access keyword: {matched}"
```
*Kết quả trace GQ02:* `route_reason: "task contains policy/access keyword: ['hoàn tiền', 'flash sale', 'kỹ thuật số']"`.


---

## 3. Kết quả grading questions (150–200 từ)

**Tổng điểm raw ước tính:** 92 / 96 (~96%)

**Câu pipeline xử lý tốt nhất:**
- ID: **GQ09 (Multi-hop bypass)** — Lý do: Đây là câu khó nhất yêu cầu gọi MCP tool để lấy luật "Emergency Bypass" thay vì luật Document. Hệ thống đã trigger đúng `policy_tool_worker`, gọi Tool thành công và Synthesis tổng hợp chính xác điều kiện "Line Manager + IT Admin".

**Câu pipeline fail hoặc partial:**
- ID: **GQ01 (Kênh PagerDuty)** — Fail ở đâu: Chỉ đạt 8/10.  
  Root cause: AI chỉ chú trọng vào Slack/Email (thông tin chính trong doc) mà bỏ qua channel PagerDuty nằm ở phần phụ lục sâu bên dưới. Điều này cho thấy `top_k=3` của Retrieval đôi khi vẫn bỏ sót các chi tiết nhỏ ở cuối trang.

**Câu gq07 (abstain):** Nhóm xử lý rất tốt (10/10). Thay vì bịa ra một con số phạt tài chính cho vi phạm SLA (không có trong tài liệu), hệ thống đã dũng cảm trả lời: *"Tài liệu không đề cập đến mức phạt tài chính cụ thể, vui lòng liên hệ phòng Pháp chế."*

**Câu gq09 (multi-hop khó nhất):** Trace ghi nhận chuỗi gọi: `retrieval_worker` -> `policy_tool_worker` (gọi MCP `check_access_permission`) -> `synthesis_worker`. Kết quả đạt điểm tuyệt đối 16/16.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

**Metric thay đổi rõ nhất (có số liệu):**
- **Độ chính xác Multi-hop:** Tăng từ ~30% (Day 08) lên **96%** (Day 09).
- **Thời gian Debug:** Giảm từ hơn 60 phút xuống còn **10 phút** nhờ có trace chi tiết cho từng worker.
- **Latency:** Tăng từ ~2.5s lên **~5.5s** (do overhead của việc chuyển node và gọi thêm tool).

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**
Khả năng "kiềm chế" ảo giác cực tốt. Khi tách riêng Worker Synthesis với chỉ thị "Chỉ trả lời dựa trên context được cung cấp", AI không còn tự ý "nhét" các luật tự chế vào câu trả lời như ở Day 08.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Với các câu hỏi cực kỳ đơn giản (Ví dụ: "SLA P1 là bao lâu?"), kiến trúc Multi-Agent tạo ra một sự lãng phí về thời gian quay vòng (overhead). Single-agent RAG thuần túy sẽ trả về kết quả nhanh hơn ~3 giây mà độ chính xác vẫn tương đương.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Ngọc Khánh Duy | Supervisor Node, Routing Logic, Graph Orchestration | Sprint 1 |
| Nguyễn Ngọc Hưng | Worker Nodes (Retrieval, Policy, Synthesis) | Sprint 2 |
| Huỳnh Lê Xuân Ánh | Mock MCP Server Implementation, System Architecture | Sprint 3 |
| Huỳnh Nhựt Huy | Advanced MCP Server Implementation, Traces analysis, Evaluation, Routing_Decisions, Single_vs_Multi_Comparison | Sprint 3 |

**Điều nhóm làm tốt:**
- Phối hợp nhịp nhàng trong việc định nghĩa **Shared State Schema**, giúp dữ liệu luân chuyển giữa các worker không bị lỗi format.
- Xử lý triệt để bẫy **Temporal Scoping** bằng cách ép logic kiểm tra ngày tháng vào Policy Worker.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
- Ban đầu chưa thống nhất cách inject MCP output vào Synthesis, dẫn đến việc synthesis bị "mù" thông tin từ Tool trong các bản chạy thử đầu tiên.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**
Sẽ dành thêm thời gian để chuẩn hoá bộ data test ngay từ đầu Sprint 1 thay vì đợi đến Sprint 3 mới chạy pipeline đánh giá, giúp phát hiện lỗi "mất context" sớm hơn.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ thực hiện 2 cải tiến:
1. **Auto-Retry Node:** Tự động gọi lại Node Retrieval với `top_k` cao hơn nếu Node Synthesis báo `confidence < 0.3` (như case PagerDuty GQ01).
2. **External MCP:** Thay thế Mocked Python Server bằng một External MCP thực sự (chạy Node.js) để gọi trực tiếp Jira API, mang lại dữ liệu Live 100% cho hệ thống.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*

