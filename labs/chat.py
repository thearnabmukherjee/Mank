
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
        
    except ConnectionError as e:
            raise HTTPException(status_code=503, detail="Service unavailable: " + str(e))
    except Exception as e:
            raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))

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



