import streamlit as st
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("CHAT_SERVICE_URL", "http://localhost:8001")

# Session management
def init_session():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = datetime.now().strftime("%Y%m%d%H%M%S")

# UI Components
def settings_sidebar():
    with st.sidebar:
        st.title("Chat Settings")
        st.session_state.medicine = st.text_input(
            "Medicine Filter (optional)",
            value=getattr(st.session_state, "medicine", "")
        )
        if st.button("New Session"):
            st.session_state.session_id = datetime.now().strftime("%Y%m%d%H%M%S")
            st.session_state.chat_history = []
            st.rerun()

def display_chat():
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for src in msg["sources"]:
                        st.caption(f"{src['medicine']} - {src['label']} ({src['score']:.2f})")

def handle_user_input():
    if prompt := st.chat_input("Ask about medications..."):
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now()
        })
        
        # Get response
        with st.spinner("Thinking..."):
            response = requests.post(
                f"{BACKEND_URL}/chats/{st.session_state.session_id}/message",
                json={
                    "message": prompt,
                    "medicine_name": st.session_state.medicine,
                    "session_id": st.session_state.session_id,
                    "history": [
                        {"role": "user" if m["role"] == "user" else "assistant", 
                         "content": m["content"]}
                        for m in st.session_state.chat_history[-6:]
                    ]
                }
            ).json()
        
        # Add AI response
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response["response"],
            "sources": response["sources"],
            "timestamp": response["timestamp"]
        })
        
        st.rerun()

# Main app
def main():
    st.set_page_config(page_title="Pharma Chat", layout="wide")
    init_session()
    settings_sidebar()
    
    st.title("Pharmaceutical Chat Assistant")
    st.caption(f"Session: {st.session_state.session_id}")
    
    display_chat()
    handle_user_input()

if __name__ == "__main__":
    main()