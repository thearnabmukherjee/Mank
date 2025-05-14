import streamlit as st
import requests

# FastAPI backend URL
API_URL = "http://localhost:8000/chat"  # Update if hosted elsewhere

st.set_page_config(page_title="Qdrant Hybrid Chatbot", layout="centered")

st.title("💊 Qdrant Hybrid Search Chatbot")
st.write("Ask a question about prescriptions, medicines, or sales commitment.")

# Session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# User input
user_query = st.text_input("Enter your query:", placeholder="e.g., Strong prescriptions for Codistaz")

if st.button("Submit") and user_query.strip():
    with st.spinner("Searching Qdrant..."):
        response = requests.post(API_URL, json={"query": user_query})
        result = response.json()

        # Store and display chat history
        st.session_state.chat_history.append(("You", user_query))
        st.session_state.chat_history.append(("Bot", result))

# Display chat history
st.subheader("Chat History")
for speaker, message in reversed(st.session_state.chat_history):
    if speaker == "You":
        st.markdown(f"**🧑‍💻 {speaker}:** {message}")
    else:
        st.markdown(f"**🤖 {speaker}:**")
        for match in message["matches"]:
            st.markdown(f"""
- **Medicine:** {match['medicine_name']}
- **Label:** {match['label']}
- **Reason:** {match['label_reason']}
- **Score:** {match['score']:.4f}
---
""")
