# # import streamlit as st
# # from qdrant import qdrant_service  # Don't change qdrant.py
# # from openai import OpenAI
# # import os
# # from dotenv import load_dotenv

# # # Load env vars
# # load_dotenv()
# # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# # # Page setup
# # st.set_page_config(page_title="Qdrant Chatbot", layout="centered")
# # st.title("💬 Qdrant-Powered Chatbot")
# # st.markdown("Ask me about medicines and labels from your Qdrant DB.")

# # # Session state
# # if "messages" not in st.session_state:
# #     st.session_state.messages = []

# # # Display chat history
# # for msg in st.session_state.messages:
# #     with st.chat_message(msg["role"]):
# #         st.markdown(msg["content"])

# # # # --- Summarization helper ---
# # # def summarize_results(results, query):
# # #     context = "\n\n".join([
# # #         f"Medicine: {hit['payload'].get('medicine_name', 'Unknown')}\n"
# # #         f"Label: {hit['payload'].get('label', 'None')}\n"
# # #         f"Reason: {hit['payload'].get('label_reason', 'No reason')}"
# # #         for hit in results
# # #     ])

# # #     system_prompt = (
# # #         "You are a helpful medical assistant. Use the following context from a medicine knowledge base "
# # #         "to answer the user's question clearly and thoroughly."
# # #     )

# # #     messages = [
# # #         {"role": "system", "content": system_prompt},
# # #         {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
# # #     ]

# # #     response = openai.ChatCompletion.create(
# # #         model="gpt-4",
# # #         messages=messages,
# # #         temperature=0.4
# # #     )

# # #     return response.choices[0].message.content.strip()

# # def summarize_results(results, query):
# #     context = "\n\n".join([
# #         f"Medicine: {hit['payload'].get('medicine_name', 'Unknown')}\n"
# #         f"Label: {hit['payload'].get('label', 'None')}\n"
# #         f"Reason: {hit['payload'].get('label_reason', 'No reason')}"
# #         for hit in results
# #     ])

# #     system_prompt = (
# #         "You are a helpful medical assistant. Use the following context from a medicine knowledge base "
# #         "to answer the user's question clearly and thoroughly."
# #     )

# #     response = client.chat.completions.create(
# #         model="gpt-4",
# #         messages=[
# #             {"role": "system", "content": system_prompt},
# #             {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
# #         ],
# #         temperature=0.4,
# #     )

# #     return response.choices[0].message.content.strip()


# # # --- Chat interaction ---
# # query = st.chat_input("Ask your question here...")

# # if query:
# #     st.session_state.messages.append({"role": "user", "content": query})
# #     with st.chat_message("user"):
# #         st.markdown(query)

# #     with st.chat_message("assistant"):
# #         with st.spinner("Searching Qdrant..."):
# #             results = qdrant_service.search_similar(query, limit=5)

# #         if results:
# #             with st.spinner("Summarizing with GPT..."):
# #                 final_response = summarize_results(results, query)
# #         else:
# #             final_response = "Sorry, I couldn’t find anything relevant in the vector database."

# #         st.markdown(final_response)
# #         st.session_state.messages.append({"role": "assistant", "content": final_response})




# # # import streamlit as st
# # # import os
# # # from dotenv import load_dotenv
# # # from openai import OpenAI
# # # from qdrant_client import QdrantClient
# # # from qdrant_client.models import SearchParams
# # # import warnings

# # # # Suppress specific warnings
# # # warnings.filterwarnings("ignore", category=UserWarning, message="Failed to obtain server version")

# # # # Load environment variables
# # # load_dotenv()
# # # openai_api_key = os.getenv("OPENAI_API_KEY")
# # # qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
# # # collection_name = os.getenv("QDRANT_COLLECTION", "medicines")
# # # embedding_model = "text-embedding-ada-002"

# # # # Initialize clients with explicit settings
# # # try:
# # #     client = OpenAI(api_key=openai_api_key)
# # #     qdrant = QdrantClient(
# # #         url=qdrant_url,
# # #         timeout=30,
# # #         prefer_grpc=False,
# # #         check_compatibility=False  # This explicitly disables version checking
# # #     )
# # # except Exception as e:
# # #     st.error(f"Initialization failed: {str(e)}")
# # #     st.stop()

# # # def embed_text(text: str) -> list[float]:
# # #     """Generate embeddings using OpenAI with error handling"""
# # #     try:
# # #         response = client.embeddings.create(
# # #             input=[text],
# # #             model=embedding_model,
# # #         )
# # #         return response.data[0].embedding
# # #     except Exception as e:
# # #         st.error(f"Failed to generate embeddings: {str(e)}")
# # #         return []

# # # def query_qdrant(query: str, limit: int = 3) -> list:
# # #     """Query Qdrant using modern methods with full error handling"""
# # #     vector = embed_text(query)
# # #     if not vector:
# # #         return []

# # #     try:
# # #         return qdrant.search(
# # #             collection_name=collection_name,
# # #             query_vector=vector,
# # #             limit=limit,
# # #             search_params=SearchParams(hnsw_ef=128),
# # #         )
# # #     except Exception as e:
# # #         st.error(f"Database query failed: {str(e)}")
# # #         return []

# # # # Streamlit UI Configuration
# # # st.set_page_config(page_title="Medicine Q&A", layout="centered")
# # # st.title("💊 Medicine Information Assistant")
# # # st.caption("Ask about drug labels and safety information")

# # # # Initialize chat history
# # # if "messages" not in st.session_state:
# # #     st.session_state.messages = []

# # # # Display existing messages
# # # for message in st.session_state.messages:
# # #     with st.chat_message(message["role"]):
# # #         st.markdown(message["content"])

# # # # Process user input
# # # if prompt := st.chat_input("Ask about a medicine..."):
# # #     # Add user message to history
# # #     st.session_state.messages.append({"role": "user", "content": prompt})
# # #     with st.chat_message("user"):
# # #         st.markdown(prompt)

# # #     # Generate response
# # #     with st.chat_message("assistant"):
# # #         with st.spinner("Analyzing medical information..."):
# # #             results = query_qdrant(prompt)

# # #         if results:
# # #             context = "\n".join(
# # #                 f"• {hit.payload.get('medicine_name', 'Unknown')}: "
# # #                 f"{hit.payload.get('label', 'No label available')}\n"
# # #                 f"  Reason: {hit.payload.get('label_reason', 'Not specified')}"
# # #                 for hit in results
# # #             )

# # #             try:
# # #                 response = client.chat.completions.create(
# # #                     model="gpt-3.5-turbo",
# # #                     messages=[{
# # #                         "role": "system",
# # #                         "content": "You are a medical information specialist. "
# # #                                   "Provide accurate, concise answers based on the context."
# # #                     }, {
# # #                         "role": "user",
# # #                         "content": f"Context:\n{context}\n\nQuestion: {prompt}"
# # #                     }],
# # #                     temperature=0.2
# # #                 )
# # #                 answer = response.choices[0].message.content
# # #             except Exception as e:
# # #                 answer = f"⚠️ Error generating response: {str(e)}"
# # #         else:
# # #             answer = "No matching information found in our database."

# # #         st.markdown(answer)
# # #         st.session_state.messages.append({"role": "assistant", "content": answer})




# # simple_chatbot.py

# import streamlit as st
# from qdrant_client import QdrantClient
# from qdrant_client.http.models import Filter, FieldCondition, MatchValue

# # Connect to Qdrant
# client = QdrantClient("http://localhost:6333")  # Adjust to your host
# collection_name = "your_collection_name"  # Replace with your actual collection name

# st.title("🧠 Medicine Label Chatbot")

# user_query = st.text_input("Ask about a medicine label (e.g., 'availability'):")

# if user_query:
#     # Example: Match "Availability Assurance" if user mentions "availability"
#     if "availability" in user_query.lower():
#         label_value = "Availability Assurance"
#     else:
#         st.warning("Only 'Availability Assurance' supported in this demo.")
#         st.stop()

#     # Apply payload filter
#     filter_ = Filter(
#         must=[
#             FieldCondition(
#                 key="label",
#                 match=MatchValue(value=label_value)
#             )
#         ]
#     )

#     # Query Qdrant using scroll (no vector needed)
#     points, _ = client.scroll(
#         collection_name=collection_name,
#         scroll_filter=filter_,
#         limit=10
#     )

#     st.subheader("Results:")

#     if not points:
#         st.info("No matching records found.")
#     else:
#         for pt in points:
#             st.write(f"**Medicine Name:** {pt.payload.get('medicine_name')}")
#             st.write(f"**Label:** {pt.payload.get('label')}")
#             st.write(f"**Reason:** {pt.payload.get('label_reason')}")
#             st.markdown("---")







import streamlit as st
from qdrant_service import QdrantService

# Initialize QdrantService
qdrant_service = QdrantService()

# Streamlit app configuration
st.set_page_config(page_title="Qdrant Chatbot", layout="wide")
st.title("Qdrant Chatbot")

# Sidebar for user instructions
st.sidebar.title("Instructions")
st.sidebar.markdown("""
- Enter your query in the text box.
- The chatbot will fetch the relevant data from Qdrant based on your query.
- You can search for similar documents, specific medicines, or labels.
""")

# User query input
query_type = st.radio("Choose the type of query:", ["Search Similar Documents", "Search by Medicine and Label"])
user_query = st.text_input("Enter your query:")

# For Search by Medicine and Label
medicine_name = ""
label = ""
if query_type == "Search by Medicine and Label":
    medicine_name = st.text_input("Enter Medicine Name:")
    label = st.text_input("Enter Label (Optional):")

# Button to trigger the query
if st.button("Search"):
    if query_type == "Search Similar Documents":
        if user_query.strip():
            st.info(f"Searching for documents similar to: '{user_query}'")
            results = qdrant_service.search_similar(text=user_query)
            if results:
                st.success("Results fetched successfully!")
                for idx, result in enumerate(results):
                    st.subheader(f"Result {idx + 1}")
                    st.write(f"**ID:** {result['id']}")
                    st.write(f"**Score:** {result['score']}")
                    st.write(f"**Payload:**")
                    st.json(result['payload'])
            else:
                st.warning("No similar documents found.")
        else:
            st.error("Please enter a valid query to search for similar documents.")
    elif query_type == "Search by Medicine and Label":
        if medicine_name.strip():
            st.info(f"Searching for Medicine: '{medicine_name}' and Label: '{label}'")
            results = qdrant_service.search_by_medicine_and_label(medicine_name=medicine_name, label=label)
            if results:
                st.success("Results fetched successfully!")
                for idx, result in enumerate(results):
                    st.subheader(f"Result {idx + 1}")
                    st.write(f"**ID:** {result['id']}")
                    st.write(f"**Score:** {result['score']}")
                    st.write(f"**Payload:**")
                    st.json(result['payload'])
            else:
                st.warning("No documents found for the given medicine and label.")
        else:
            st.error("Please enter a valid medicine name to search.")

# Footer
st.sidebar.markdown("---")
st.sidebar.subheader("About")
st.sidebar.info("""
This chatbot fetches data from Qdrant based on your queries. 
You can search for similar documents or find documents by a specific medicine and label.
""")