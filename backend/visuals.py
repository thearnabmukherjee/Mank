from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import uvicorn
import ssl
import certifi
import google.generativeai as genai
from pydantic import BaseModel
import json
import logging
from bson import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# MongoDB Configuration
def get_mongo_client():
    username = os.getenv("DB_USERNAME", "arnabjay")
    password = os.getenv("DB_PASSWORD", "T2EjuV7askptx6pM")
    encoded_password = quote_plus(password)
    
    connection_string = (
        f"mongodb+srv://{username}:{encoded_password}@"
        "cluster0.bct41gd.mongodb.net/"
        "?retryWrites=true&w=majority&appName=Cluster0"
    )
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return MongoClient(
        connection_string,
        tls=True,
        tlsCAFile=certifi.where()
    )

client = get_mongo_client()
db = client["atrina"]
collection = db["atrina_test"]

# Gemini AI Configuration
# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# model = genai.GenerativeModel('gemini-2.0-flash')

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
class MedicineCategory(BaseModel):
    medicine_name: str
    related_labels: List[str]

class CategorizedLabelsResponse(BaseModel):
    medicine_categories: List[MedicineCategory]

class BulkLabelResponse(BaseModel):
    status: str
    total_documents: int
    processed_documents: int
    labels_generated: int

# Helper Functions
# def extract_labels_from_text(text: str) -> List[str]:
#     """Enhanced medicine-focused label extraction"""
#     try:
#         prompt = """
#         Analyze this medical transcript and extract specific medicine-related labels.
#         Focus on these aspects:

#         1. Medicine Names (Brand/Generic names)
#         2. Doctor Opinions (Positive/Negative/Neutral)
#         3. Product Comparisons (vs other medicines)
#         4. Patient Outcomes (Effectiveness, results)
#         5. Safety Concerns (Side effects, warnings)
#         6. Dosage Information
#         7. Cost/Pricing Information
#         8. Market Availability

#         RULES:
#         - Extract ALL relevant attributes
#         - Labels MUST be unique and specific
#         - Never repeat similar labels
#         - Format as comma-separated values

#         Example Output:
#         Positive doctor feedback, Product comparison, Side effects mentioned

#         Transcript:
#         {transcript}

#         Provide ONLY the labels, comma-separated.
#         """.format(transcript=text[:10000])  # Limit text length

#         response = model.generate_content(prompt)

#         if response.text:
#             # Clean and deduplicate labels
#             labels = [label.strip() for label in response.text.split(",") if label.strip()]
#             return list(set(labels))  # Remove duplicates
#         return []
#     except Exception as e:
#         logger.error(f"Error extracting labels: {str(e)}")
#         return []

def categorize_labels_by_medicine(labels_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Categorize labels based on pre-existing medicine_name field"""
    try:
        categories_dict = {}
        
        for item in labels_data:
            # Safely get medicine_name with default to "General"
            medicine_name = item.get("medicine_name", "General")
            if not isinstance(medicine_name, str):
                medicine_name = "General"
            
            labels = item.get("labels", [])
            if not isinstance(labels, list):
                continue
                
            if medicine_name not in categories_dict:
                categories_dict[medicine_name] = set()  # Using set to avoid duplicates
            
            # Add only valid string labels
            for label in labels:
                if isinstance(label, str) and label.strip():
                    categories_dict[medicine_name].add(label.strip())
        
        # Convert to the required format and sort labels
        categories = [
            {
                "medicine_name": med, 
                "related_labels": sorted(list(labels))  # Sort labels alphabetically
            } 
            for med, labels in categories_dict.items()
        ]
        
        # Sort categories by medicine name
        categories.sort(key=lambda x: x["medicine_name"])
        
        return categories
        
    except Exception as e:
        logger.error(f"Failed to categorize labels: {str(e)}")
        # Return empty list instead of failing
        return []

# API Endpoints
# @app.post("/bulk-extract-labels/", response_model=BulkLabelResponse)
# async def bulk_extract_labels(background_tasks: BackgroundTasks):
#     """Trigger background label extraction"""
#     background_tasks.add_task(process_bulk_label_extraction)
#     return {
#         "status": "Bulk extraction started",
#         "total_documents": collection.count_documents({}),
#         "processed_documents": collection.count_documents({"labels": {"$exists": True}}),
#         "labels_generated": 0
#     }

@app.get("/bulk-extract-labels/status", response_model=BulkLabelResponse)
async def get_bulk_extract_status():
    """Get extraction status"""
    total = collection.count_documents({})
    processed = collection.count_documents({"labels": {"$exists": True}})
    pipeline = [{"$unwind": "$labels"}, {"$group": {"_id": None, "count": {"$sum": 1}}}]
    result = list(collection.aggregate(pipeline))
    return {
        "status": "complete" if processed >= total else "in progress",
        "total_documents": total,
        "processed_documents": processed,
        "labels_generated": result[0]["count"] if result else 0
    }

@app.get("/labels/all", response_model=List[str])
async def get_all_labels():
    """Get all unique labels"""
    try:
        pipeline = [
            {"$match": {"labels": {"$exists": True}}},
            {"$unwind": "$labels"},
            {"$group": {"_id": "$labels"}},
            {"$sort": {"_id": 1}}
        ]
        labels = list(collection.aggregate(pipeline))
        return [label["_id"] for label in labels]
    except Exception as e:
        logger.error(f"Error fetching labels: {str(e)}")
        raise HTTPException(500, detail=str(e))

@app.get("/labels/categorized", response_model=CategorizedLabelsResponse)
async def get_categorized_labels():
    """Get categorized labels using medicine_name field"""
    try:
        # Get all documents with labels and medicine_name
        pipeline = [
            {"$match": {"labels": {"$exists": True}, "medicine_name": {"$exists": True}}},
            {"$project": {"medicine_name": 1, "labels": 1}}
        ]
        documents = list(collection.aggregate(pipeline))
        
        # If no documents with medicine_name, fallback to general categorization
        if not documents:
            pipeline = [
                {"$match": {"labels": {"$exists": True}}},
                {"$project": {"labels": 1}}
            ]
            documents = list(collection.aggregate(pipeline))
            documents = [{"medicine_name": "General", "labels": doc["labels"]} for doc in documents]
        
        # Categorize by medicine_name
        categories = categorize_labels_by_medicine(documents)
        
        return CategorizedLabelsResponse(
            medicine_categories=[MedicineCategory(**cat) for cat in categories]
        )

    except Exception as e:
        logger.error(f"Error in get_categorized_labels: {str(e)}")
        raise HTTPException(500, detail=str(e))

# Background Task
# def process_bulk_label_extraction():
#     """Process documents for label extraction"""
#     try:
#         for doc in collection.find({"labels": {"$exists": False}}):  # Fixed missing closing brace and quote
#             if doc.get("text"):
#                 labels = extract_labels_from_text(doc["text"])
#                 if labels:
#                     collection.update_one(
#                         {"_id": doc["_id"]},
#                         {"$set": {"labels": labels}}
#                     )
#     except Exception as e:
#         logger.error(f"Bulk extraction error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("visuals:app", host="0.0.0.0", port=8001, reload=True)