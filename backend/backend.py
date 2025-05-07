
import json
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
# import openai
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
from qdrant import qdrant_service
from concurrent.futures import ThreadPoolExecutor
import time
from openai import OpenAI
from insights import init_insights_service
from chat1 import router as chat_router
# from chat1 import router as chat_router

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

client = get_mongo_client()
db = client["atrina"]
fs = gridfs.GridFS(db)
collection = db["atrina_test"]

insights_service = init_insights_service(db)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
# client = openai.OpenAI(
#     # This is the default and can be omitted
#     api_key=os.getenv("OPENAI_API_KEY"))

# model = genai.GenerativeModel('gemini-2.0-flash')


app = FastAPI()

# app.include_router(chat_router)
# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)
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

class SearchQuery(BaseModel):
    text: str
    limit: Optional[int] = 5

class DocumentResponse(BaseModel):
    id: str
    text: str
    title: Optional[str] = None
    medicine_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    has_audio: bool
    labels: List[str]
    label_summary: str
    label_reason: Dict[str, str] = {}  # Added field to store reasons for each label
    audio_id: Optional[str] = None

def convert_object_ids(document: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all ObjectId fields to strings in a document"""
    if document is None:
        return None
        
    document["_id"] = str(document["_id"])
    if "audio_id" in document:
        document["audio_id"] = str(document["audio_id"])
    return document


def extract_labels_from_text(text: str) -> tuple:
    """Use OpenAI-o3-mini to extract labels from text with individual reasons for each label"""
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

**Refer the Detailed Section Below for more information**
##1.Deeply Understand the Transcript
-Carefully read the transcript and identify key phrases that indicate business actions, strategies, or insights. Focus on the context of the text to ensure accurate label generation
and make decision that might not seem import with respect the business action or business insights also double check the transcript and make sure that the label is not related to any clinical or patient-related information or any medicine-related information or Dosage regarding information 
-Search for the Labels that might most likely be used with respect to the product which will be useful with respect to the business heads which give them better knowledge about the product and the business action or business insights or business strategy which can be used to generate the labels based on that and make sure that the label is not related to any clinical or patient-related information or any medicine-related information or Dosage regarding information
-Also make a detailed thinking for the keywords selection which keyword would be appropriate regards to Insights 
-If the keywords already exist then please do not generate the same keywords or word with same meaning again please 
-make sure that the keywords are not repeated or same meaning or synonyms of the same word


### **Label Generation Instructions**:

1. **Ensure Uniqueness**:
   - **Check if the label already exists** in the stored list of labels. If a label is **already present** with the same or similar meaning, **do not generate the new label**.
   - **Similarity Check**: If a label has a similar **meaning**, use the existing label and avoid creating new ones. For example, if both "Product Prescription Confirmation" and "Product Prescription" exist, they should not both be created as separate labels.

2. **Label Extraction Criteria**:
   - Extract only **business-relevant** labels. These should focus on **market dynamics**, **product performance**, **sales strategies**, **pricing**, and **competitive positioning**.


### **Label Extraction Criteria**:

1. **Doctor Feedback**:
   - Extract any feedback from the **doctor** about the **product's effectiveness** or **acceptability**. This could be positive feedback on the product's benefits or **constructive feedback** on improvements.
   - **Example Label**: "Doctor Feedback" or "Product Feedback."

2. **MR Suggestion**:
   - Look for instances where the **Medical Representative (MR)** suggests a product to the doctor, including **recommendations**, **usage**, or strategies to enhance adoption.
   - **Example Label**: "MR Suggestion" or "Sales Suggestion."

3. **Market Competition**:
   - Identify discussions about **competitor products** in the market, including **comparisons**, **pricing**, or **market trends**.
   - **Example Label**: "Market Competition" or "Competitive Analysis."

4. **Product Availability**:
   - Extract mentions of **product availability** in terms of **stock levels**, **supply chain**, or **timeliness** of product delivery.
   - **Example Label**: "Product Availability" or "Supply Assurance."

5. **Promotional Request**:
   - Look for requests for **promotional materials**, such as **brochures**, **sample kits**, or **marketing tools** used to support product promotion.
   - **Example Label**: "Promotional Request" or "Marketing Request."

6. **Product Response**:
   - Extract mentions of how **patients** or **doctors** have responded to the product, including **efficacy**, **side effects**, or overall feedback.
   - **Example Label**: "Product Response" or "Patient Response."

7. **Cost Comparison**:
   - Identify comparisons of the **product cost** with competitor products, especially regarding **pricing** or **cost-to-therapy**.
   - **Example Label**: "Cost Comparison" or "Price Comparison."

8. **Pricing Advantage**:
   - Look for references to **pricing advantages** such as **discounts**, **affordable pricing**, or **value for money**.
   - **Example Label**: "Pricing Advantage" or "Price Advantage."

9. **Prescription Duration**:
   - Extract mentions of the **prescription duration** for the product, whether it's prescribed for **short-term** or **long-term**.
   - **Example Label**: "Prescription Duration" or "Treatment Duration."

10. **Sales Strategy**:
    - Identify discussions about **sales strategies**, **goals**, or **approaches** to push the product in the market.
    - **Example Label**: "Sales Strategy" or "Market Strategy."

11. **Product Comparison**:
    - Look for **comparisons** between the product and competing brands, particularly regarding **efficacy**, **pricing**, or **unique features**.
    - **Example Label**: "Product Comparison" or "Competitive Comparison."

12. **Market Launch**:
    - Extract mentions of the **product launch**, including **timing**, **target markets**, or **expansion** plans.
    - **Example Label**: "Market Launch" or "Launch Strategy."

13. **Prescription Confirmation**:
    - Identify instances where the doctor or MR confirms they will **prescribe** the product.
    - **Example Label**: "Prescription Confirmation" or "Product Prescription."

14. **Absorption Claim**:
    - Look for **claims** regarding the **absorption rate**, **bioavailability**, or **effectiveness** of the product.
    - **Example Label**: "Absorption Claim" or "Efficacy Claim."

15. **Counter-Argument**:
    - Extract statements where the MR or doctor prepares to **counter** claims made by competitors, using data or facts to defend the product's position.
    - **Example Label**: "Counter Argument" or "Competitive Counter."

16. **Doctor's Suggestion**:
    - Extract instances where the **doctor** suggests a specific product based on **patient needs** or **clinical outcomes**.
    - **Example Label**: "Doctor's Suggestion" or "Product Recommendation."

17. **Labeling Suggestion**:
    - Identify any suggestions made regarding changes to the **product label** for better clarity or **regulatory compliance**.
    - **Example Label**: "Labeling Suggestion" or "Label Changes."

---

### **Final Output**:
For each transcript, generate **business-focused labels** related to **market dynamics**, **sales strategies**, **competitive positioning**, and **product performance** in the market. Each label should only contain **two words**.

### **Example Output**:
  

**Examples:**  
Input: "Will beat CompetitorX's 20% discount if ordered before quarter-end"  
→ `Discount Beat Guarantee,Quarter-End Push,Competitor Price Match`  

Input: "Guaranteed pharmacy availability in Tier-1 cities by Q3"  
→ `Tier-1 Rollout,Q3 Stock Promise,City-Wide Availability`  

**Rejection Rules:**  
1. Reject if >3 words  
2. Reject if clinical/patient-related  
3. Reject if vague ("Good Feedback")  
4. Reject duplicates/synonyms  
5. Anything which is not related to business action or Business strategy or Business insights reject it 
6. Reject the Order like ("Order 1000 units") these should be rejected as well
7. Reason how can we use the labels in business insights or business action and generate labels based on that

**Validation Protocol:**  
1. Does this label trigger business action?  
2. Is it tied to revenue/competition/logistics?  
3. Would it fit a sales dashboard?  
If NO to any → DISCARD  


**Transcript:**
{transcript}


**Response Format:**
Return a JSON object with:
- "related_labels": comma-separated list of labels
- "label_reasons": a dictionary/object where each key is a label and the value is a detailed reason for that label
- "label_summary": a detailed summary(1 sentences) of the key business insights from the Labels

""".format(transcript=text)
    
    try:
        response = client.chat.completions.create(
            model="o3-mini",
            reasoning_effort="medium",
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
            # Handle cases where response isn't proper JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
                result = json.loads(content)
            else:
                raise ValueError("Invalid JSON response format")
        
        # Process labels
        labels = []
        if "related_labels" in result:
            labels = [label.strip() for label in result["related_labels"].split(",") if label.strip()]
        
        # Get the label reasons dictionary
        label_reasons = {}
        if "label_reasons" in result:
            label_reasons = result["label_reasons"]
        
        # Get the label summary
        summary = result.get("label_summary", "No summary generated")
        
        # Get medicine name if available
        medicine_name = result.get("medicine_name", None)
        
        return labels, medicine_name, summary, label_reasons
        
    except Exception as e:
        print(f"Error extracting labels: {str(e)}")
        return [], None, "Error generating summary", {}

def process_label_extraction(document_id: str):
    """Process label extraction and update Qdrant if ready"""
    try:
        # Rate limiting
        time.sleep(1)
        
        doc = collection.find_one({"_id": ObjectId(document_id)})
        if not doc or not doc.get("text"):
            return
        
        # Call extract_labels_from_text and unpack all four return values
        labels, medicine_name, summary, label_reasons = extract_labels_from_text(doc["text"])
        
        # Prepare update data
        update_data = {
            "labels": labels,
            "label_summary": summary,
            "label_reason": label_reasons,  # Store the reasons dictionary
            "updated_at": datetime.now()
        }
        
        # Update medicine_name if provided and different
        if medicine_name and medicine_name.lower() != "unknown":
            if doc.get("medicine_name") != medicine_name:
                update_data["medicine_name"] = medicine_name
        
        # Update document in database
        collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_data}
        )
        
        # Get the updated document
        updated_doc = collection.find_one({"_id": ObjectId(document_id)})
        
        # Only add to Qdrant if we have both labels and medicine name
        if (updated_doc.get("labels") and len(updated_doc["labels"]) > 0 and 
            updated_doc.get("medicine_name") and updated_doc["medicine_name"].strip() != ""):
            qdrant_service.insert_document(updated_doc)
            
    except Exception as e:
        print(f"Error processing label extraction for {document_id}: {str(e)}")


def process_all_documents_label_extraction():
    """Process label extraction for all documents with parallel processing"""
    try:
        # Get all document IDs that have text content
        documents = list(collection.find({"text": {"$exists": True, "$ne": ""}}, {"_id": 1}))
        
        # Use ThreadPoolExecutor for parallel processing with rate limiting
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(process_label_extraction, [str(doc["_id"]) for doc in documents])
            
    except Exception as e:
        print(f"Error processing label extraction for all documents: {str(e)}")

def migrate_existing_documents():
    """
    Migration script to update existing documents to include label_reason field
    and regenerate labels with reasons
    """
    try:
        # Find all documents that don't have label_reason field
        docs_to_update = list(collection.find({"label_reason": {"$exists": False}}))
        print(f"Found {len(docs_to_update)} documents that need migration")
        
        for doc in docs_to_update:
            # First, add the empty label_reason field
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"label_reason": {}}}
            )
            
            # Then trigger the label extraction process which will update the label_reason
            process_label_extraction(str(doc["_id"]))
            print(f"Updated document {doc['_id']}")
            
            # Add a small delay to avoid overwhelming the API
            time.sleep(2)
            
        print("Migration completed successfully")
    except Exception as e:
        print(f"Error during migration: {str(e)}")

# Add an endpoint to trigger the migration
@app.post("/admin/migrate-label-reasons")
async def migrate_label_reasons(background_tasks: BackgroundTasks):
    """Trigger migration of documents to add label_reason field"""
    background_tasks.add_task(migrate_existing_documents)
    return {"status": "Migration started in background"}



# Update the document creation endpoint to initialize the label_reason field
@app.post("/documents/", response_model=Dict[str, str])
async def create_document(
    text: str = Form(...),
    title: Optional[str] = Form(None),
    medicine_name: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new document - won't add to Qdrant until labels are generated"""
    document = {
        "text": text,
        "title": title,
        "medicine_name": medicine_name if medicine_name else "",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "has_audio": False,
        "labels": [],
        "label_reason": {},  # Initialize as empty dictionary
        "label_summary": ""
    }
    
    if audio_file:
        audio_id = fs.put(await audio_file.read(), 
                         filename=f"audio_{datetime.now().timestamp()}")
        document["audio_id"] = audio_id
        document["has_audio"] = True
    
    result = collection.insert_one(document)
    
    # Trigger label generation (which will handle Qdrant insertion when ready)
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
async def get_all_documents():
    """Get all documents sorted by last updated"""
    documents = list(collection.find().sort("updated_at", -1))
    return [convert_object_ids(doc) for doc in documents]

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
    
    # Update in Qdrant
    if result.modified_count > 0:
        updated_doc = collection.find_one({"_id": ObjectId(document_id)})
        background_tasks.add_task(qdrant_service.update_document, updated_doc)
    
    # Automatically trigger label regeneration if text was updated
    if "text" in update_data:
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
    qdrant_service.delete_document(str(doc["_id"]))
    
    result = collection.delete_one({"_id": ObjectId(document_id)})
    return {"deleted_count": result.deleted_count}

# Add these new endpoints for Qdrant operations
@app.post("/search/similar")
async def search_similar_documents(query: SearchQuery):
    """Search for similar documents using vector similarity"""
    results = qdrant_service.search_similar(query.text, query.limit)
    return results

@app.post("/documents/sync-to-qdrant")
async def sync_to_qdrant(background_tasks: BackgroundTasks):
    """Trigger a full sync of MongoDB documents to Qdrant"""
    background_tasks.add_task(sync_all_documents_to_qdrant)
    return {"status": "Sync to Qdrant started in background"}

def sync_all_documents_to_qdrant():
    """Synchronize all documents from MongoDB to Qdrant"""
    documents = list(collection.find())
    print(f"Syncing {len(documents)} documents to Qdrant")
    
    success_count = 0
    for doc in documents:
        if qdrant_service.insert_document(doc):
            success_count += 1
    
    print(f"Successfully synced {success_count}/{len(documents)} documents to Qdrant")

# Label Endpoints (kept for backward compatibility)
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
async def get_all_labels():
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

@app.get("/labels/{label}")
async def get_label_details(label: str):
    """Get details for a specific label with reasons"""
    pipeline = [
        {"$match": {"labels": label}},
        {"$project": {
            "title": 1,
            "text": {"$substr": ["$text", 0, 100]},
            "updated_at": 1,
            "has_audio": 1,
            "label_reason": 1  # Include label reasons
        }}
    ]
    
    documents = list(collection.aggregate(pipeline))
    
    if not documents:
        raise HTTPException(status_code=404, detail="Label not found")
    
    # Collect all reasons for this label across documents
    all_reasons = []
    for doc in documents:
        if "label_reason" in doc and label in doc["label_reason"]:
            reason = doc["label_reason"][label]
            if reason not in all_reasons:
                all_reasons.append(reason)
    
    return {
        "label": label,
        "document_count": len(documents),
        "reasons": all_reasons,  # Include all unique reasons for this label
        "documents": [{
            "id": str(doc["_id"]),
            "title": doc.get("title", "Untitled"),
            "text_preview": doc["text"] + ("..." if len(doc["text"]) == 100 else ""),
            "updated_at": doc["updated_at"],
            "has_audio": doc.get("has_audio", False),
            "label_reason": doc.get("label_reason", {}).get(label, "")  # Include reason for this document
        } for doc in documents]
    }


@app.get("/documents/{document_id}/label-reasons", response_model=Dict[str, str])
async def get_document_label_reasons(document_id: str):
    """Get label reasons for a specific document"""
    doc = collection.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.get("label_reason", {})

#delete this if doesn't work 
# Add these new endpoints to backend.py

@app.get("/medicines/", response_model=List[str])
async def get_all_medicines():
    """Get a list of all unique medicine names"""
    result = collection.distinct("medicine_name")
    # Filter out empty or None values
    medicines = [med for med in result if med and med.strip()]
    return sorted(medicines)

# @app.get("/medicines/{medicine_name}/labels", response_model=List[Dict[str, Any]])
# async def get_medicine_labels(medicine_name: str):
#     """Get all labels associated with a specific medicine"""
#     pipeline = [
#         {"$match": {"medicine_name": medicine_name}},
#         {"$unwind": "$labels"},
#         {"$group": {
#             "_id": "$labels",
#             "count": {"$sum": 1},
#             "reasons": {"$addToSet": {"$ifNull": [{"$getField": {"field": {"$concat": ["$label_reason.", "$labels"]}}}, ""]}},
#         }},
#         {"$sort": {"count": -1}}
#     ]
    
#     labels = list(collection.aggregate(pipeline))
    
#     return [{
#         "label": label["_id"],
#         "count": label["count"],
#         "reasons": [reason for reason in label["reasons"] if reason]  # Filter out empty reasons
#     } for label in labels]

@app.get("/medicines/{medicine_name}/labels", response_model=List[Dict[str, Any]])
async def get_medicine_labels(medicine_name: str):
    """Get all labels associated with a specific medicine"""
    pipeline = [
        {"$match": {"medicine_name": medicine_name}},
        {"$unwind": "$labels"},
        {"$group": {
            "_id": "$labels",
            "count": {"$sum": 1},
            "reasons": {"$addToSet": "$label_reason"}  # Simplified this part
        }},
        {"$sort": {"count": -1}}
    ]
    
    labels = list(collection.aggregate(pipeline))
    
    return [{
        "label": label["_id"],
        "count": label["count"],
        "reasons": [reason.get(label["_id"], "") for reason in label["reasons"] if reason and label["_id"] in reason]
    } for label in labels]


# Add these endpoints to your backend.py

@app.get("/medicines/{medicine_name}/insights")
async def get_medicine_insights(medicine_name: str):
    """Get comprehensive label insights for a medicine"""
    try:
        return insights_service.get_medicine_labels_with_reasons(medicine_name)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get medicine insights: {str(e)}"
        )

@app.post("/search/medicine-label")
async def search_by_medicine_label(
    medicine_name: str = Form(...),
    label: Optional[str] = Form(None),
    limit: Optional[int] = Form(20)
):
    """Search for documents with specific medicine name and optionally a specific label"""
    results = qdrant_service.search_by_medicine_and_label(medicine_name, label, limit)
    return results

# Insight Endpoints
# In backend.py, modify the generate_insights endpoint
# Insight Endpoints
@app.post("/insights/generate")
async def generate_insights(
    medicine_name: str = Form(...),
    label: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Trigger insight generation for a medicine"""
    try:
        # Validate medicine exists
        medicine_count = collection.count_documents({
            "medicine_name": medicine_name,
            "medicine_name": {"$exists": True, "$ne": ""}
        })
        
        if medicine_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No documents found for medicine: {medicine_name}"
            )
        
        # If specific label requested, validate it exists
        if label:
            label_count = collection.count_documents({
                "medicine_name": medicine_name,
                "labels": label
            })
            
            if label_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"No documents found for {medicine_name} with label: {label}"
                )
        
        # Start background task
        background_tasks.add_task(insights_service.generate_insights, medicine_name, label)
        
        return {
            "status": "started",
            "message": "Insight generation started in background",
            "medicine_name": medicine_name,
            "label": label
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start insight generation: {str(e)}"
        )

@app.get("/insights/history")
async def get_insights_history(
    medicine_name: Optional[str] = None,
    label: Optional[str] = None,
    limit: int = 10
):
    """Get historical insights with better formatting"""
    try:
        insights = insights_service.get_insights_history(medicine_name, label, limit)
        
        # Convert ObjectId to string and format the response
        formatted_insights = []
        for insight in insights:
            formatted = {
                "id": str(insight["_id"]),
                "medicine_name": insight["medicine_name"],
                "label": insight.get("label"),
                "generated_at": insight["generated_at"],
                "summary": insight["insights"].split("\n")[0] if insight["insights"] else "",
                "document_count": insight.get("document_count", 0)
            }
            formatted_insights.append(formatted)
        
        return formatted_insights
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve insights: {str(e)}"
        )

@app.get("/insights/{insight_id}")
async def get_insight(insight_id: str):
    """Get full insight details by ID"""
    try:
        insight = insights_service.get_insight_by_id(insight_id)
        
        # Format the response
        return {
            "id": str(insight["_id"]),
            "medicine_name": insight["medicine_name"],
            "label": insight.get("label"),
            "generated_at": insight["generated_at"],
            "insights": insight["insights"],
            "context": insight.get("context", {}),
            "document_count": insight.get("document_count", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve insight: {str(e)}"
        )


# Add an endpoint to reindex all documents with the new format
@app.post("/admin/reindex-qdrant")
async def reindex_qdrant(background_tasks: BackgroundTasks):
    """Reindex all documents in Qdrant with the new format"""
    background_tasks.add_task(reindex_all_documents)
    return {"status": "Reindexing started in background"}

def reindex_all_documents():
    """
    Reindex all documents in Qdrant with individual labels
    This should be run once after updating the code
    """
    try:
        # Get all documents that have labels and medicine_name
        documents = list(collection.find({
            "labels": {"$exists": True, "$ne": []},
            "medicine_name": {"$exists": True, "$ne": ""}
        }))
        
        print(f"Reindexing {len(documents)} documents to Qdrant with individual labels")
        
        # First, clear the collection to avoid duplicates
        try:
            # Reset Qdrant collection - careful with this in production!
            qdrant_service.client.delete_collection(qdrant_service.collection_name)
            qdrant_service._initialize_collection()
            print("Qdrant collection reset successfully")
        except Exception as e:
            print(f"Error resetting Qdrant collection: {str(e)}")
        
        # Now reindex all documents
        success_count = 0
        for doc in documents:
            if qdrant_service.insert_document(doc):
                success_count += 1
                # Add a small delay to avoid overwhelming the embedding API
                time.sleep(0.5)
        
        print(f"Successfully reindexed {success_count}/{len(documents)} documents to Qdrant")
    except Exception as e:
        print(f"Error during reindexing: {str(e)}")
#till here



if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
