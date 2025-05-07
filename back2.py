
# import json
# from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
# from fastapi.middleware.cors import CORSMiddleware
# from openai import OpenAI
# from pydantic import BaseModel
# from pymongo import MongoClient
# from datetime import datetime
# from urllib.parse import quote_plus
# import os
# from dotenv import load_dotenv
# import gridfs
# from bson import ObjectId
# from typing import Optional, List, Dict, Any
# import uvicorn
# import ssl
# import certifi
# from qdrant_client import QdrantClient
# from qdrant_client.http import models
# from qdrant_client.http.models import PointStruct
# from concurrent.futures import ThreadPoolExecutor
# import time
# from openai import OpenAI
# # Load environment variables
# load_dotenv()

# # Initialize MongoDB connection with SSL
# def get_mongo_client():
#     username = os.getenv("DB_USERNAME", "arnabjay")
#     password = os.getenv("DB_PASSWORD", "T2EjuV7askptx6pM")
#     encoded_password = quote_plus(password)
    
#     connection_string = (
#         f"mongodb+srv://{username}:{encoded_password}@"
#         "cluster0.bct41gd.mongodb.net/"
#         "?retryWrites=true&w=majority&appName=Cluster0"
#     )
    
#     # SSL configuration
#     ssl_context = ssl.create_default_context(cafile=certifi.where())
#     ssl_context.check_hostname = False
#     ssl_context.verify_mode = ssl.CERT_NONE
    
#     return MongoClient(
#         connection_string,
#         tls=True,
#         tlsAllowInvalidCertificates=True,
#         tlsCAFile=certifi.where(),
#         retryWrites=True,
#         w="majority"
#     )

# client = get_mongo_client()
# db = client["atrina"]
# fs = gridfs.GridFS(db)
# collection = db["atrina_test"]

# # Qdrant Configuration
# qdrant_client = QdrantClient(
#     url=os.getenv("QDRANT_URL", "http://localhost:6333"),
#     api_key=os.getenv("QDRANT_API_KEY"),
# )

# QDRANT_COLLECTION_NAME = "medical_transcripts"
# EMBEDDING_MODEL = "text-embedding-ada-002"

# # Initialize Gemini AI
# client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
# # model = genai.GenerativeModel('gemini-2.0-flash')


# app = FastAPI()

# # CORS configuration
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Models
# class DocumentCreate(BaseModel):
#     text: str
#     title: Optional[str] = None
#     medicine_name: Optional[str] = None

# class DocumentUpdate(BaseModel):
#     text: str
#     title: Optional[str] = None
#     audio_action: Optional[str] = "keep"

# class LabelResponse(BaseModel):
#     label: str
#     document_count: int
#     documents: List[Dict[str, Any]]

# def convert_object_ids(document: Dict[str, Any]) -> Dict[str, Any]:
#     """Convert all ObjectId fields to strings in a document"""
#     if document is None:
#         return None
        
#     document["_id"] = str(document["_id"])
#     if "audio_id" in document:
#         document["audio_id"] = str(document["audio_id"])
#     return document

# # Label extraction utility functions
# def extract_labels_from_text(text: str) -> List[str]:
#     """Use OpenAI-o3-mini to extract labels from text"""
#     prompt = """
# **Objective:**  
# Analyze this medical transcript and extract EXCLUSIVELY business-relevant labels meeting ALL criteria:  
# 1. **Three-word limit** (strictly enforced)  
# 2. **Revenue/Competition/Operations focus** (no clinical terms)  
# 3. **Actionable insights only** (no opinions/feedback)  

# **Allowed Categories:**  
# - Pricing Strategy (discounts, margins, offers)  
# - Market Competition (rival comparisons, switches)  
# - Supply Chain (stock, delivery, launches)  
# - Sales Commitments (prescriptions, quotas)
# - MR  suggestions (feedback, insights)
# - Competition comparisons
# - Market trends (growth, shifts)
# - Feedback

# **Refer the Detailed Section Below for more information**
# ##1.Deeply Understand the Transcript
# -Carefully read the transcript and identify key phrases that indicate business actions, strategies, or insights. Focus on the context of the text to ensure accurate label generation
# and make decision that might not seem import with respect the business action or business insights also double check the transcript and make sure that the label is not related to any clinical or patient-related information or any medicine-related information or Dosage regarding information 
# -Search for the Labels that might most likely be used with respect to the product which will be useful with respect to the business heads which give them better knowledge about the product and the business action or business insights or business strategy which can be used to generate the labels based on that and make sure that the label is not related to any clinical or patient-related information or any medicine-related information or Dosage regarding information
# -Also make a detailed thinking for the keywords selection which keyword would be appropriate regards to Insights 
# -If the keywords already exist then please do not generate the same keywords or word with same meaning again please 
# -make sure that the keywords are not repeated or same meaning or synonyms of the same word




# ### **Label Generation Instructions**:

# 1. **Ensure Uniqueness**:
#    - **Check if the label already exists** in the stored list of labels. If a label is **already present** with the same or similar meaning, **do not generate the new label**.
#    - **Similarity Check**: If a label has a similar **meaning**, use the existing label and avoid creating new ones. For example, if both "Product Prescription Confirmation" and "Product Prescription" exist, they should not both be created as separate labels.

# 2. **Label Extraction Criteria**:
#    - Extract only **business-relevant** labels. These should focus on **market dynamics**, **product performance**, **sales strategies**, **pricing**, and **competitive positioning**.


# ### **Label Extraction Criteria**:

# 1. **Doctor Feedback**:
#    - Extract any feedback from the **doctor** about the **product's effectiveness** or **acceptability**. This could be positive feedback on the product’s benefits or **constructive feedback** on improvements.
#    - **Example Label**: "Doctor Feedback" or "Product Feedback."

# 2. **MR Suggestion**:
#    - Look for instances where the **Medical Representative (MR)** suggests a product to the doctor, including **recommendations**, **usage**, or strategies to enhance adoption.
#    - **Example Label**: "MR Suggestion" or "Sales Suggestion."

# 3. **Market Competition**:
#    - Identify discussions about **competitor products** in the market, including **comparisons**, **pricing**, or **market trends**.
#    - **Example Label**: "Market Competition" or "Competitive Analysis."

# 4. **Product Availability**:
#    - Extract mentions of **product availability** in terms of **stock levels**, **supply chain**, or **timeliness** of product delivery.
#    - **Example Label**: "Product Availability" or "Supply Assurance."

# 5. **Promotional Request**:
#    - Look for requests for **promotional materials**, such as **brochures**, **sample kits**, or **marketing tools** used to support product promotion.
#    - **Example Label**: "Promotional Request" or "Marketing Request."

# 6. **Product Response**:
#    - Extract mentions of how **patients** or **doctors** have responded to the product, including **efficacy**, **side effects**, or overall feedback.
#    - **Example Label**: "Product Response" or "Patient Response."

# 7. **Cost Comparison**:
#    - Identify comparisons of the **product cost** with competitor products, especially regarding **pricing** or **cost-to-therapy**.
#    - **Example Label**: "Cost Comparison" or "Price Comparison."

# 8. **Pricing Advantage**:
#    - Look for references to **pricing advantages** such as **discounts**, **affordable pricing**, or **value for money**.
#    - **Example Label**: "Pricing Advantage" or "Price Advantage."

# 9. **Prescription Duration**:
#    - Extract mentions of the **prescription duration** for the product, whether it's prescribed for **short-term** or **long-term**.
#    - **Example Label**: "Prescription Duration" or "Treatment Duration."

# 10. **Sales Strategy**:
#     - Identify discussions about **sales strategies**, **goals**, or **approaches** to push the product in the market.
#     - **Example Label**: "Sales Strategy" or "Market Strategy."

# 11. **Product Comparison**:
#     - Look for **comparisons** between the product and competing brands, particularly regarding **efficacy**, **pricing**, or **unique features**.
#     - **Example Label**: "Product Comparison" or "Competitive Comparison."

# 12. **Market Launch**:
#     - Extract mentions of the **product launch**, including **timing**, **target markets**, or **expansion** plans.
#     - **Example Label**: "Market Launch" or "Launch Strategy."

# 13. **Prescription Confirmation**:
#     - Identify instances where the doctor or MR confirms they will **prescribe** the product.
#     - **Example Label**: "Prescription Confirmation" or "Product Prescription."

# 14. **Absorption Claim**:
#     - Look for **claims** regarding the **absorption rate**, **bioavailability**, or **effectiveness** of the product.
#     - **Example Label**: "Absorption Claim" or "Efficacy Claim."

# 15. **Counter-Argument**:
#     - Extract statements where the MR or doctor prepares to **counter** claims made by competitors, using data or facts to defend the product’s position.
#     - **Example Label**: "Counter Argument" or "Competitive Counter."

# 16. **Doctor's Suggestion**:
#     - Extract instances where the **doctor** suggests a specific product based on **patient needs** or **clinical outcomes**.
#     - **Example Label**: "Doctor's Suggestion" or "Product Recommendation."

# 17. **Labeling Suggestion**:
#     - Identify any suggestions made regarding changes to the **product label** for better clarity or **regulatory compliance**.
#     - **Example Label**: "Labeling Suggestion" or "Label Changes."

# ---

# ### **Final Output**:
# For each transcript, generate **business-focused labels** related to **market dynamics**, **sales strategies**, **competitive positioning**, and **product performance** in the market. Each label should only contain **two words**.

# ### **Example Output**:
  

# **Examples:**  
# Input: "Will beat CompetitorX's 20% discount if ordered before quarter-end"  
# → `Discount Beat Guarantee,Quarter-End Push,Competitor Price Match`  

# Input: "Guaranteed pharmacy availability in Tier-1 cities by Q3"  
# → `Tier-1 Rollout,Q3 Stock Promise,City-Wide Availability`  

# **Rejection Rules:**  
# 1. Reject if >3 words  
# 2. Reject if clinical/patient-related  
# 3. Reject if vague ("Good Feedback")  
# 4. Reject duplicates/synonyms  
# 5. Anything which is not related to business action or Business strategy or Business insights reject it 
# 6. Reject the Order like ("Order 1000 units") these should be rejected as well
# 7. Reason how can we use the labels in business insights or business action and generate labels based on that

# **Validation Protocol:**  
# 1. Does this label trigger business action?  
# 2. Is it tied to revenue/competition/logistics?  
# 3. Would it fit a sales dashboard?  
# If NO to any → DISCARD  


# **Transcript:**
# {transcript}


# **Response Format:**
# Return a JSON object with:
# - "related_labels": comma-separated list of labels

# """.format(transcript=text)
    
#     try:
#             response = client.chat.completions.create(
#                 model="o3-mini",
#                 messages=[
#                     {"role": "system", "content": "You extract business-relevant labels from medical transcripts."},
#                     {"role": "user", "content": prompt}  
#                 ],
                
#                 response_format={"type": "json_object"}  
#             )
            
#             if not response.choices:
#                 raise ValueError("No choices in response")
            
#             content = response.choices[0].message.content
#             if not content:
#                 raise ValueError("Empty content in response")
            
#             # Parse JSON response
#             try:
#                 result = json.loads(content)
#             except json.JSONDecodeError:
#                 # Handle cases where response isn't proper JSON
#                 if "```json" in content:
#                     content = content.split("```json")[1].split("```")[0].strip()
#                     result = json.loads(content)
#                 else:
#                     raise ValueError("Invalid JSON response format")
            
#             # Process labels
#             labels = []
#             if "related_labels" in result:
#                 labels = [label.strip() for label in result["related_labels"].split(",") if label.strip()]
            
#             return labels, result.get("medicine_name", None)
            
#     except Exception as e:
#             print(f"Error extracting labels: {str(e)}")
#             return [], None

# def process_label_extraction(document_id: str):
#     """Process label extraction for a single document with rate limiting"""
#     try:
#         # Rate limiting to avoid hitting API limits
#         time.sleep(1)  # 1 second delay between requests
        
#         doc = collection.find_one({"_id": ObjectId(document_id)})
#         if not doc or not doc.get("text"):
#             return
        
#         labels, medicine_name = extract_labels_from_text(doc["text"])
        
#         # Prepare update data
#         update_data = {
#             "labels": labels,
#             "updated_at": datetime.now()
#         }
        
#         # Update medicine_name if provided and different
#         if medicine_name and medicine_name.lower() != "unknown":
#             if doc.get("medicine_name") != medicine_name:
#                 update_data["medicine_name"] = medicine_name
        
#         # Update document in database
#         collection.update_one(
#             {"_id": ObjectId(document_id)},
#             {"$set": update_data}
#         )
        
#     except Exception as e:
#         print(f"Error processing label extraction for {document_id}: {str(e)}")

# def process_all_documents_label_extraction():
#     """Process label extraction for all documents with parallel processing"""
#     try:
#         # Get all document IDs that have text content
#         documents = list(collection.find({"text": {"$exists": True, "$ne": ""}}, {"_id": 1}))
        
#         # Use ThreadPoolExecutor for parallel processing with rate limiting
#         with ThreadPoolExecutor(max_workers=5) as executor:
#             executor.map(process_label_extraction, [str(doc["_id"]) for doc in documents])
            
#     except Exception as e:
#         print(f"Error processing label extraction for all documents: {str(e)}")

# # API Endpoints
# @app.post("/documents/", response_model=Dict[str, str])
# async def create_document(
#     text: str = Form(...),
#     title: Optional[str] = Form(None),
#     medicine_name: Optional[str] = Form(None),
#     audio_file: Optional[UploadFile] = File(None),
#     background_tasks: BackgroundTasks = BackgroundTasks()
# ):
#     """Create a new document with optional audio attachment and medicine name"""
#     document = {
#         "text": text,
#         "title": title,
#         "medicine_name": medicine_name,
#         "created_at": datetime.now(),
#         "updated_at": datetime.now(),
#         "has_audio": False,
#         "labels": []
#     }
    
#     if audio_file:
#         audio_id = fs.put(await audio_file.read(), 
#                          filename=f"audio_{datetime.now().timestamp()}")
#         document["audio_id"] = audio_id
#         document["has_audio"] = True
    
#     result = collection.insert_one(document)
    
#     # Automatically trigger label generation for new documents
#     if text:  # Only if there's text content
#         background_tasks.add_task(process_label_extraction, str(result.inserted_id))
    
#     return {"id": str(result.inserted_id)}

# @app.get("/documents/{document_id}", response_model=Dict[str, Any])
# async def get_document(document_id: str):
#     """Get a specific document by ID"""
#     doc = collection.find_one({"_id": ObjectId(document_id)})
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found")
#     return convert_object_ids(doc)

# @app.get("/documents/", response_model=List[Dict[str, Any]])
# async def get_all_documents():
#     """Get all documents sorted by last updated"""
#     documents = list(collection.find().sort("updated_at", -1))
#     return [convert_object_ids(doc) for doc in documents]

# @app.get("/documents/{document_id}/audio")
# async def get_document_audio(document_id: str):
#     """Get audio file associated with a document"""
#     doc = collection.find_one({"_id": ObjectId(document_id)})
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found")
#     if not doc.get("has_audio", False):
#         raise HTTPException(status_code=404, detail="No audio attached")
    
#     audio_data = fs.get(doc["audio_id"]).read()
#     return {"audio": audio_data.hex()}

# @app.put("/documents/{document_id}")
# async def update_document(
#     document_id: str,
#     text: str = Form(...),
#     title: Optional[str] = Form(None),
#     medicine_name: Optional[str] = Form(None),  
#     audio_action: str = Form("keep"),
#     audio_file: Optional[UploadFile] = File(None),
#     background_tasks: BackgroundTasks = BackgroundTasks()
# ):
#     """Update an existing document with optional audio and medicine name"""
#     update_data = {
#         "text": text,
#         "updated_at": datetime.now()
#     }
    
#     if title is not None:
#         update_data["title"] = title
    
#     if medicine_name is not None:
#         update_data["medicine_name"] = medicine_name
    
#     doc = collection.find_one({"_id": ObjectId(document_id)})
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found")
    
#     if audio_action == "replace":
#         if not audio_file:
#             raise HTTPException(status_code=400, detail="Audio file required for replacement")
        
#         if doc.get("has_audio", False):
#             fs.delete(doc["audio_id"])
        
#         audio_id = fs.put(await audio_file.read(), 
#                          filename=f"audio_{datetime.now().timestamp()}")
#         update_data["audio_id"] = audio_id
#         update_data["has_audio"] = True
#     elif audio_action == "remove":
#         if doc.get("has_audio", False):
#             fs.delete(doc["audio_id"])
#         update_data["has_audio"] = False
#         update_data["audio_id"] = None
    
#     result = collection.update_one(
#         {"_id": ObjectId(document_id)},
#         {"$set": update_data}
#     )
    
#     # Automatically trigger label regeneration if text was updated
#     if "text" in update_data:
#         background_tasks.add_task(process_label_extraction, document_id)
    
#     return {"modified_count": result.modified_count}

# @app.delete("/documents/{document_id}")
# async def delete_document(document_id: str):
#     """Delete a document and its associated audio"""
#     doc = collection.find_one({"_id": ObjectId(document_id)})
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found")
    
#     if doc.get("has_audio", False):
#         fs.delete(doc["audio_id"])
    
#     result = collection.delete_one({"_id": ObjectId(document_id)})
#     return {"deleted_count": result.deleted_count}

# # Label Endpoints (kept for backward compatibility)
# @app.post("/documents/{document_id}/extract-labels")
# async def extract_labels(document_id: str, background_tasks: BackgroundTasks):
#     """Trigger label extraction for a document (manual override)"""
#     doc = collection.find_one({"_id": ObjectId(document_id)})
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found")
    
#     if not doc.get("text"):
#         raise HTTPException(status_code=400, detail="Document has no text content")
    
#     background_tasks.add_task(process_label_extraction, document_id)
#     return {"status": "Label extraction started in background"}

# @app.post("/documents/generate-labels-all")
# async def generate_labels_for_all(background_tasks: BackgroundTasks):
#     """Trigger label extraction for all documents (manual override)"""
#     background_tasks.add_task(process_all_documents_label_extraction)
#     return {"status": "Label extraction started for all documents in background"}

# @app.get("/documents/{document_id}/labels", response_model=List[str])
# async def get_document_labels(document_id: str):
#     """Get labels for a specific document"""
#     doc = collection.find_one({"_id": ObjectId(document_id)})
#     if not doc:
#         raise HTTPException(status_code=404, detail="Document not found")
#     return doc.get("labels", [])

# @app.get("/labels/", response_model=List[LabelResponse])
# async def get_all_labels():
#     """Get all unique labels with document counts"""
#     pipeline = [
#         {"$unwind": "$labels"},
#         {"$group": {
#             "_id": "$labels",
#             "document_count": {"$sum": 1},
#             "documents": {"$push": {
#                 "id": "$_id",
#                 "title": "$title",
#                 "text_preview": {"$substr": ["$text", 0, 100]},
#                 "updated_at": "$updated_at"
#             }}
#         }},
#         {"$sort": {"document_count": -1}}
#     ]
    
#     labels = list(collection.aggregate(pipeline))
    
#     return [{
#         "label": label["_id"],
#         "document_count": label["document_count"],
#         "documents": [{
#             "id": str(doc["id"]),
#             "title": doc.get("title", "Untitled"),
#             "text_preview": doc["text_preview"] + ("..." if len(doc["text_preview"]) == 100 else ""),
#             "updated_at": doc["updated_at"]
#         } for doc in label["documents"]]
#     } for label in labels]

# @app.get("/labels/{label}", response_model=LabelResponse)
# async def get_label_details(label: str):
#     """Get details for a specific label"""
#     pipeline = [
#         {"$match": {"labels": label}},
#         {"$project": {
#             "title": 1,
#             "text": {"$substr": ["$text", 0, 100]},
#             "updated_at": 1,
#             "has_audio": 1
#         }}
#     ]
    
#     documents = list(collection.aggregate(pipeline))
    
#     if not documents:
#         raise HTTPException(status_code=404, detail="Label not found")
    
#     return {
#         "label": label,
#         "document_count": len(documents),
#         "documents": [{
#             "id": str(doc["_id"]),
#             "title": doc.get("title", "Untitled"),
#             "text_preview": doc["text"] + ("..." if len(doc["text"]) == 100 else ""),
#             "updated_at": doc["updated_at"],
#             "has_audio": doc.get("has_audio", False)
#         } for doc in documents]
#     }

# if __name__ == "__main__":
#     uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)










import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv
import gridfs
from bson import ObjectId
from typing import Optional, List, Dict, Any
import uvicorn
import ssl
import certifi
from concurrent.futures import ThreadPoolExecutor
import time
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import PointStruct
import threading

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

client = get_mongo_client()
db = client["atrina"]
fs = gridfs.GridFS(db)
collection = db["atrina_test"]

# Initialize OpenAI
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Qdrant Configuration
qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

QDRANT_COLLECTION_NAME = "medical_transcripts"
EMBEDDING_MODEL = "text-embedding-ada-002"

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class DocumentCreate(BaseModel):
    text: str
    title: Optional[str] = None
    medicine_name: Optional[str] = None

class DocumentUpdate(BaseModel):
    text: str
    title: Optional[str] = None
    audio_action: Optional[str] = "keep"

class LabelResponse(BaseModel):
    label: str
    document_count: int
    documents: List[Dict[str, Any]]

class BulkLabelResponse(BaseModel):
    status: str
    total_documents: int
    processed_documents: int
    labels_generated: int

# Helper Functions
def convert_object_ids(document: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all ObjectId fields to strings in a document"""
    if document is None:
        return None
        
    document["_id"] = str(document["_id"])
    if "audio_id" in document:
        document["audio_id"] = str(document["audio_id"])
    return document

def initialize_qdrant_collection():
    """Create or verify the Qdrant collection exists with proper configuration"""
    try:
        collections = qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if QDRANT_COLLECTION_NAME not in collection_names:
            qdrant_client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=1536,  # ada-002 embedding size
                    distance=models.Distance.COSINE,
                ),
            )
            print(f"Created new Qdrant collection: {QDRANT_COLLECTION_NAME}")
        else:
            print(f"Using existing Qdrant collection: {QDRANT_COLLECTION_NAME}")
    except Exception as e:
        print(f"Error initializing Qdrant collection: {str(e)}")

def generate_embeddings(text: str) -> List[float]:
    """Generate embeddings using OpenAI's ada-002 model"""
    try:
        response = openai_client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embeddings: {str(e)}")
        return None

def ensure_data_consistency():
    """Periodically check and fix inconsistencies between MongoDB and Qdrant"""
    try:
        # Get all document IDs from MongoDB
        mongo_ids = set(str(doc["_id"]) for doc in collection.find({}, {"_id": 1}))
        
        # Get all point IDs from Qdrant
        qdrant_ids = set()
        for point in qdrant_client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            with_payload=False,
            with_vectors=False
        ):
            qdrant_ids.add(point.id)
        
        # Find missing documents in Qdrant
        missing_in_qdrant = mongo_ids - qdrant_ids
        if missing_in_qdrant:
            print(f"Found {len(missing_in_qdrant)} documents missing in Qdrant")
            for doc_id in missing_in_qdrant:
                doc = collection.find_one({"_id": ObjectId(doc_id)})
                if doc and doc.get("text"):
                    embedding = generate_embeddings(doc["text"])
                    if embedding:
                        point = PointStruct(
                            id=doc_id,
                            vector=embedding,
                            payload={
                                "text": doc.get("text", ""),
                                "title": doc.get("title"),
                                "medicine_name": doc.get("medicine_name"),
                                "labels": doc.get("labels", []),
                                "created_at": doc.get("created_at", datetime.now()).isoformat(),
                                "updated_at": doc.get("updated_at", datetime.now()).isoformat(),
                                "mongo_id": doc_id
                            }
                        )
                        qdrant_client.upsert(
                            collection_name=QDRANT_COLLECTION_NAME,
                            points=[point]
                        )
        
        # Find orphaned documents in Qdrant
        orphaned_in_qdrant = qdrant_ids - mongo_ids
        if orphaned_in_qdrant:
            print(f"Found {len(orphaned_in_qdrant)} orphaned documents in Qdrant")
            qdrant_client.delete(
                collection_name=QDRANT_COLLECTION_NAME,
                points_selector=models.PointIdsList(
                    points=list(orphaned_in_qdrant)
                )
            )
            
    except Exception as e:
        print(f"Data consistency check failed: {str(e)}")

def schedule_consistency_checks(interval_hours=24):
    """Background task for periodic data consistency checks"""
    while True:
        ensure_data_consistency()
        time.sleep(interval_hours * 3600)

# Start the consistency check thread
consistency_thread = threading.Thread(target=schedule_consistency_checks, daemon=True)
consistency_thread.start()

# Label extraction utility functions
def extract_labels_from_text(text: str) -> List[str]:
    """Use OpenAI-o3-mini to extract labels from text"""
    prompt = """
**Objective:**  
Analyze this medical transcript and extract EXCLUSIVELY business-relevant labels meeting ALL criteria:  
1. **Three-word limit** (strictly enforced)  
2. **Revenue/Competition/Operations focus** (no clinical terms)  
3. **Actionable insights only** (no opinions/feedback)  

**Allowed Categories:**  
- Pricing Strategy (discounts, margins, offers)  
- Market Competition (rival comparisons, switches)  
- Supply Chain (stock, delivery, launches)  
- Sales Commitments (prescriptions, quotas)
- MR suggestions (feedback, insights)
- Competition comparisons
- Market trends (growth, shifts)
- Feedback

**Transcript:**
{transcript}

**Response Format:**
Return a JSON object with:
- "related_labels": comma-separated list of labels
- "medicine_name": extracted medicine name if found
""".format(transcript=text)
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You extract business-relevant labels from medical transcripts."},
                {"role": "user", "content": prompt}  
            ],
            response_format={"type": "json_object"}  
        )
        
        if not response.choices:
            raise ValueError("No choices in response")
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty content in response")
        
        # Parse JSON response
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
                result = json.loads(content)
            else:
                raise ValueError("Invalid JSON response format")
        
        # Process labels
        labels = []
        if "related_labels" in result:
            labels = [label.strip() for label in result["related_labels"].split(",") if label.strip()]
        
        return labels, result.get("medicine_name", None)
            
    except Exception as e:
        print(f"Error extracting labels: {str(e)}")
        return [], None

def process_label_extraction(document_id: str):
    """Process label extraction for a single document with rate limiting"""
    try:
        time.sleep(1)  # Rate limiting
        
        doc = collection.find_one({"_id": ObjectId(document_id)})
        if not doc or not doc.get("text"):
            return
        
        labels, medicine_name = extract_labels_from_text(doc["text"])
        
        update_data = {
            "labels": labels,
            "updated_at": datetime.now()
        }
        
        if medicine_name and medicine_name.lower() != "unknown":
            if doc.get("medicine_name") != medicine_name:
                update_data["medicine_name"] = medicine_name
        
        collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_data}
        )
        
        # Update Qdrant
        embedding = generate_embeddings(doc["text"])
        if embedding:
            point = PointStruct(
                id=str(document_id),
                vector=embedding,
                payload={
                    "text": doc.get("text", ""),
                    "title": doc.get("title"),
                    "medicine_name": medicine_name or doc.get("medicine_name"),
                    "labels": labels,
                    "updated_at": datetime.now().isoformat(),
                    "mongo_id": str(document_id)
                }
            )
            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION_NAME,
                points=[point]
            )
        
    except Exception as e:
        print(f"Error processing label extraction for {document_id}: {str(e)}")

def process_all_documents_label_extraction():
    """Process label extraction for all documents with parallel processing"""
    try:
        documents = list(collection.find({"text": {"$exists": True, "$ne": ""}}, {"_id": 1}))
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(process_label_extraction, [str(doc["_id"]) for doc in documents])
            
    except Exception as e:
        print(f"Error processing label extraction for all documents: {str(e)}")

def migrate_all_documents_to_qdrant():
    """Migrate all documents from MongoDB to Qdrant"""
    try:
        initialize_qdrant_collection()
        
        documents = collection.find({})
        total_count = collection.count_documents({})
        processed = 0
        
        for doc in documents:
            try:
                embedding = generate_embeddings(doc.get("text", ""))
                if not embedding:
                    continue
                
                point = PointStruct(
                    id=str(doc["_id"]),
                    vector=embedding,
                    payload={
                        "text": doc.get("text", ""),
                        "title": doc.get("title"),
                        "medicine_name": doc.get("medicine_name"),
                        "labels": doc.get("labels", []),
                        "created_at": doc.get("created_at", datetime.now()).isoformat(),
                        "updated_at": doc.get("updated_at", datetime.now()).isoformat(),
                        "mongo_id": str(doc["_id"])
                    }
                )
                
                qdrant_client.upsert(
                    collection_name=QDRANT_COLLECTION_NAME,
                    points=[point]
                )
                
                processed += 1
                if processed % 100 == 0:
                    print(f"Migration progress: {processed}/{total_count}")
                    
            except Exception as e:
                print(f"Error migrating document {doc['_id']}: {str(e)}")
                continue
                
        print(f"Migration completed. Processed {processed}/{total_count} documents")
        
    except Exception as e:
        print(f"Migration failed: {str(e)}")

# API Endpoints
@app.post("/documents/", response_model=Dict[str, str])
async def create_document(
    text: str = Form(...),
    title: Optional[str] = Form(None),
    medicine_name: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new document with optional audio attachment and medicine name"""
    document = {
        "text": text,
        "title": title,
        "medicine_name": medicine_name,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "has_audio": False,
        "labels": []
    }
    
    if audio_file:
        audio_id = fs.put(await audio_file.read(), 
                         filename=f"audio_{datetime.now().timestamp()}")
        document["audio_id"] = audio_id
        document["has_audio"] = True
    
    result = collection.insert_one(document)
    
    # Add to Qdrant
    embedding = generate_embeddings(text)
    if embedding:
        point = PointStruct(
            id=str(result.inserted_id),
            vector=embedding,
            payload={
                "text": text,
                "title": title,
                "medicine_name": medicine_name,
                "labels": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "mongo_id": str(result.inserted_id)
            }
        )
        qdrant_client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=[point]
        )
    
    if text:
        background_tasks.add_task(process_label_extraction, str(result.inserted_id))
    
    return {"id": str(result.inserted_id)}

@app.get("/documents/{document_id}", response_model=Dict[str, Any])
async def get_document(document_id: str):
    """Get a specific document by ID"""
    doc = collection.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return convert_object_ids(doc)

@app.get("/documents/", response_model=List[Dict[str, Any]])
async def get_all_documents(enhanced: bool = False, limit: int = 100, offset: int = 0):
    """Get all documents sorted by last updated"""
    documents = list(collection.find().sort("updated_at", -1).skip(offset).limit(limit))
    
    if not enhanced:
        return [convert_object_ids(doc) for doc in documents]
    
    enhanced_docs = []
    for doc in documents:
        enhanced_doc = convert_object_ids(doc)
        
        if doc.get("text"):
            embedding = generate_embeddings(doc["text"])
            if embedding:
                similar = qdrant_client.search(
                    collection_name=QDRANT_COLLECTION_NAME,
                    query_vector=embedding,
                    query_filter=models.Filter(
                        must_not=[models.FieldCondition(
                            key="mongo_id",
                            match=models.MatchValue(value=str(doc["_id"]))
                        )]
                    ),
                    limit=3,
                    with_payload=True
                )
                enhanced_doc["similar_transcripts"] = [
                    {
                        "id": hit.id,
                        "score": hit.score,
                        "title": hit.payload.get("title"),
                        "medicine_name": hit.payload.get("medicine_name")
                    }
                    for hit in similar
                ]
        
        enhanced_docs.append(enhanced_doc)
    
    return enhanced_docs

@app.get("/transcripts/all", response_model=List[Dict[str, Any]])
async def get_all_transcripts(enhanced: bool = False, limit: int = 100, offset: int = 0):
    """Alias for get_all_documents for backward compatibility"""
    return await get_all_documents(enhanced, limit, offset)

@app.get("/documents/{document_id}/audio")
async def get_document_audio(document_id: str):
    """Get audio file associated with a document"""
    doc = collection.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.get("has_audio", False):
        raise HTTPException(status_code=404, detail="No audio attached")
    
    audio_data = fs.get(doc["audio_id"]).read()
    return {"audio": audio_data.hex()}

@app.put("/documents/{document_id}")
async def update_document(
    document_id: str,
    text: str = Form(...),
    title: Optional[str] = Form(None),
    medicine_name: Optional[str] = Form(None),  
    audio_action: str = Form("keep"),
    audio_file: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Update an existing document with optional audio and medicine name"""
    update_data = {
        "text": text,
        "updated_at": datetime.now()
    }
    
    if title is not None:
        update_data["title"] = title
    
    if medicine_name is not None:
        update_data["medicine_name"] = medicine_name
    
    doc = collection.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if audio_action == "replace":
        if not audio_file:
            raise HTTPException(status_code=400, detail="Audio file required for replacement")
        
        if doc.get("has_audio", False):
            fs.delete(doc["audio_id"])
        
        audio_id = fs.put(await audio_file.read(), 
                         filename=f"audio_{datetime.now().timestamp()}")
        update_data["audio_id"] = audio_id
        update_data["has_audio"] = True
    elif audio_action == "remove":
        if doc.get("has_audio", False):
            fs.delete(doc["audio_id"])
        update_data["has_audio"] = False
        update_data["audio_id"] = None
    
    result = collection.update_one(
        {"_id": ObjectId(document_id)},
        {"$set": update_data}
    )
    
    # Update Qdrant if text changed
    if "text" in update_data:
        embedding = generate_embeddings(text)
        if embedding:
            point = PointStruct(
                id=document_id,
                vector=embedding,
                payload={
                    "text": text,
                    "title": title or doc.get("title"),
                    "medicine_name": medicine_name or doc.get("medicine_name"),
                    "updated_at": datetime.now().isoformat(),
                    "mongo_id": document_id
                }
            )
            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION_NAME,
                points=[point]
            )
        background_tasks.add_task(process_label_extraction, document_id)
    
    return {"modified_count": result.modified_count}

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its associated audio"""
    doc = collection.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.get("has_audio", False):
        fs.delete(doc["audio_id"])
    
    # Delete from Qdrant
    qdrant_client.delete(
        collection_name=QDRANT_COLLECTION_NAME,
        points_selector=models.PointIdsList(points=[document_id])
    )
    
    result = collection.delete_one({"_id": ObjectId(document_id)})
    return {"deleted_count": result.deleted_count}

# Label Endpoints
@app.post("/documents/{document_id}/extract-labels")
async def extract_labels(document_id: str, background_tasks: BackgroundTasks):
    """Trigger label extraction for a document (manual override)"""
    doc = collection.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.get("text"):
        raise HTTPException(status_code=400, detail="Document has no text content")
    
    background_tasks.add_task(process_label_extraction, document_id)
    return {"status": "Label extraction started in background"}

@app.post("/documents/generate-labels-all")
async def generate_labels_for_all(background_tasks: BackgroundTasks):
    """Trigger label extraction for all documents (manual override)"""
    background_tasks.add_task(process_all_documents_label_extraction)
    return {"status": "Label extraction started for all documents in background"}

@app.get("/documents/{document_id}/labels", response_model=List[str])
async def get_document_labels(document_id: str):
    """Get labels for a specific document"""
    doc = collection.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.get("labels", [])

@app.get("/labels/", response_model=List[LabelResponse])
async def get_all_labels(enhanced: bool = False):
    """Get all unique labels with document counts"""
    pipeline = [
        {"$unwind": "$labels"},
        {"$group": {
            "_id": "$labels",
            "document_count": {"$sum": 1},
            "documents": {"$push": {
                "id": "$_id",
                "title": "$title",
                "text_preview": {"$substr": ["$text", 0, 100]},
                "updated_at": "$updated_at"
            }}
        }},
        {"$sort": {"document_count": -1}}
    ]
    
    labels = list(collection.aggregate(pipeline))
    
    if not enhanced:
        return [{
            "label": label["_id"],
            "document_count": label["document_count"],
            "documents": [{
                "id": str(doc["id"]),
                "title": doc.get("title", "Untitled"),
                "text_preview": doc["text_preview"] + ("..." if len(doc["text_preview"]) == 100 else ""),
                "updated_at": doc["updated_at"]
            } for doc in label["documents"]]
        } for label in labels]
    
    # Enhanced version with vector clusters
    enhanced_labels = []
    for label in labels:
        # Get cluster information from Qdrant
        cluster_info = []
        for doc in label["documents"][:3]:  # Sample 3 documents per label
            doc_data = collection.find_one({"_id": doc["id"]})
            if doc_data and doc_data.get("text"):
                embedding = generate_embeddings(doc_data["text"])
                if embedding:
                    similar = qdrant_client.search(
                        collection_name=QDRANT_COLLECTION_NAME,
                        query_vector=embedding,
                        limit=5,
                        with_payload=True
                    )
                    cluster_info.append({
                        "representative_text": doc_data["text"][:100] + "...",
                        "similar_documents": [
                            {
                                "id": hit.id,
                                "score": hit.score,
                                "title": hit.payload.get("title"),
                                "medicine_name": hit.payload.get("medicine_name")
                            }
                            for hit in similar
                        ]
                    })
        
        enhanced_labels.append({
            "label": label["_id"],
            "document_count": label["document_count"],
            "documents": [{
                "id": str(doc["id"]),
                "title": doc.get("title", "Untitled"),
                "text_preview": doc["text_preview"] + ("..." if len(doc["text_preview"]) == 100 else ""),
                "updated_at": doc["updated_at"]
            } for doc in label["documents"]],
            "clusters": cluster_info
        })
    
    return enhanced_labels

@app.get("/labels/{label}", response_model=LabelResponse)
async def get_label_details(label: str, enhanced: bool = False):
    """Get details for a specific label"""
    pipeline = [
        {"$match": {"labels": label}},
        {"$project": {
            "title": 1,
            "text": {"$substr": ["$text", 0, 100]},
            "updated_at": 1,
            "has_audio": 1
        }}
    ]
    
    documents = list(collection.aggregate(pipeline))
    
    if not documents:
        raise HTTPException(status_code=404, detail="Label not found")
    
    if not enhanced:
        return {
            "label": label,
            "document_count": len(documents),
            "documents": [{
                "id": str(doc["_id"]),
                "title": doc.get("title", "Untitled"),
                "text_preview": doc["text"] + ("..." if len(doc["text"]) == 100 else ""),
                "updated_at": doc["updated_at"],
                "has_audio": doc.get("has_audio", False)
            } for doc in documents]
        }
    
    # Enhanced version with vector clusters
    clusters = []
    for doc in documents[:3]:  # Sample 3 documents
        doc_data = collection.find_one({"_id": doc["_id"]})
        if doc_data and doc_data.get("text"):
            embedding = generate_embeddings(doc_data["text"])
            if embedding:
                similar = qdrant_client.search(
                    collection_name=QDRANT_COLLECTION_NAME,
                    query_vector=embedding,
                    limit=5,
                    with_payload=True
                )
                clusters.append({
                    "representative_text": doc_data["text"][:100] + "...",
                    "similar_documents": [
                        {
                            "id": hit.id,
                            "score": hit.score,
                            "title": hit.payload.get("title"),
                            "medicine_name": hit.payload.get("medicine_name")
                        }
                        for hit in similar
                    ]
                })
    
    return {
        "label": label,
        "document_count": len(documents),
        "documents": [{
            "id": str(doc["_id"]),
            "title": doc.get("title", "Untitled"),
            "text_preview": doc["text"] + ("..." if len(doc["text"]) == 100 else ""),
            "updated_at": doc["updated_at"],
            "has_audio": doc.get("has_audio", False)
        } for doc in documents],
        "clusters": clusters
    }

@app.get("/labels/enhanced", response_model=List[Dict[str, Any]])
async def get_enhanced_labels():
    """Get all labels with vector-based clustering information"""
    try:
        pipeline = [
            {"$unwind": "$labels"},
            {"$group": {"_id": "$labels", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        labels = list(collection.aggregate(pipeline))
        
        enhanced_labels = []
        for label in labels:
            docs = list(collection.find(
                {"labels": label["_id"]},
                {"text": 1, "title": 1, "medicine_name": 1},
                limit=3
            ))
            
            cluster_info = []
            for doc in docs:
                if "text" in doc:
                    embedding = generate_embeddings(doc["text"])
                    if embedding:
                        similar = qdrant_client.search(
                            collection_name=QDRANT_COLLECTION_NAME,
                            query_vector=embedding,
                            limit=5,
                            with_payload=True
                        )
                        cluster_info.append({
                            "representative_text": doc["text"][:100] + "...",
                            "similar_documents": [
                                {
                                    "id": hit.id,
                                    "score": hit.score,
                                    "title": hit.payload.get("title"),
                                    "medicine_name": hit.payload.get("medicine_name")
                                }
                                for hit in similar
                            ]
                        })
            
            enhanced_labels.append({
                "label": label["_id"],
                "document_count": label["count"],
                "clusters": cluster_info
            })
        
        return enhanced_labels
        
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# Search Endpoints
@app.get("/search/semantic")
async def semantic_search(
    query: str,
    label_filter: Optional[str] = None,
    medicine_filter: Optional[str] = None,
    limit: int = 10
):
    """Semantic search using vector embeddings"""
    try:
        query_embedding = generate_embeddings(query)
        if not query_embedding:
            raise HTTPException(400, detail="Failed to generate query embedding")
        
        filter_conditions = []
        if label_filter:
            filter_conditions.append(
                models.FieldCondition(
                    key="labels",
                    match=models.MatchValue(value=label_filter))
            )
        if medicine_filter:
            filter_conditions.append(
                models.FieldCondition(
                    key="medicine_name",
                    match=models.MatchValue(value=medicine_filter)
                )
            )
        
        search_result = qdrant_client.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=models.Filter(
                must=filter_conditions if filter_conditions else None
            ),
            limit=limit,
            with_payload=True
        )
        
        results = []
        for hit in search_result:
            doc = collection.find_one({"_id": ObjectId(hit.id)})
            if doc:
                results.append({
                    "score": hit.score,
                    "document": convert_object_ids(doc),
                    "payload": hit.payload
                })
        
        return results
        
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/search/hybrid")
async def hybrid_search(
    query: str,
    label_filter: Optional[str] = None,
    medicine_filter: Optional[str] = None,
    limit: int = 10
):
    """Hybrid search combining vector and keyword search"""
    try:
        # Vector search
        query_embedding = generate_embeddings(query)
        vector_results = []
        if query_embedding:
            filter_conditions = []
            if label_filter:
                filter_conditions.append(
                    models.FieldCondition(
                        key="labels",
                        match=models.MatchValue(value=label_filter)
                    )
                )
            if medicine_filter:
                filter_conditions.append(
                    models.FieldCondition(
                        key="medicine_name",
                        match=models.MatchValue(value=medicine_filter)
                    )
                )
            
            vector_results = qdrant_client.search(
                collection_name=QDRANT_COLLECTION_NAME,
                query_vector=query_embedding,
                query_filter=models.Filter(
                    must=filter_conditions if filter_conditions else None
                ),
                limit=limit,
                with_payload=True
            )
        
        # Keyword search in MongoDB
        keyword_results = list(collection.find(
            {
                "$text": {"$search": query},
                **({"labels": label_filter} if label_filter else {}),
                **({"medicine_name": medicine_filter} if medicine_filter else {})
            },
            {"score": {"$meta": "textScore"}},
            limit=limit
        ).sort([("score", {"$meta": "textScore"})]))
        
        # Combine and deduplicate results
        combined = []
        seen_ids = set()
        
        for hit in vector_results:
            doc_id = hit.payload.get("mongo_id")
            if doc_id and doc_id not in seen_ids:
                doc = collection.find_one({"_id": ObjectId(doc_id)})
                if doc:
                    combined.append({
                        "type": "vector",
                        "score": hit.score,
                        "document": convert_object_ids(doc)
                    })
                    seen_ids.add(doc_id)
        
        for doc in keyword_results:
            doc_id = str(doc["_id"])
            if doc_id not in seen_ids:
                combined.append({
                    "type": "keyword",
                    "score": doc.get("score", 0),
                    "document": convert_object_ids(doc)
                })
                seen_ids.add(doc_id)
        
        combined.sort(key=lambda x: x["score"], reverse=True)
        
        return combined[:limit]
        
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# Migration Endpoints
@app.post("/migrate/to-qdrant")
async def migrate_to_qdrant(background_tasks: BackgroundTasks):
    """Trigger background migration of all documents to Qdrant"""
    background_tasks.add_task(migrate_all_documents_to_qdrant)
    return {"status": "Migration started in background"}

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

if __name__ == "__main__":
    initialize_qdrant_collection()
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
