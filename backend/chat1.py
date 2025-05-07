from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain.memory import ConversationBufferMemory
from openai import OpenAI
from qdrant import qdrant_service

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize MongoDB connection
def get_mongo_client():
    username = os.getenv("DB_USERNAME", "arnabjay")
    password = os.getenv("DB_PASSWORD", "T2EjuV7askptx6pM")
    
    connection_string = (
        f"mongodb+srv://{username}:{password}@"
        "cluster0.bct41gd.mongodb.net/"
        "?retryWrites=true&w=majority&appName=Cluster0"
    )
    
    return MongoClient(connection_string,
        tls=True,
        tlsAllowInvalidCertificates=True,
        retryWrites=True,
        w="majority"
    )

client = get_mongo_client()
db = client["atrina"]
chat_collection = db["chat_sessions"]
messages_collection = db["chat_messages"]

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatSessionCreate(BaseModel):
    title: str
    medicine_name: Optional[str] = None

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None

class ChatRequest(BaseModel):
    session_id: str
    message: str
    medicine_name: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    message: str
    context: Optional[Dict[str, Any]] = None

# Helper functions
def convert_object_id(doc):
    """Convert ObjectId to string in a document"""
    if doc is None:
        return None
    
    doc["id"] = str(doc.pop("_id"))
    return doc

def get_chat_session(session_id: str):
    """Get chat session by ID"""
    try:
        session = chat_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        return convert_object_id(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat session: {str(e)}")

def get_message_history(session_id: str):
    """Get LangChain MongoDB message history for a session"""
    connection_string = os.getenv("MONGODB_URI", client.address[0])
    return MongoDBChatMessageHistory(
        connection_string=connection_string,
        database_name="atrina",
        collection_name="chat_messages",
        session_id=session_id
    )

def get_rag_context(query: str, medicine_name: Optional[str] = None, limit: int = 3):
    """Get RAG context from Qdrant based on query"""
    context = []
    
    # If medicine name is provided, search in that medicine's documents
    if medicine_name:
        results = qdrant_service.search_by_medicine_and_label(medicine_name, None, limit)
        
        # Add more context with semantic search if not enough results
        if len(results) < limit:
            similarity_results = qdrant_service.search_similar(query, limit - len(results))
            results.extend(similarity_results)
    else:
        # Just do semantic search
        results = qdrant_service.search_similar(query, limit)
    
    # Format results for context
    for result in results:
        payload = result.get("payload", {})
        medicine = payload.get("medicine_name", "Unknown")
        label = payload.get("label", "")
        reason = payload.get("label_reason", "")
        
        context_item = {
            "medicine": medicine,
            "label": label,
            "reason": reason,
            "relevance_score": result.get("score", 0)
        }
        context.append(context_item)
    
    return context

def generate_assistant_response(query: str, history_messages: List[Dict], context: List[Dict]):
    """Generate response using OpenAI with context"""
    
    # Format context for the system prompt
    context_text = ""
    for ctx in context:
        context_text += f"- Medicine: {ctx['medicine']}\n"
        context_text += f"  Label: {ctx['label']}\n"
        context_text += f"  Reason: {ctx['reason']}\n\n"
    
    system_prompt = f"""You are an AI medical information assistant that helps users understand medical data.
Use the following context information to answer the user's question:

{context_text}

If the context doesn't contain enough information to answer the question, you can say you don't have enough information.
Keep your answers focused on the information in the context and be concise but informative.
"""
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    for msg in history_messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add the current query
    messages.append({"role": "user", "content": query})
    
    try:
        response = openai_client.chat.completions.create(
            model="o3-mini", 
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return "I'm sorry, I couldn't generate a response at this time."

# Routes
@router.post("/sessions")
async def create_chat_session(chat_data: ChatSessionCreate):
    """Create a new chat session"""
    session = {
        "title": chat_data.title,
        "medicine_name": chat_data.medicine_name,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "is_archived": False,
        "message_count": 0
    }
    
    try:
        result = chat_collection.insert_one(session)
        session_id = str(result.inserted_id)
        
        # Initialize message history
        history = get_message_history(session_id)
        history.add_user_message("Hello")
        history.add_ai_message("Hi! How can I help you with medical information today?")
        
        # Update message count
        chat_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"message_count": 2}}
        )
        
        return {"id": session_id, "title": chat_data.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating chat session: {str(e)}")

@router.get("/sessions")
async def get_chat_sessions(archived: bool = False):
    """Get all chat sessions"""
    try:
        sessions = list(chat_collection.find({"is_archived": archived}).sort("updated_at", -1))
        return [convert_object_id(session) for session in sessions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat sessions: {str(e)}")

@router.get("/sessions/{session_id}")
async def get_chat_session_by_id(session_id: str):
    """Get chat session by ID"""
    return get_chat_session(session_id)

@router.put("/sessions/{session_id}")
async def update_chat_session(session_id: str, session_data: ChatSessionUpdate):
    """Update chat session"""
    session = get_chat_session(session_id)
    
    update_data = {"updated_at": datetime.now()}
    if session_data.title is not None:
        update_data["title"] = session_data.title
    if session_data.is_archived is not None:
        update_data["is_archived"] = session_data.is_archived
    
    try:
        result = chat_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {"id": session_id, **update_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating chat session: {str(e)}")

@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete chat session and its messages"""
    session = get_chat_session(session_id)
    
    try:
        # Delete messages
        messages_collection.delete_many({"session_id": session_id})
        
        # Delete session
        result = chat_collection.delete_one({"_id": ObjectId(session_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {"id": session_id, "deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting chat session: {str(e)}")

@router.get("/sessions/{session_id}/messages")
async def get_chat_messages(session_id: str):
    """Get all messages for a chat session"""
    session = get_chat_session(session_id)
    
    try:
        history = get_message_history(session_id)
        messages = history.messages
        
        return {"session_id": session_id, "messages": [{"role": msg.type, "content": msg.content} for msg in messages]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chat messages: {str(e)}")

@router.post("/message")
async def send_message(chat_request: ChatRequest):
    """Process a chat message and get response"""
    session = get_chat_session(chat_request.session_id)
    
    # Get or use medicine name from request or session
    medicine_name = chat_request.medicine_name or session.get("medicine_name")
    
    try:
        # Get message history
        history = get_message_history(chat_request.session_id)
        
        # Get context from Qdrant
        context = get_rag_context(chat_request.message, medicine_name)
        
        # Add user message to history
        history.add_user_message(chat_request.message)
        
        # Get all messages for context
        messages = [{"role": msg.type, "content": msg.content} for msg in history.messages]
        
        # Generate response
        response_text = generate_assistant_response(chat_request.message, messages, context)
        
        # Add assistant response to history
        history.add_ai_message(response_text)
        
        # Update session
        chat_collection.update_one(
            {"_id": ObjectId(chat_request.session_id)},
            {
                "$set": {"updated_at": datetime.now()},
                "$inc": {"message_count": 2}
            }
        )
        
        return {
            "session_id": chat_request.session_id,
            "message": response_text,
            "context": context
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")