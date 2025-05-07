from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from typing import List, Dict, Any
import uvicorn
from datetime import datetime
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MongoDB connection
def get_mongo_client():
    username = os.getenv("DB_USERNAME", "arnabjay")
    password = os.getenv("DB_PASSWORD", "T2EjuV7askptx6pM")
    encoded_password = quote_plus(password)
    connection_string = (
        f"mongodb+srv://{username}:{encoded_password}@"
        "cluster0.bct41gd.mongodb.net/"
        "?retryWrites=true&w=majority&appName=Cluster0"
    )
    return MongoClient(connection_string)

client = get_mongo_client()
db = client["atrina"]
collection = db["atrina_test"]

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/test/documents")
async def get_test_documents():
    """Get all documents for testing purposes"""
    documents = list(collection.find().sort("updated_at", -1).limit(10))
    for doc in documents:
        doc["_id"] = str(doc["_id"])
        if "audio_id" in doc:
            doc["audio_id"] = str(doc["audio_id"])
    return documents

@app.get("/test/analyze/{document_id}")
async def analyze_test_document(document_id: str):
    """Analyze a specific document with test categories"""
    doc = collection.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    text = doc.get("text", "")
    title = doc.get("title", "Untitled")
    
    # Simple test analysis - counts words and characters
    word_count = len(text.split())
    char_count = len(text)
    created_date = doc.get("created_at", datetime.now())
    
    # Simple sentiment (placeholder - would use NLP in real implementation)
    positive_words = ["good", "great", "excellent", "happy", "success"]
    negative_words = ["bad", "poor", "fail", "unhappy", "problem"]
    
    positive = sum(text.lower().count(word) for word in positive_words)
    negative = sum(text.lower().count(word) for word in negative_words)
    sentiment = "Positive" if positive > negative else "Negative" if negative > positive else "Neutral"
    
    return {
        "document_id": document_id,
        "title": title,
        "word_count": word_count,
        "char_count": char_count,
        "created_date": created_date.isoformat(),
        "sentiment": sentiment,
        "positive_words": positive,
        "negative_words": negative,
        "analysis_date": datetime.now().isoformat()
    }

@app.get("/test/stats")
async def get_test_stats():
    """Get basic statistics about the documents"""
    total_docs = collection.count_documents({})
    oldest = collection.find_one(sort=[("created_at", 1)])
    newest = collection.find_one(sort=[("created_at", -1)])
    
    return {
        "total_documents": total_docs,
        "oldest_document": {
            "id": str(oldest["_id"]),
            "title": oldest.get("title", "Untitled"),
            "created_at": oldest["created_at"].isoformat()
        },
        "newest_document": {
            "id": str(newest["_id"]),
            "title": newest.get("title", "Untitled"),
            "created_at": newest["created_at"].isoformat()
        },
        "analysis_date": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("test_backend:app", host="0.0.0.0", port=8001, reload=True)