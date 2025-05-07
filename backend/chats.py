# # from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory 


# # chat_message_history = MongoDBChatMessageHistory(
# #     session_id="test_session",
# #     connection_string="mongodb://mongo_user:password123@mongo:27017",
# #     database_name="my_db",
# #     collection_name="chat_histories",
# # )

# # chat_message_history.messages



# import os
# from datetime import datetime
# from typing import List, Dict, Optional
# from fastapi import FastAPI, HTTPException, Depends
# from pymongo import MongoClient
# from langchain_qdrant import Qdrant
# from bson import ObjectId
# from dotenv import load_dotenv
# from qdrant_client import QdrantClient
# from qdrant_client.models import Filter, FieldCondition
# from langchain.memory import MongoDBChatMessageHistory
# from langchain_core.messages import HumanMessage, AIMessage
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from langchain.chains import RetrievalQA
# from langchain.vectorstores import Qdrant
# from pydantic import BaseModel 
# # Load environment variables
# load_dotenv()

# app = FastAPI()

# # Initialize connections
# mongo_client = MongoClient(os.getenv("MONGO_URI"))
# db = mongo_client["atrina"]
# qdrant_client = QdrantClient(
#     url=os.getenv("QDRANT_URL"),
#     api_key=os.getenv("QDRANT_API_KEY")
# )

# # Initialize models
# embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
# llm = ChatOpenAI(model="gpt-4", temperature=0.1, api_key=os.getenv("OPENAI_API_KEY"))

# # Initialize Qdrant vector store
# vector_store = Qdrant(
#     client=qdrant_client,
#     collection_name="mongodb_to_qdrant",
#     embeddings=embeddings
# ) 

# class ChatRequest(BaseModel):
#     message: str
#     medicine_name: Optional[str] = ""

# class ChatService:
#     def __init__(self):
#         self.insights_collection = db["atrina"]
#         self.chat_history_collection = db["chat_histories"]

#     def get_chat_history(self, session_id: str) -> MongoDBChatMessageHistory:
#         return MongoDBChatMessageHistory(
#             connection_string=os.getenv("MONGO_URI"),
#             database_name="atrina",
#             collection_name="chat_histories",
#             session_id=session_id
#         )

#     # async def chat_with_medicine(
#     #     self,
#     #     session_id: str,
#     #     message: str,
#     #     medicine_name: Optional[str] = None
#     # ) -> Dict:
#     #     """Process chat message with medical context"""
#     #     try:
#     #         # Setup chat history
#     #         history = self.get_chat_history(session_id)
#     #         history.add_user_message(message)

#     #         # Build retrieval filter
#     #         filter_ = Filter(must=[
#     #             FieldCondition(key="medicine_name", match={"value": medicine_name})
#     #         ]) if medicine_name else None

#     #         # Create retrieval chain
#     #         qa_chain = RetrievalQA.from_chain_type(
#     #             llm=llm,
#     #             chain_type="stuff",
#     #             retriever=vector_store.as_retriever(
#     #                 search_kwargs={"filter": filter_, "k": 3}
#     #             ),
#     #             return_source_documents=True
#     #         )

#     #         # Get response
#     #         result = await qa_chain.ainvoke({
#     #             "query": message,
#     #             "chat_history": history.messages
#     #         })

#     #         # Store AI response
#     #         history.add_ai_message(result["result"])

#     #         return {
#     #             "response": result["result"],
#     #             "sources": [doc.metadata for doc in result["source_documents"]],
#     #             "session_id": session_id,
#     #             "timestamp": datetime.now()
#     #         }

#     #     except Exception as e:
#     #         raise HTTPException(status_code=500, detail=str(e))

#     async def chat_with_medicine(
#         self,
#         session_id: str,
#         message: str,
#         medicine_name: Optional[str] = None
#     ) -> Dict:
#         """Process chat message with medical context"""
#         try:
#             # Setup chat history
#             history = self.get_chat_history(session_id)
#             history.add_user_message(message)

#             # Build retrieval filter - ensure medicine_name is properly handled
#             filter_ = None
#             if medicine_name and medicine_name.strip():
#                 filter_ = Filter(must=[
#                     FieldCondition(key="medicine_name", match={"value": medicine_name.strip()})
#                 ])

#             # Create retrieval chain with proper input handling
#             qa_chain = RetrievalQA.from_chain_type(
#                 llm=llm,
#                 chain_type="stuff",
#                 retriever=vector_store.as_retriever(
#                     search_kwargs={"filter": filter_, "k": 3} if filter_ else {"k": 3}
#                 ),
#                 return_source_documents=True
#             )

#             # Get response with properly formatted input
#             result = await qa_chain.ainvoke({
#                 "query": message,
#                 "chat_history": [msg.dict() for msg in history.messages]
#             })

#             # Store AI response
#             history.add_ai_message(result["result"])

#             return {
#                 "response": result["result"],
#                 "sources": [doc.metadata for doc in result["source_documents"]],
#                 "session_id": session_id,
#                 "timestamp": datetime.now().isoformat()
#             }
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))

#     async def get_chat_history(self, session_id: str) -> List[Dict]:
#         """Get formatted chat history"""
#         history = self.get_chat_history(session_id)
#         return [
#             {
#                 "type": "human" if isinstance(msg, HumanMessage) else "ai",
#                 "content": msg.content,
#                 "timestamp": datetime.now()
#             }
#             for msg in history.messages
#         ]

#     async def generate_insights(self, medicine_name: str) -> Dict:
#         """Generate insights for a medicine"""
#         try:
#             # Search relevant documents
#             docs = vector_store.similarity_search(
#                 query=f"What are the insights for {medicine_name}?",
#                 filter=Filter(must=[
#                     FieldCondition(key="medicine_name", match={"value": medicine_name})
#                 ]),
#                 k=10
#             )

#             if not docs:
#                 raise HTTPException(status_code=404, detail="No documents found")

#             # Generate insights prompt
#             prompt = ChatPromptTemplate.from_messages([
#                 ("system", """You are a pharmaceutical analyst. Generate insights from these documents:
                
#                 {documents}
                
#                 Structure your response with:
#                 1. Key Findings
#                 2. Market Trends
#                 3. Recommendations"""),
#                 ("human", "Generate insights for {medicine_name}")
#             ])

#             chain = prompt | llm | StrOutputParser()
#             insights = await chain.ainvoke({
#                 "documents": "\n\n".join([doc.page_content for doc in docs]),
#                 "medicine_name": medicine_name
#             })

#             # Store insights
#             insight_doc = {
#                 "medicine_name": medicine_name,
#                 "insights": insights,
#                 "sources": [doc.metadata for doc in docs],
#                 "generated_at": datetime.now()
#             }
#             self.insights_collection.insert_one(insight_doc)

#             return insight_doc

#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))

#     async def get_insights_history(self, medicine_name: str, limit: int = 5) -> List[Dict]:
#         """Get historical insights for a medicine"""
#         return list(self.insights_collection.find(
#             {"medicine_name": medicine_name}
#         ).sort("generated_at", -1).limit(limit))

# # Dependency
# def get_chat_service():
#     return ChatService()

# # Chat Endpoints
# @app.post("/chats/{session_id}/message")
# async def chat_message(
#     session_id: str,
#     message: str,
#     medicine_name: Optional[str] = None,
#     service: ChatService = Depends(get_chat_service)
# ):
#     return await service.chat_with_medicine(session_id, message, medicine_name)

# @app.get("/chats/{session_id}/history")
# async def get_chat_history(
#     session_id: str,
#     service: ChatService = Depends(get_chat_service)
# ):
#     return await service.get_chat_history(session_id)

# # Insights Endpoints
# @app.post("/insights/{medicine_name}/generate")
# async def generate_insights(
#     medicine_name: str,
#     service: ChatService = Depends(get_chat_service)
# ):
#     return await service.generate_insights(medicine_name)

# @app.get("/insights/{medicine_name}/history")
# async def get_insights_history(
#     medicine_name: str,
#     limit: int = 5,
#     service: ChatService = Depends(get_chat_service)
# ):
#     return await service.get_insights_history(medicine_name, limit)

# @app.on_event("shutdown")
# async def shutdown_event():
#     mongo_client.close()
#     qdrant_client.close()

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8001)


















from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
from langchain_community.chat_message_histories import MongoDBChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from pymongo import MongoClient
from urllib.parse import quote_plus
from dotenv import load_dotenv
import openai
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, Filter, FieldCondition
import uuid
import ssl
import certifi

# Load environment variables
load_dotenv()

# Initialize MongoDB connection with SSL
def get_mongo_client():
    username = os.getenv("DB_USERNAME", "arnabjay")
    password = os.getenv("DB_PASSWORD", "T2EjuV7askptx6pM")
    encoded_password = quote_plus(password)
    
    connection_string = (
        f"mongodb+srv://{username}:{encoded_password}@"
        "cluster0.bct41gd.mongodb.net/"
        "?retryWrites=true&w=majority&appName=Cluster0"
    )
    
    # SSL configuration
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    return MongoClient(
        connection_string,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsCAFile=certifi.where(),
        retryWrites=True,
        w="majority"
    )

# Qdrant Service Implementation
class QdrantChatService:
    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
        self.collection_name = "mongodb_to_qdrant"
        self._initialize_collection()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def _initialize_collection(self):
        """Initialize or verify the Qdrant collection exists"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            if collection_info.vectors_config.params.size != 1536:
                print("Warning: Existing collection has different vector size")
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )

    def get_text_embedding(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI"""
        try:
            response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding generation failed: {str(e)}")
            return []

    def search_context(self, query: str, medicine_name: Optional[str] = None, limit: int = 3) -> List[Dict]:
        """Search for relevant context in Qdrant"""
        query_embedding = self.get_text_embedding(query)
        if not query_embedding:
            return []

        # Build filter conditions
        filters = []
        if medicine_name:
            filters.append(FieldCondition(key="medicine_name", match={"value": medicine_name}))

        search_filter = Filter(must=filters) if filters else None

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                with_payload=True
            )
            
            return [{
                "payload": hit.payload,
                "score": hit.score
            } for hit in results]
        except Exception as e:
            print(f"Qdrant search failed: {str(e)}")
            return []

# Initialize services
client = get_mongo_client()
db = client["atrina"]
qdrant_service = QdrantChatService()

router = APIRouter(prefix="/chats", tags=["Chat"])

# Models
class ChatMessage(BaseModel):
    message: str
    medicine_name: Optional[str] = None
    session_id: str

class ChatHistoryResponse(BaseModel):
    id: str
    timestamp: datetime
    question: str
    answer: str
    medicine_name: Optional[str] = None
    sources: List[Dict[str, Any]] = []

# Chat service setup
def get_chat_history(session_id: str):
    return MongoDBChatMessageHistory(
        session_id=session_id,
        connection_string=client.get_connection_string(),
        database_name="atrina",
        collection_name="chat_histories"
    )

# Initialize LangChain components
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a medical assistant that will give insights about medicines.
     You will be provided with context from Qdrant and chat history. 
     
     Use the following context to answer questions. Be concise and professional.
     Context: {context}"""),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

chain = prompt | llm | StrOutputParser()

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_chat_history,
    input_messages_key="question",
    history_messages_key="history"
)

@router.post("/{session_id}/message")
async def chat_with_context(
    session_id: str,
    chat_message: ChatMessage,
    background_tasks: BackgroundTasks
):
    """Chat endpoint with Qdrant context and chat history"""
    try:
        # Search for relevant context
        search_results = qdrant_service.search_context(
            query=chat_message.message,
            medicine_name=chat_message.medicine_name,
            limit=3
        )
        
        # Prepare context and sources
        context_parts = []
        sources = []
        
        for result in search_results:
            payload = result.get("payload", {})
            context_parts.append(f"Related info: {payload.get('label_reason', '')}")
            sources.append({
                "medicine_name": payload.get("medicine_name", "Unknown"),
                "label": payload.get("label", "N/A"),
                "score": result.get("score", 0)
            })
        
        context = "\n".join(context_parts) if context_parts else "No specific context found"
        
        # Get LLM response
        response = chain_with_history.invoke(
            {
                "question": chat_message.message,
                "context": context
            },
            config={"configurable": {"session_id": session_id}}
        )
        
        # Store interaction
        background_tasks.add_task(
            store_chat_interaction,
            session_id,
            chat_message.message,
            response,
            chat_message.medicine_name,
            sources
        )
        
        return {
            "response": response,
            "sources": sources
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def store_chat_interaction(
    session_id: str,
    question: str,
    answer: str,
    medicine_name: Optional[str] = None,
    sources: List[Dict] = []
):
    """Store chat interaction in MongoDB"""
    try:
        db["chat_interactions"].insert_one({
            "session_id": session_id,
            "timestamp": datetime.now(),
            "question": question,
            "answer": answer,
            "medicine_name": medicine_name,
            "sources": sources
        })
    except Exception as e:
        print(f"Error storing chat interaction: {str(e)}")

@router.get("/{session_id}/history", response_model=List[ChatHistoryResponse])
async def get_chat_history(session_id: str, limit: int = 20):
    """Get chat history for a session"""
    try:
        history = list(db["chat_interactions"].find(
            {"session_id": session_id}
        ).sort("timestamp", -1).limit(limit))
        
        return [{
            "id": str(msg["_id"]),
            "timestamp": msg["timestamp"],
            "question": msg["question"],
            "answer": msg["answer"],
            "medicine_name": msg.get("medicine_name"),
            "sources": msg.get("sources", [])
        } for msg in history]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))