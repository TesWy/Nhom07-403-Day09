import streamlit as st
from graph import build_graph, make_initial_state

st.set_page_config(page_title="Day 09 - Multi-Agent Helpdesk", page_icon="🤖", layout="centered")

st.title("🤖 Trợ lý ảo IT Helpdesk (Multi-Agent)")
st.markdown("Hệ thống tích hợp **LangGraph-style Orchestration** và **H.I.T.L (Human in the loop)**.")

# --- Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_state" not in st.session_state:
    st.session_state.agent_state = None

if "run_graph" not in st.session_state:
    st.session_state.run_graph = build_graph()

# --- Draw Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "trace" in msg and msg["trace"]:
            with st.expander("🛠️ Xem quá trình phân tích (Trace & MCP)"):
                st.json(msg["trace"])

# --- HITL Interruption UI ---
state = st.session_state.agent_state
if state and state.get("status") == "awaiting_human":
    st.warning("⚠️ **HỆ THỐNG PHÁT HIỆN RỦI RO CAO (Cần con người phê duyệt)**")
    st.info(f"**Lý do:** {state.get('route_reason')}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Phê duyệt & Tiếp tục (Approve)", use_container_width=True):
            # Cập nhật state để resume
            st.session_state.agent_state["status"] = "awaiting_human" # Để graph nhận diện
            st.session_state.agent_state["hitl_triggered"] = True
            
            with st.spinner("Đang tiếp tục xử lý..."):
                # Resume execution
                final_state = st.session_state.run_graph(st.session_state.agent_state)
                st.session_state.agent_state = final_state
                
                if final_state.get("status") == "completed":
                    answer = final_state.get("final_answer", "Lỗi tổng hợp câu trả lời.")
                    trace_data = {
                        "workers_called": final_state.get("workers_called"),
                        "supervisor_route": final_state.get("supervisor_route"),
                        "history": final_state.get("history"),
                        "confidence": final_state.get("confidence")
                    }
                    st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace_data})
                    st.rerun()

    with col2:
        if st.button("❌ Từ chối (Reject)", type="primary", use_container_width=True):
            st.session_state.agent_state = None
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "🚫 Phiên xử lý đã bị bạn từ chối. Vui lòng đặt câu hỏi khác."
            })
            st.rerun()

# --- User Input ---
if prompt := st.chat_input("Hỏi tôi về SLA, chính sách hoàn tiền, hoặc cấp quyền access..."):
    # Chỉ cho phép hỏi câu mới nếu không bị kẹt ở HITL
    if state and state.get("status") == "awaiting_human":
        st.error("Vui lòng Phê duyệt hoặc Từ chối yêu cầu hiện tại trước khi tiếp tục!")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Đang suy nghĩ (Multi-agent routing)..."):
                # Initialize new graph state
                initial_state = make_initial_state(prompt)
                initial_state["hitl_mode"] = "pause" # Kích hoạt chế độ UI
                
                # Run graph
                new_state = st.session_state.run_graph(initial_state)
                st.session_state.agent_state = new_state
                
                if new_state.get("status") == "awaiting_human":
                    st.rerun() # Refresh layout để hiện HITL Box
                else:
                    # Completed smoothly
                    answer = new_state.get("final_answer", "Lỗi tổng hợp câu trả lời.")
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
