import streamlit as st
import requests
from datetime import datetime
import pandas as pd

# Set page configuration
st.set_page_config(
    page_title="ChatGPT-like Interface",
    page_icon="💬",
    layout="wide"
)

# Define API URL
API_URL = "http://localhost:8000"

# Initialize session state
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "sessions" not in st.session_state:
    st.session_state.sessions = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "new_chat_clicked" not in st.session_state:
    st.session_state.new_chat_clicked = False
if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "expanded"  # or "collapsed"
if "last_context" not in st.session_state:
    st.session_state.last_context = []

# Helper functions
def format_timestamp(timestamp_str):
    """Format a timestamp string into a readable format"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%d %b %Y, %H:%M")
    except:
        return timestamp_str

def fetch_sessions():
    """Fetch all chat sessions from the API"""
    try:
        response = requests.get(f"{API_URL}/chat/sessions")
        if response.status_code == 200:
            st.session_state.sessions = response.json()
        else:
            st.error(f"Error fetching sessions: {response.text}")
    except Exception as e:
        st.error(f"Failed to connect to backend: {str(e)}")

def fetch_messages(session_id):
    """Fetch messages for a specific chat session"""
    try:
        response = requests.get(f"{API_URL}/chat/sessions/{session_id}/messages")
        if response.status_code == 200:
            result = response.json()
            if "messages" in result:
                st.session_state.messages = result["messages"]
            else:
                st.session_state.messages = []
                st.error("Unexpected response format: 'messages' key not found")
        else:
            st.error(f"Error fetching messages: {response.text}")
    except Exception as e:
        st.error(f"Failed to fetch messages: {str(e)}")

def create_new_session(title="New Chat"):
    """Create a new chat session"""
    try:
        data = {"title": title}
        response = requests.post(f"{API_URL}/chat/sessions", json=data)
        if response.status_code == 200:
            result = response.json()
            st.session_state.current_session_id = result["id"]
            fetch_sessions()
            fetch_messages(result["id"])
            return True
        else:
            st.error(f"Error creating session: {response.text}")
            return False
    except Exception as e:
        st.error(f"Failed to create session: {str(e)}")
        return False

def send_message(message):
    """Send a message and get response"""
    if not st.session_state.current_session_id:
        # Create a new session if none exists
        if not create_new_session():
            return False
    
    try:
        data = {
            "session_id": st.session_state.current_session_id,
            "message": message
        }
        
        response = requests.post(f"{API_URL}/chat/message", json=data)
        
        if response.status_code == 200:
            # Check if response is JSON and has expected structure
            try:
                result = response.json()
                # Store any context if available
                st.session_state.last_context = result.get("context", [])
            except:
                # Handle case where response might not be JSON
                pass
                
            fetch_messages(st.session_state.current_session_id)
            
            # Update the session title if it's the first message
            current_session = next((s for s in st.session_state.sessions if s["id"] == st.session_state.current_session_id), None)
            if current_session and current_session.get("title") == "New Chat" and len(st.session_state.messages) <= 2:
                # Generate a title from the first user message
                title = message[:30] + "..." if len(message) > 30 else message
                update_session_title(st.session_state.current_session_id, title)
            return True
        else:
            st.error(f"Error sending message: {response.text}")
            return False
    except Exception as e:
        st.error(f"Failed to send message: {str(e)}")
        return False

def delete_session(session_id):
    """Delete a chat session"""
    try:
        response = requests.delete(f"{API_URL}/chat/sessions/{session_id}")
        if response.status_code == 200:
            if st.session_state.current_session_id == session_id:
                st.session_state.current_session_id = None
                st.session_state.messages = []
            fetch_sessions()
            return True
        else:
            st.error(f"Error deleting session: {response.text}")
            return False
    except Exception as e:
        st.error(f"Failed to delete session: {str(e)}")
        return False

def update_session_title(session_id, new_title):
    """Update the title of a chat session"""
    try:
        response = requests.put(
            f"{API_URL}/chat/sessions/{session_id}", 
            json={"title": new_title}
        )
        if response.status_code == 200:
            fetch_sessions()
            return True
        else:
            st.error(f"Error updating session title: {response.text}")
            return False
    except Exception as e:
        st.error(f"Failed to update session title: {str(e)}")
        return False

def toggle_sidebar():
    """Toggle the sidebar state"""
    st.session_state.sidebar_state = "collapsed" if st.session_state.sidebar_state == "expanded" else "expanded"

def handle_new_chat():
    """Handle creating a new chat"""
    st.session_state.current_session_id = None
    st.session_state.messages = []
    st.session_state.new_chat_clicked = True

# Apply custom CSS for ChatGPT-like styling
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #f9f9f9;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #202123;
        color: white;
    }
    
    /* Chat message styling */
    .human-msg {
        background-color: #ffffff;
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .ai-msg {
        background-color: #f0f0f0;
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* Chat input box styling */
    .stTextArea textarea {
        border-radius: 15px;
        border: 1px solid #10a37f;
        padding: 10px;
    }
    
    /* Button styling */
    .stButton button {
        border-radius: 20px;
        background-color: #10a37f;
        color: white;
        border: none;
    }
    
    /* Chat history item styling */
    .chat-history-item {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 5px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    
    .chat-history-item:hover {
        background-color: #343541;
    }
    
    .chat-history-item.active {
        background-color: #444654;
    }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Layout with sidebar and chat area
sidebar = st.sidebar

# Sidebar header with logo and new chat button
with sidebar:
    # Using HTML/CSS for layout since we can't use columns in sidebar
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 style="margin: 0;">💬 ChatGPT</h3>
        <button onclick="window.streamlit:componentEvent('new_chat_clicked', {})" 
                style="background-color: #10a37f; color: white; border: none; 
                       border-radius: 20px; padding: 0.5rem 1rem; cursor: pointer;">
            + New chat
        </button>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("+ New chat"):
        handle_new_chat()
    
    st.divider()
    
    # Chat history section
    st.subheader("Chat History")
    
    # Display sessions as chat history
    if not st.session_state.sessions:
        fetch_sessions()
    
    # Sort sessions by updated_at (most recent first)
    sorted_sessions = sorted(
        st.session_state.sessions, 
        key=lambda x: x.get("updated_at", ""), 
        reverse=True
    )
    
    for session in sorted_sessions:
        # Check if this is the active session
        is_active = session["id"] == st.session_state.current_session_id
        
        # Add CSS class for styling
        if is_active:
            st.markdown(f"""
            <div class="chat-history-item active">
                {session.get("title", "Untitled")}
            </div>
            """, unsafe_allow_html=True)
        else:
            # Make clickable
            if st.button(
                session.get("title", "Untitled"), 
                key=f"session_{session['id']}",
                use_container_width=True
            ):
                st.session_state.current_session_id = session["id"]
                fetch_messages(session["id"])
                st.experimental_rerun()
        
        # Show a delete button (simplified version without columns)
        if st.button(
            "🗑️",
            key=f"delete_{session['id']}", 
            help="Delete this chat"
        ):
            if delete_session(session["id"]):
                if session["id"] == st.session_state.current_session_id:
                    st.session_state.current_session_id = None
                    st.session_state.messages = []
                st.experimental_rerun()

# Main chat area
main_container = st.container()

with main_container:
    # Chat header
    if st.session_state.current_session_id:
        current_session = next((s for s in st.session_state.sessions if s["id"] == st.session_state.current_session_id), {})
        st.subheader(current_session.get("title", "Chat"))
    else:
        st.subheader("New Chat")
    
    # Message display area
    message_container = st.container(height=500)
    
    with message_container:
        # Display messages
        if st.session_state.current_session_id and not st.session_state.messages:
            fetch_messages(st.session_state.current_session_id)
        
        # Render messages with styling
        for msg in st.session_state.messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "human":
                st.markdown(f"""
                <div class="human-msg">
                    <strong>You:</strong><br>{content}
                </div>
                """, unsafe_allow_html=True)
            elif role == "ai":
                st.markdown(f"""
                <div class="ai-msg">
                    <strong>AI:</strong><br>{content}
                </div>
                """, unsafe_allow_html=True)
    
    # Input area at the bottom
    st.divider()
    
    # Message input with send button
    input_col, button_col = st.columns([6, 1])
    
    with input_col:
        # Handle different Streamlit versions for label_visibility
        try:
            user_input = st.text_area(
                label="Message Input", 
                placeholder="Message ChatGPT...", 
                key="user_input", 
                height=80,
                label_visibility="collapsed"
            )
        except:
            # Fallback for older Streamlit versions
            user_input = st.text_area(
                label="",  # Empty label for older versions
                placeholder="Message ChatGPT...", 
                key="user_input", 
                height=80
            )
    
    with button_col:
        st.write("")  # Add some space
        st.write("")  # Add some space
        if st.button(label="Send", key="send_button", use_container_width=True):
            if user_input:
                if send_message(user_input):
                    st.session_state.user_input = ""
                    st.experimental_rerun()
            else:
                st.warning("Please type a message first", icon="⚠️")

# Create new chat automatically if button was clicked
if st.session_state.new_chat_clicked:
    st.session_state.new_chat_clicked = False
    create_new_session()
    st.experimental_rerun()