import streamlit as st
import json
from graph import build_graph, make_initial_state

st.set_page_config(page_title="Day 09 - Multi-Agent Helpdesk", page_icon="👨‍💻", layout="wide")

USER_AVATAR = "🧑‍💼"
BOT_AVATAR = "👨‍💻"

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Tiện ích & Mẫu thử")
    
    # Nút xoá lịch sử
    if st.button("🗑️ Xoá lịch sử hội thoại", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_state = None
        st.rerun()
        
    st.markdown("---")
    st.markdown("**📝 Bộ câu hỏi kiểm thử:**")
    try:
        with open("data/test_questions.json", encoding="utf-8") as f:
            test_questions = json.load(f)
            q_options = ["--- Chọn câu hỏi mẫu ---"] + [f"{q['id']}: {q['question']}" for q in test_questions]
    except Exception:
        q_options = ["--- Chọn câu hỏi mẫu ---"]
        
    selected_q = st.selectbox("Chọn để nạp nhanh câu hỏi:", q_options)
    trigger_sample = False
    if selected_q != "--- Chọn câu hỏi mẫu ---":
        sample_text = selected_q.split(": ", 1)[-1]
        if st.button("💬 Gửi câu hỏi này", type="primary", use_container_width=True):
            trigger_sample = sample_text

st.title("👨‍💻 Trợ lý ảo IT Helpdesk (Multi-Agent)")
st.caption("Hệ thống tích hợp **LangGraph-style Orchestration** và luồng **H.I.T.L (Human in the loop)**.")

# --- Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_state" not in st.session_state:
    st.session_state.agent_state = None

if "run_graph" not in st.session_state:
    st.session_state.run_graph = build_graph()

# --- Draw Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=USER_AVATAR if msg["role"]=="user" else BOT_AVATAR):
        st.markdown(msg["content"])
        if "trace" in msg and msg["trace"]:
            with st.expander("🛠️ Xem quá trình phân tích (Trace & MCP)"):
                st.json(msg["trace"])

# --- HITL Interruption UI ---
state = st.session_state.agent_state
if state and state.get("status") == "awaiting_human":
    st.error("⚠️ **HỆ THỐNG PHÁT HIỆN RỦI RO CAO (Cần con người phê duyệt chốt chặn)**")
    st.info(f"**Lý do:** {state.get('route_reason')}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Phê duyệt & Cấp quyền (Approve)", use_container_width=True):
            st.session_state.agent_state["status"] = "awaiting_human" 
            st.session_state.agent_state["hitl_triggered"] = True
            
            with st.spinner("Đang tiếp tục xử lý lệnh..."):
                final_state = st.session_state.run_graph(st.session_state.agent_state)
                st.session_state.agent_state = final_state
                
                if final_state.get("status") == "completed":
                    answer = final_state.get("final_answer", "Lỗi tổng hợp câu trả lời.")
                    sources = final_state.get("sources", [])
                    
                    # Tự động gán nguồn tham khảo
                    if sources:
                        answer += "\n\n**📚 Nguồn tài liệu được tham chiếu:**\n"
                        for s in sources:
                            answer += f"- `{s}`\n"
                            
                    trace_data = {
                        "workers_called": final_state.get("workers_called"),
                        "supervisor_route": final_state.get("supervisor_route"),
                        "history": final_state.get("history"),
                        "confidence": final_state.get("confidence")
                    }
                    st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace_data})
                    st.rerun()

    with col2:
        if st.button("❌ Ngăn chặn khẩn cấp (Reject)", type="primary", use_container_width=True):
            st.session_state.agent_state = None
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "🚫 Hệ thống đã ngắt lệnh theo yêu cầu của bạn. Rất vui lòng được hỗ trợ bạn các vấn đề khác."
            })
            st.rerun()

# --- User Input ---
prompt = st.chat_input("Hỏi tôi về SLA, chính sách hoàn tiền, hoặc cấp quyền access...")

# Merge input trigger
if trigger_sample:
    prompt = trigger_sample

if prompt:
    if state and state.get("status") == "awaiting_human":
        st.warning("Vui lòng Phê duyệt hoặc Từ chối yêu cầu rủi ro cao hiện tại trước khi chat tiếp!")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=BOT_AVATAR):
            with st.spinner("Đang truy xuất và đối chiếu luồng (Multi-agent routing)..."):
                initial_state = make_initial_state(prompt)
                initial_state["hitl_mode"] = "pause" 
                
                new_state = st.session_state.run_graph(initial_state)
                st.session_state.agent_state = new_state
                
                if new_state.get("status") == "awaiting_human":
                    st.rerun()
                else:
                    answer = new_state.get("final_answer", "Lỗi tổng hợp câu trả lời.")
                    sources = new_state.get("sources", [])
                    
                    # Tự động gán nguồn tham khảo rõ ràng cho người dùng
                    if sources:
                        answer += "\n\n**📚 Nguồn tài liệu được tham chiếu:**\n"
                        for s in sources:
                            answer += f"- `{s}`\n"
                            
                    trace_data = {
                        "workers_called": new_state.get("workers_called"),
                        "supervisor_route": new_state.get("supervisor_route"),
                        "history": new_state.get("history"),
                        "confidence": new_state.get("confidence")
                    }
                    st.markdown(answer)
                    with st.expander("🛠️ Xem quá trình phân tích (Trace & MCP)"):
                        st.json(trace_data)
                    st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace_data})
