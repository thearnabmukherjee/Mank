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
# from concurrent.futures import ThreadPoolExecutor
# import time
# from qdrant_client import QdrantClient
# from qdrant_client.http import models
# from qdrant_client.http.models import PointStruct
# import threading

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

# # Initialize OpenAI
# openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# # Qdrant Configuration
# qdrant_client = QdrantClient(
#     url=os.getenv("QDRANT_URL", "http://localhost:6333"),
#     api_key=os.getenv("QDRANT_API_KEY"),
# )

# QDRANT_COLLECTION_NAME = "medical_transcripts"
# EMBEDDING_MODEL = "text-embedding-ada-002"

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

# class BulkLabelResponse(BaseModel):
#     status: str
#     total_documents: int
#     processed_documents: int
#     labels_generated: int

# # Helper Functions
# def convert_object_ids(document: Dict[str, Any]) -> Dict[str, Any]:
#     """Convert all ObjectId fields to strings in a document"""
#     if document is None:
#         return None
        
#     document["_id"] = str(document["_id"])
#     if "audio_id" in document:
#         document["audio_id"] = str(document["audio_id"])
#     return document

# def initialize_qdrant_collection():
#     """Create or verify the Qdrant collection exists with proper configuration"""
#     try:
#         collections = qdrant_client.get_collections()
#         collection_names = [col.name for col in collections.collections]
        
#         if QDRANT_COLLECTION_NAME not in collection_names:
#             qdrant_client.create_collection(
#                 collection_name=QDRANT_COLLECTION_NAME,
#                 vectors_config=models.VectorParams(
#                     size=1536,  # ada-002 embedding size
#                     distance=models.Distance.COSINE,
#                 ),
#             )
#             print(f"Created new Qdrant collection: {QDRANT_COLLECTION_NAME}")
#         else:
#             print(f"Using existing Qdrant collection: {QDRANT_COLLECTION_NAME}")
#     except Exception as e:
#         print(f"Error initializing Qdrant collection: {str(e)}")
#         raise

# def generate_embeddings(text: str) -> List[float]:
#     """Generate embeddings using OpenAI's ada-002 model"""
#     try:
#         response = openai_client.embeddings.create(
#             input=text,
#             model=EMBEDDING_MODEL
#         )
#         return response.data[0].embedding
#     except Exception as e:
#         print(f"Error generating embeddings: {str(e)}")
#         return None

# def ensure_data_consistency():
#     """Periodically check and fix inconsistencies between MongoDB and Qdrant"""
#     try:
#         # First verify the collection exists
#         collections = qdrant_client.get_collections()
#         collection_names = [col.name for col in collections.collections]
        
#         if QDRANT_COLLECTION_NAME not in collection_names:
#             print(f"Collection {QDRANT_COLLECTION_NAME} not found, creating it...")
#             initialize_qdrant_collection()
#             return  # Skip first consistency check since we just created the collection

#         # Get all document IDs from MongoDB
#         mongo_ids = set(str(doc["_id"]) for doc in collection.find({}, {"_id": 1}))
        
#         # Get all point IDs from Qdrant
#         qdrant_ids = set()
#         for point in qdrant_client.scroll(
#             collection_name=QDRANT_COLLECTION_NAME,
#             with_payload=False,
#             with_vectors=False
#         ):
#             qdrant_ids.add(point.id)
        
#         # Find missing documents in Qdrant
#         missing_in_qdrant = mongo_ids - qdrant_ids
#         if missing_in_qdrant:
#             print(f"Found {len(missing_in_qdrant)} documents missing in Qdrant")
#             for doc_id in missing_in_qdrant:
#                 doc = collection.find_one({"_id": ObjectId(doc_id)})
#                 if doc and doc.get("text"):
#                     embedding = generate_embeddings(doc["text"])
#                     if embedding:
#                         point = PointStruct(
#                             id=doc_id,
#                             vector=embedding,
#                             payload={
#                                 "text": doc.get("text", ""),
#                                 "title": doc.get("title"),
#                                 "medicine_name": doc.get("medicine_name"),
#                                 "labels": doc.get("labels", []),
#                                 "created_at": doc.get("created_at", datetime.now()).isoformat(),
#                                 "updated_at": doc.get("updated_at", datetime.now()).isoformat(),
#                                 "mongo_id": doc_id
#                             }
#                         )
#                         qdrant_client.upsert(
#                             collection_name=QDRANT_COLLECTION_NAME,
#                             points=[point]
#                         )
        
#         # Find orphaned documents in Qdrant
#         orphaned_in_qdrant = qdrant_ids - mongo_ids
#         if orphaned_in_qdrant:
#             print(f"Found {len(orphaned_in_qdrant)} orphaned documents in Qdrant")
#             qdrant_client.delete(
#                 collection_name=QDRANT_COLLECTION_NAME,
#                 points_selector=models.PointIdsList(
#                     points=list(orphaned_in_qdrant)
#                 )
#             )
            
#     except Exception as e:
#         print(f"Data consistency check failed: {str(e)}")

# def schedule_consistency_checks(interval_hours=24):
#     """Background task for periodic data consistency checks"""
#     while True:
#         ensure_data_consistency()
#         time.sleep(interval_hours * 3600)

# # Initialize Qdrant collection at startup
# try:
#     initialize_qdrant_collection()
#     print("Successfully initialized Qdrant collection")
# except Exception as e:
#     print(f"Failed to initialize Qdrant collection: {str(e)}")
#     raise

# # Start the consistency check thread
# consistency_thread = threading.Thread(target=schedule_consistency_checks, daemon=True)
# consistency_thread.start()

# # [Rest of your existing code remains exactly the same...]
# # All the label extraction functions, API endpoints, etc. stay unchanged


# #  Label extraction utility functions
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
# - MR suggestions (feedback, insights)
# - Competition comparisons
# - Market trends (growth, shifts)
# - Feedback

# **Transcript:**
# {transcript}

# **Response Format:**
# Return a JSON object with:
# - "related_labels": comma-separated list of labels
# - "medicine_name": extracted medicine name if found
# """.format(transcript=text)
    
#     try:
#         response = openai_client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You extract business-relevant labels from medical transcripts."},
#                 {"role": "user", "content": prompt}  
#             ],
#             response_format={"type": "json_object"}  
#         )
        
#         if not response.choices:
#             raise ValueError("No choices in response")
        
#         content = response.choices[0].message.content
#         if not content:
#             raise ValueError("Empty content in response")
        
#         # Parse JSON response
#         try:
#             result = json.loads(content)
#         except json.JSONDecodeError:
#             if "```json" in content:
#                 content = content.split("```json")[1].split("```")[0].strip()
#                 result = json.loads(content)
#             else:
#                 raise ValueError("Invalid JSON response format")
        
#         # Process labels
#         labels = []
#         if "related_labels" in result:
#             labels = [label.strip() for label in result["related_labels"].split(",") if label.strip()]
        
#         return labels, result.get("medicine_name", None)
            
#     except Exception as e:
#         print(f"Error extracting labels: {str(e)}")
#         return [], None

# def process_label_extraction(document_id: str):
#     """Process label extraction for a single document with rate limiting"""
#     try:
#         time.sleep(1)  # Rate limiting
        
#         doc = collection.find_one({"_id": ObjectId(document_id)})
#         if not doc or not doc.get("text"):
#             return
        
#         labels, medicine_name = extract_labels_from_text(doc["text"])
        
#         update_data = {
#             "labels": labels,
#             "updated_at": datetime.now()
#         }
        
#         if medicine_name and medicine_name.lower() != "unknown":
#             if doc.get("medicine_name") != medicine_name:
#                 update_data["medicine_name"] = medicine_name
        
#         collection.update_one(
#             {"_id": ObjectId(document_id)},
#             {"$set": update_data}
#         )
        
#         # Update Qdrant
#         embedding = generate_embeddings(doc["text"])
#         if embedding:
#             point = PointStruct(
#                 id=str(document_id),
#                 vector=embedding,
#                 payload={
#                     "text": doc.get("text", ""),
#                     "title": doc.get("title"),
#                     "medicine_name": medicine_name or doc.get("medicine_name"),
#                     "labels": labels,
#                     "updated_at": datetime.now().isoformat(),
#                     "mongo_id": str(document_id)
#                 }
#             )
#             qdrant_client.upsert(
#                 collection_name=QDRANT_COLLECTION_NAME,
#                 points=[point]
#             )
        
#     except Exception as e:
#         print(f"Error processing label extraction for {document_id}: {str(e)}")

# def process_all_documents_label_extraction():
#     """Process label extraction for all documents with parallel processing"""
#     try:
#         documents = list(collection.find({"text": {"$exists": True, "$ne": ""}}, {"_id": 1}))
        
#         with ThreadPoolExecutor(max_workers=5) as executor:
#             executor.map(process_label_extraction, [str(doc["_id"]) for doc in documents])
            
#     except Exception as e:
#         print(f"Error processing label extraction for all documents: {str(e)}")

# def migrate_all_documents_to_qdrant():
#     """Migrate all documents from MongoDB to Qdrant"""
#     try:
#         initialize_qdrant_collection()
        
#         documents = collection.find({})
#         total_count = collection.count_documents({})
#         processed = 0
        
#         for doc in documents:
#             try:
#                 embedding = generate_embeddings(doc.get("text", ""))
#                 if not embedding:
#                     continue
                
#                 point = PointStruct(
#                     id=str(doc["_id"]),
#                     vector=embedding,
#                     payload={
#                         "text": doc.get("text", ""),
#                         "title": doc.get("title"),
#                         "medicine_name": doc.get("medicine_name"),
#                         "labels": doc.get("labels", []),
#                         "created_at": doc.get("created_at", datetime.now()).isoformat(),
#                         "updated_at": doc.get("updated_at", datetime.now()).isoformat(),
#                         "mongo_id": str(doc["_id"])
#                     }
#                 )
                
#                 qdrant_client.upsert(
#                     collection_name=QDRANT_COLLECTION_NAME,
#                     points=[point]
#                 )
                
#                 processed += 1
#                 if processed % 100 == 0:
#                     print(f"Migration progress: {processed}/{total_count}")
                    
#             except Exception as e:
#                 print(f"Error migrating document {doc['_id']}: {str(e)}")
#                 continue
                
#         print(f"Migration completed. Processed {processed}/{total_count} documents")
        
#     except Exception as e:
#         print(f"Migration failed: {str(e)}")

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
    
#     # Add to Qdrant
#     embedding = generate_embeddings(text)
#     if embedding:
#         point = PointStruct(
#             id=str(result.inserted_id),
#             vector=embedding,
#             payload={
#                 "text": text,
#                 "title": title,
#                 "medicine_name": medicine_name,
#                 "labels": [],
#                 "created_at": datetime.now().isoformat(),
#                 "updated_at": datetime.now().isoformat(),
#                 "mongo_id": str(result.inserted_id)
#             }
#         )
#         qdrant_client.upsert(
#             collection_name=QDRANT_COLLECTION_NAME,
#             points=[point]
#         )
    
#     if text:
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
# async def get_all_documents(enhanced: bool = False, limit: int = 100, offset: int = 0):
#     """Get all documents sorted by last updated"""
#     documents = list(collection.find().sort("updated_at", -1).skip(offset).limit(limit))
    
#     if not enhanced:
#         return [convert_object_ids(doc) for doc in documents]
    
#     enhanced_docs = []
#     for doc in documents:
#         enhanced_doc = convert_object_ids(doc)
        
#         if doc.get("text"):
#             embedding = generate_embeddings(doc["text"])
#             if embedding:
#                 similar = qdrant_client.search(
#                     collection_name=QDRANT_COLLECTION_NAME,
#                     query_vector=embedding,
#                     query_filter=models.Filter(
#                         must_not=[models.FieldCondition(
#                             key="mongo_id",
#                             match=models.MatchValue(value=str(doc["_id"]))
#                         )]
#                     ),
#                     limit=3,
#                     with_payload=True
#                 )
#                 enhanced_doc["similar_transcripts"] = [
#                     {
#                         "id": hit.id,
#                         "score": hit.score,
#                         "title": hit.payload.get("title"),
#                         "medicine_name": hit.payload.get("medicine_name")
#                     }
#                     for hit in similar
#                 ]
        
#         enhanced_docs.append(enhanced_doc)
    
#     return enhanced_docs

# @app.get("/transcripts/all", response_model=List[Dict[str, Any]])
# async def get_all_transcripts(enhanced: bool = False, limit: int = 100, offset: int = 0):
#     """Alias for get_all_documents for backward compatibility"""
#     return await get_all_documents(enhanced, limit, offset)

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
    
#     # Update Qdrant if text changed
#     if "text" in update_data:
#         embedding = generate_embeddings(text)
#         if embedding:
#             point = PointStruct(
#                 id=document_id,
#                 vector=embedding,
#                 payload={
#                     "text": text,
#                     "title": title or doc.get("title"),
#                     "medicine_name": medicine_name or doc.get("medicine_name"),
#                     "updated_at": datetime.now().isoformat(),
#                     "mongo_id": document_id
#                 }
#             )
#             qdrant_client.upsert(
#                 collection_name=QDRANT_COLLECTION_NAME,
#                 points=[point]
#             )
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
    
#     # Delete from Qdrant
#     qdrant_client.delete(
#         collection_name=QDRANT_COLLECTION_NAME,
#         points_selector=models.PointIdsList(points=[document_id])
#     )
    
#     result = collection.delete_one({"_id": ObjectId(document_id)})
#     return {"deleted_count": result.deleted_count}

# # Label Endpoints
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
# async def get_all_labels(enhanced: bool = False):
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
    
#     if not enhanced:
#         return [{
#             "label": label["_id"],
#             "document_count": label["document_count"],
#             "documents": [{
#                 "id": str(doc["id"]),
#                 "title": doc.get("title", "Untitled"),
#                 "text_preview": doc["text_preview"] + ("..." if len(doc["text_preview"]) == 100 else ""),
#                 "updated_at": doc["updated_at"]
#             } for doc in label["documents"]]
#         } for label in labels]
    
#     # Enhanced version with vector clusters
#     enhanced_labels = []
#     for label in labels:
#         # Get cluster information from Qdrant
#         cluster_info = []
#         for doc in label["documents"][:3]:  # Sample 3 documents per label
#             doc_data = collection.find_one({"_id": doc["id"]})
#             if doc_data and doc_data.get("text"):
#                 embedding = generate_embeddings(doc_data["text"])
#                 if embedding:
#                     similar = qdrant_client.search(
#                         collection_name=QDRANT_COLLECTION_NAME,
#                         query_vector=embedding,
#                         limit=5,
#                         with_payload=True
#                     )
#                     cluster_info.append({
#                         "representative_text": doc_data["text"][:100] + "...",
#                         "similar_documents": [
#                             {
#                                 "id": hit.id,
#                                 "score": hit.score,
#                                 "title": hit.payload.get("title"),
#                                 "medicine_name": hit.payload.get("medicine_name")
#                             }
#                             for hit in similar
#                         ]
#                     })
        
#         enhanced_labels.append({
#             "label": label["_id"],
#             "document_count": label["document_count"],
#             "documents": [{
#                 "id": str(doc["id"]),
#                 "title": doc.get("title", "Untitled"),
#                 "text_preview": doc["text_preview"] + ("..." if len(doc["text_preview"]) == 100 else ""),
#                 "updated_at": doc["updated_at"]
#             } for doc in label["documents"]],
#             "clusters": cluster_info
#         })
    
#     return enhanced_labels

# @app.get("/labels/{label}", response_model=LabelResponse)
# async def get_label_details(label: str, enhanced: bool = False):
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
    
#     if not enhanced:
#         return {
#             "label": label,
#             "document_count": len(documents),
#             "documents": [{
#                 "id": str(doc["_id"]),
#                 "title": doc.get("title", "Untitled"),
#                 "text_preview": doc["text"] + ("..." if len(doc["text"]) == 100 else ""),
#                 "updated_at": doc["updated_at"],
#                 "has_audio": doc.get("has_audio", False)
#             } for doc in documents]
#         }
    
#     # Enhanced version with vector clusters
#     clusters = []
#     for doc in documents[:3]:  # Sample 3 documents
#         doc_data = collection.find_one({"_id": doc["_id"]})
#         if doc_data and doc_data.get("text"):
#             embedding = generate_embeddings(doc_data["text"])
#             if embedding:
#                 similar = qdrant_client.search(
#                     collection_name=QDRANT_COLLECTION_NAME,
#                     query_vector=embedding,
#                     limit=5,
#                     with_payload=True
#                 )
#                 clusters.append({
#                     "representative_text": doc_data["text"][:100] + "...",
#                     "similar_documents": [
#                         {
#                             "id": hit.id,
#                             "score": hit.score,
#                             "title": hit.payload.get("title"),
#                             "medicine_name": hit.payload.get("medicine_name")
#                         }
#                         for hit in similar
#                     ]
#                 })
    
#     return {
#         "label": label,
#         "document_count": len(documents),
#         "documents": [{
#             "id": str(doc["_id"]),
#             "title": doc.get("title", "Untitled"),
#             "text_preview": doc["text"] + ("..." if len(doc["text"]) == 100 else ""),
#             "updated_at": doc["updated_at"],
#             "has_audio": doc.get("has_audio", False)
#         } for doc in documents],
#         "clusters": clusters
#     }

# @app.get("/labels/enhanced", response_model=List[Dict[str, Any]])
# async def get_enhanced_labels():
#     """Get all labels with vector-based clustering information"""
#     try:
#         pipeline = [
#             {"$unwind": "$labels"},
#             {"$group": {"_id": "$labels", "count": {"$sum": 1}}},
#             {"$sort": {"count": -1}}
#         ]
#         labels = list(collection.aggregate(pipeline))
        
#         enhanced_labels = []
#         for label in labels:
#             docs = list(collection.find(
#                 {"labels": label["_id"]},
#                 {"text": 1, "title": 1, "medicine_name": 1},
#                 limit=3
#             ))
            
#             cluster_info = []
#             for doc in docs:
#                 if "text" in doc:
#                     embedding = generate_embeddings(doc["text"])
#                     if embedding:
#                         similar = qdrant_client.search(
#                             collection_name=QDRANT_COLLECTION_NAME,
#                             query_vector=embedding,
#                             limit=5,
#                             with_payload=True
#                         )
#                         cluster_info.append({
#                             "representative_text": doc["text"][:100] + "...",
#                             "similar_documents": [
#                                 {
#                                     "id": hit.id,
#                                     "score": hit.score,
#                                     "title": hit.payload.get("title"),
#                                     "medicine_name": hit.payload.get("medicine_name")
#                                 }
#                                 for hit in similar
#                             ]
#                         })
            
#             enhanced_labels.append({
#                 "label": label["_id"],
#                 "document_count": label["count"],
#                 "clusters": cluster_info
#             })
        
#         return enhanced_labels
        
#     except Exception as e:
#         raise HTTPException(500, detail=str(e))

# # Search Endpoints
# @app.get("/search/semantic")
# async def semantic_search(
#     query: str,
#     label_filter: Optional[str] = None,
#     medicine_filter: Optional[str] = None,
#     limit: int = 10
# ):
#     """Semantic search using vector embeddings"""
#     try:
#         query_embedding = generate_embeddings(query)
#         if not query_embedding:
#             raise HTTPException(400, detail="Failed to generate query embedding")
        
#         filter_conditions = []
#         if label_filter:
#             filter_conditions.append(
#                 models.FieldCondition(
#                     key="labels",
#                     match=models.MatchValue(value=label_filter)
#             ))
#         if medicine_filter:
#             filter_conditions.append(
#                 models.FieldCondition(
#                     key="medicine_name",
#                     match=models.MatchValue(value=medicine_filter)
#                 )
#             )
        
#         search_result = qdrant_client.search(
#             collection_name=QDRANT_COLLECTION_NAME,
#             query_vector=query_embedding,
#             query_filter=models.Filter(
#                 must=filter_conditions if filter_conditions else None
#             ),
#             limit=limit,
#             with_payload=True
#         )
        
#         results = []
#         for hit in search_result:
#             doc = collection.find_one({"_id": ObjectId(hit.id)})
#             if doc:
#                 results.append({
#                     "score": hit.score,
#                     "document": convert_object_ids(doc),
#                     "payload": hit.payload
#                 })
        
#         return results
        
#     except Exception as e:
#         raise HTTPException(500, detail=str(e))

# @app.get("/search/hybrid")
# async def hybrid_search(
#     query: str,
#     label_filter: Optional[str] = None,
#     medicine_filter: Optional[str] = None,
#     limit: int = 10
# ):
#     """Hybrid search combining vector and keyword search"""
#     try:
#         # Vector search
#         query_embedding = generate_embeddings(query)
#         vector_results = []
#         if query_embedding:
#             filter_conditions = []
#             if label_filter:
#                 filter_conditions.append(
#                     models.FieldCondition(
#                         key="labels",
#                         match=models.MatchValue(value=label_filter)
#                     )
#                 )
#             if medicine_filter:
#                 filter_conditions.append(
#                     models.FieldCondition(
#                         key="medicine_name",
#                         match=models.MatchValue(value=medicine_filter)
#                     )
#                 )
            
#             vector_results = qdrant_client.search(
#                 collection_name=QDRANT_COLLECTION_NAME,
#                 query_vector=query_embedding,
#                 query_filter=models.Filter(
#                     must=filter_conditions if filter_conditions else None
#                 ),
#                 limit=limit,
#                 with_payload=True
#             )
        
#         # Keyword search in MongoDB
#         keyword_results = list(collection.find(
#             {
#                 "$text": {"$search": query},
#                 **({"labels": label_filter} if label_filter else {}),
#                 **({"medicine_name": medicine_filter} if medicine_filter else {})
#             },
#             {"score": {"$meta": "textScore"}},
#             limit=limit
#         ).sort([("score", {"$meta": "textScore"})]))
        
#         # Combine and deduplicate results
#         combined = []
#         seen_ids = set()
        
#         for hit in vector_results:
#             doc_id = hit.payload.get("mongo_id")
#             if doc_id and doc_id not in seen_ids:
#                 doc = collection.find_one({"_id": ObjectId(doc_id)})
#                 if doc:
#                     combined.append({
#                         "type": "vector",
#                         "score": hit.score,
#                         "document": convert_object_ids(doc)
#                     })
#                     seen_ids.add(doc_id)
        
#         for doc in keyword_results:
#             doc_id = str(doc["_id"])
#             if doc_id not in seen_ids:
#                 combined.append({
#                     "type": "keyword",
#                     "score": doc.get("score", 0),
#                     "document": convert_object_ids(doc)
#                 })
#                 seen_ids.add(doc_id)
        
#         combined.sort(key=lambda x: x["score"], reverse=True)
        
#         return combined[:limit]
        
#     except Exception as e:
#         raise HTTPException(500, detail=str(e))

# # Migration Endpoints
# @app.post("/migrate/to-qdrant")
# async def migrate_to_qdrant(background_tasks: BackgroundTasks):
#     """Trigger background migration of all documents to Qdrant"""
#     background_tasks.add_task(migrate_all_documents_to_qdrant)
#     return {"status": "Migration started in background"}

# @app.get("/bulk-extract-labels/status", response_model=BulkLabelResponse)
# async def get_bulk_extract_status():
#     """Get extraction status"""
#     total = collection.count_documents({})
#     processed = collection.count_documents({"labels": {"$exists": True}})
#     pipeline = [{"$unwind": "$labels"}, {"$group": {"_id": None, "count": {"$sum": 1}}}]
#     result = list(collection.aggregate(pipeline))
#     return {
#         "status": "complete" if processed >= total else "in progress",
#         "total_documents": total,
#         "processed_documents": processed,
#         "labels_generated": result[0]["count"] if result else 0
#     }

# if __name__ == "__main__":
#     # initialize_qdrant_collection()
#     uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)






# -------------------------------------------------------------------------------------------------------------------------------------------------------------------->
import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_community.embeddings import OpenAIEmbeddings
import os
import json
import uuid
from typing import Dict, Any, List
from openai import OpenAI

# Configuration - use st.secrets or environment variables for production
COLLECTION_NAME = "mongodb_to_qdrant"
EMBEDDING_MODEL = "text-embedding-ada-002"

# Initialize clients - all in-memory for local development
@st.cache_resource
def init_qdrant():
    # Local in-memory Qdrant - no Docker needed
    return QdrantClient(":memory:")

@st.cache_resource
def init_embeddings():
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    )

@st.cache_resource
def init_openai():
    return OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")))

qdrant_client = init_qdrant()
embeddings = init_embeddings()
openai_client = init_openai()

# Initialize collection if it doesn't exist
try:
    qdrant_client.get_collection(COLLECTION_NAME)
except Exception:
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=1536,  # ada-002 embedding size
            distance=Distance.COSINE
        )
    )

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "How can I help you today?"})

def add_documents_to_qdrant(documents: List[str]):
    """Add documents to Qdrant with embeddings"""
    if not documents:
        return
    
    # Generate embeddings
    doc_embeddings = embeddings.embed_documents(documents)
    
    # Prepare points for Qdrant
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={"text": text}
        )
        for text, embedding in zip(documents, doc_embeddings)
    ]
    
    # Upsert to Qdrant
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True
    )

def similarity_search(query: str, k: int = 3) -> List[str]:
    """Perform similarity search and return results"""
    query_embedding = embeddings.embed_query(query)
    
    search_results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=k
    )
    
    return [hit.payload["text"] for hit in search_results]

def generate_response(query: str, context: List[str]) -> str:
    """Generate response using context from vector search"""
    if not context:
        return "I couldn't find relevant information to answer your question."
    
    context_str = "\n".join(f"- {text}" for text in context)
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"""Answer the question using only this context:
                 
                 {context_str}
                 
                 If the context doesn't contain the answer, say you don't know."""},
                {"role": "user", "content": query}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {str(e)}"

# Streamlit UI
st.title("🤖 Local Qdrant Chatbot")

# Sidebar for document upload
with st.sidebar:
    st.header("Add Knowledge")
    
    # Simple text area for adding documents
    new_docs = st.text_area("Add new documents (one per line):", height=150)
    if st.button("Add Documents"):
        if new_docs:
            documents = [doc.strip() for doc in new_docs.split("\n") if doc.strip()]
            add_documents_to_qdrant(documents)
            st.success(f"Added {len(documents)} documents!")
        else:
            st.warning("Please enter some documents")
    
    st.markdown("---")
    st.info("Using in-memory Qdrant with OpenAI embeddings")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get and display assistant response
    with st.chat_message("assistant"):
        # First find relevant documents
        relevant_docs = similarity_search(prompt, k=3)
        
        # Then generate response
        response = generate_response(prompt, relevant_docs)
        
        st.markdown(response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})