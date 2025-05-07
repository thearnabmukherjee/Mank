# import streamlit as st
# import requests
# from datetime import datetime
# import os
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# # Session state initialization
# if "session_id" not in st.session_state:
#     st.session_state.session_id = datetime.now().strftime("%Y%m%d%H%M%S")
# if "medicine_name" not in st.session_state:
#     st.session_state.medicine_name = ""
# if "chat_history" not in st.session_state:
#     st.session_state.chat_history = []

# # Page config
# st.set_page_config(page_title="Medical Chat Assistant", layout="wide")

# # Sidebar for settings
# with st.sidebar:
#     st.title("Settings")
#     st.session_state.medicine_name = st.text_input(
#         "Medicine Name (optional)", 
#         value=st.session_state.medicine_name
#     )
#     if st.button("Clear Chat History"):
#         st.session_state.chat_history = []
#         st.experimental_rerun()

# # Main chat interface
# st.title("Medical Chat Assistant")
# st.caption(f"Session ID: {st.session_state.session_id}")

# # Chat container
# chat_container = st.container()

# # Function to call backend
# def get_chat_response(message):
#     try:
#         response = requests.post(
#             f"{BACKEND_URL}/chats/{st.session_state.session_id}/message",
#             json={
#                 "message": message,
#                 "medicine_name": st.session_state.medicine_name
#             }
#         )
#         return response.json()
#     except Exception as e:
#         return {"error": str(e)}

# # Function to generate insights
# def generate_insights():
#     try:
#         response = requests.post(
#             f"{BACKEND_URL}/insights/{st.session_state.medicine_name}/generate"
#         )
#         return response.json()
#     except Exception as e:
#         return {"error": str(e)}

# # Display chat history
# with chat_container:
#     for msg in st.session_state.chat_history:
#         if msg["type"] == "human":
#             with st.chat_message("user"):
#                 st.write(msg["content"])
#         else:
#             with st.chat_message("assistant"):
#                 st.write(msg["content"])
#                 if "sources" in msg:
#                     with st.expander("Sources"):
#                         for source in msg["sources"]:
#                             st.caption(f"Document: {source.get('medicine_name', 'Unknown')}")
#                             st.caption(f"Label: {source.get('label', 'N/A')}")
#                             st.caption("---")

# # Chat input
# if prompt := st.chat_input("Ask about medications..."):
#     # Add user message to history
#     st.session_state.chat_history.append({
#         "type": "human",
#         "content": prompt,
#         "timestamp": datetime.now().isoformat()
#     })
    
#     # Get response
#     response = get_chat_response(prompt)
    
#     if "error" not in response:
#         # Add AI response to history
#         st.session_state.chat_history.append({
#             "type": "ai",
#             "content": response["response"],
#             "sources": response.get("sources", []),
#             "timestamp": datetime.now().isoformat()
#         })
#         st.experimental_rerun()
#     else:
#         st.error(f"Error: {response['error']}")

# # Insights section
# if st.session_state.medicine_name:
#     st.divider()
#     st.subheader(f"Insights for {st.session_state.medicine_name}")
    
#     if st.button("Generate Insights"):
#         with st.spinner("Generating insights..."):
#             insights = generate_insights()
            
#             if "error" not in insights:
#                 st.markdown("### Key Insights")
#                 st.write(insights["insights"])
                
#                 with st.expander("Source Documents"):
#                     for doc in insights.get("sources", []):
#                         st.caption(f"Document ID: {doc.get('doc_id', 'N/A')}")
#                         st.caption(f"Medicine: {doc.get('medicine_name', 'Unknown')}")
#                         st.caption("---")
#             else:
#                 st.error(f"Error generating insights: {insights['error']}")

# # CSS for better appearance
# st.markdown("""
# <style>
#     .stChatMessage {
#         padding: 12px;
#         border-radius: 8px;
#         margin-bottom: 12px;
#     }
#     .stChatMessage.user {
#         background-color: #f0f2f6;
#     }
#     .stChatMessage.assistant {
#         background-color: #e6f7ff;
#     }
# </style>
# """, unsafe_allow_html=True)





# import streamlit as st
# import requests
# from datetime import datetime
# import os
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# # Session state initialization
# if "session_id" not in st.session_state:
#     st.session_state.session_id = datetime.now().strftime("%Y%m%d%H%M%S")
# if "medicine_name" not in st.session_state:
#     st.session_state.medicine_name = ""
# if "chat_history" not in st.session_state:
#     st.session_state.chat_history = []
# if "sidebar_history" not in st.session_state:
#     st.session_state.sidebar_history = []

# # Page config
# st.set_page_config(page_title="Medical Chat Assistant", layout="wide")

# # Sidebar for settings and history
# with st.sidebar:
#     st.title("Chat History")
    
#     # Load history from backend
#     if st.button("Refresh History"):
#         try:
#             response = requests.get(
#                 f"{BACKEND_URL}/chats/{st.session_state.session_id}/history"
#             )
#             if response.status_code == 200:
#                 st.session_state.sidebar_history = response.json()
#         except Exception as e:
#             st.error(f"Failed to load history: {str(e)}")
    
#     # Display historical messages
#     for msg in st.session_state.sidebar_history:
#         with st.expander(f"{msg['timestamp']} - {msg.get('medicine_name', 'General')}"):
#             st.markdown(f"**Q:** {msg['question']}")
#             st.markdown(f"**A:** {msg['answer']}")
#             if msg.get("sources"):
#                 st.caption("Sources:")
#                 for source in msg["sources"]:
#                     st.caption(f"- {source.get('medicine_name', 'Unknown')}: {source.get('label', 'N/A')}")

#     st.divider()
#     st.title("Settings")
#     st.session_state.medicine_name = st.text_input(
#         "Medicine Name (optional)", 
#         value=st.session_state.medicine_name
#     )
#     if st.button("Clear Current Chat"):
#         st.session_state.chat_history = []
#         st.experimental_rerun()

# # Main chat interface
# st.title("Medical Chat Assistant")
# st.caption(f"Session ID: {st.session_state.session_id}")

# # Chat container
# chat_container = st.container()

# # Function to call backend
# def get_chat_response(message):
#     try:
#         response = requests.post(
#             f"{BACKEND_URL}/chats/{st.session_state.session_id}/message",
#             json={
#                 "message": message,
#                 "medicine_name": st.session_state.medicine_name
#             }
#         )
#         return response.json()
#     except Exception as e:
#         return {"error": str(e)}

# # Display chat history
# with chat_container:
#     for msg in st.session_state.chat_history:
#         if msg["type"] == "human":
#             with st.chat_message("user"):
#                 st.write(msg["content"])
#         else:
#             with st.chat_message("assistant"):
#                 st.write(msg["content"])
#                 if "sources" in msg:
#                     with st.expander("Sources"):
#                         for source in msg["sources"]:
#                             st.caption(f"Medicine: {source.get('medicine_name', 'Unknown')}")
#                             st.caption(f"Label: {source.get('label', 'N/A')}")
#                             st.caption(f"Relevance: {source.get('score', 0):.2f}")
#                             st.caption("---")

# # Chat input
# if prompt := st.chat_input("Ask about medications..."):
#     # Add user message to history
#     st.session_state.chat_history.append({
#         "type": "human",
#         "content": prompt,
#         "timestamp": datetime.now().isoformat()
#     })
    
#     # Get response
#     with st.spinner("Thinking..."):
#         response = get_chat_response(prompt)
    
#     if "error" not in response:
#         # Add AI response to history
#         st.session_state.chat_history.append({
#             "type": "ai",
#             "content": response["response"],
#             "sources": response.get("sources", []),
#             "timestamp": datetime.now().isoformat()
#         })
        
#         # Refresh sidebar history
#         try:
#             history_response = requests.get(
#                 f"{BACKEND_URL}/chats/{st.session_state.session_id}/history"
#             )
#             if history_response.status_code == 200:
#                 st.session_state.sidebar_history = history_response.json()
#         except Exception:
#             pass
        
#         st.experimental_rerun()
#     else:
#         st.error(f"Error: {response['error']}")

# # CSS for better appearance
# st.markdown("""
# <style>
#     .stChatMessage {
#         padding: 12px;
#         border-radius: 8px;
#         margin-bottom: 12px;
#     }
#     .stChatMessage.user {
#         background-color: #f0f2f6;
#     }
#     .stChatMessage.assistant {
#         background-color: #e6f7ff;
#     }
#     .sidebar .sidebar-content {
#         background-color: #f8f9fa;
#     }
# </style>
# """, unsafe_allow_html=True)




# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------
import streamlit as st
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("CHAT_SERVICE_URL", "http://localhost:8000")

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