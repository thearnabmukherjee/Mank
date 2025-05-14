# # qdrant_service.py
# import os
# import uuid
# from pymongo import MongoClient
# from qdrant_client import QdrantClient
# from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition
# from dotenv import load_dotenv
# import openai
# from urllib.parse import quote_plus
# from typing import List, Dict, Any, Optional

# # Load environment variables
# load_dotenv()

# class QdrantService:
#     def __init__(self):
#         # Qdrant setup
#         self.qdrant_url = os.getenv("QDRANT_URL")
#         self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
#         self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
#         self.collection_name = "Pharma"
        
#         # Initialize collection
#         self._initialize_collection()
        
#         # OpenAI setup
#         openai.api_key = os.getenv("OPENAI_API_KEY")

#     def _initialize_collection(self):
#         """Initialize or verify the Qdrant collection exists with correct configuration"""
#         try:
#             collection_info = self.client.get_collection(self.collection_name)
#             print(f"Collection '{self.collection_name}' already exists.")
            
#             if collection_info.vectors_config.params.size != 128:
#                 print(f"Warning: Collection exists but has different vector size. Expected 128, found {collection_info.vectors_config.params.size}")
#         except Exception as e:
#             if "not found" in str(e):
#                 try:
#                     self.client.create_collection(
#                         collection_name=self.collection_name,
#                         vectors_config=VectorParams(size=1536, distance=Distance.COSINE))
#                     print(f"Collection '{self.collection_name}' created successfully.")
#                 except Exception as create_error:
#                     print(f"Collection creation failed: {create_error}")
#             else:
#                 print(f"Error checking collection: {e}")

#     def get_text_embedding(self, text: str) -> List[float]:
#         try:
#             response = openai.embeddings.create(
#                 model="text-embedding-ada-002",
#                 input=text
#             )
#             return response.data[0].embedding
#         except Exception as e:
#             print(f"Error in getting embedding: {str(e)}")
#             return []

#     def is_ready_for_qdrant(self, doc: Dict[str, Any]) -> bool:
#         """Check if document meets criteria for Qdrant upload"""
#         has_labels = bool(doc.get('labels')) and len(doc.get('labels', [])) > 0
#         has_medicine_name = bool(doc.get('medicine_name')) and doc.get('medicine_name', '').strip() != ''
#         has_text = bool(doc.get('text')) and doc.get('text', '').strip() != ''
        
#         if not all([has_labels, has_medicine_name, has_text]):
#             print(f"Document {doc.get('_id')} not ready for Qdrant - missing required fields")
#             print(f"Labels: {has_labels}, Medicine: {has_medicine_name}")
#             return False
#         return True

#     def insert_document(self, doc: Dict[str, Any]) -> bool:
#         """Insert document with individual points for each label and its reason"""
#         if not self.is_ready_for_qdrant(doc):
#             return False
        
#         text = doc.get('text', '')
#         medicine_name = doc.get('medicine_name', '')
#         labels = doc.get('labels', [])
#         label_reasons = doc.get('label_reason', {})
        
#         if not labels:
#             print(f"Document {doc.get('_id')} has no labels to store in Qdrant")
#             return False
        
#         # Get base vector for the document text
#         base_vector = self.get_text_embedding(text)
#         if not base_vector:
#             return False
        
#         # Ensure vector is exactly 128 dimensions
#         base_vector = base_vector[:128] if len(base_vector) > 128 else base_vector + [0.0] * (128 - len(base_vector))
        
#         points = []
#         success = False
        
#         # Create individual points for each label
#         for label in labels:
#             # Create a unique ID for each medicine_name + label combination
#             point_id = str(uuid.uuid5(
#                 uuid.NAMESPACE_OID, 
#                 f"{str(doc.get('_id'))}_{medicine_name}_{label}"
#             ))
            
#             # Get the reason for this label, if available
#             reason = label_reasons.get(label, "")
            
#             point = PointStruct(
#                 id=point_id,
#                 vector=base_vector,
#                 payload={
                    
                    
#                     'medicine_name': medicine_name,
#                     'label': label,
#                     'label_reason': reason,
                    
#                 }
#             )
#             points.append(point)
        
#         try:
#             if points:
#                 self.client.upsert(
#                     collection_name=self.collection_name,
#                     points=points
#                 )
#                 print(f"Successfully inserted {len(points)} label points for document {doc.get('_id')} into Qdrant")
#                 success = True
#             return success
#         except Exception as e:
#             print(f"Error inserting document {doc.get('_id')}: {str(e)}")
#             return False

#     def update_document(self, doc: Dict[str, Any]) -> bool:
#         """Update document by first deleting existing entries and then re-inserting"""
#         mongo_id = str(doc.get('_id'))
        
#         try:
#             # First, find all points related to this document
#             filter_condition = Filter(
#                 must=[
#                     FieldCondition(key="mongo_id", match={"value": mongo_id})
#                 ]
#             )
            
#             search_result = self.client.scroll(
#                 collection_name=self.collection_name,
#                 filter=filter_condition,
#                 limit=100,
#                 with_payload=False,
#                 with_vectors=False
#             )
            
#             point_ids = [point.id for point in search_result[0]]
            
#             # Delete all found points
#             if point_ids:
#                 self.client.delete(
#                     collection_name=self.collection_name,
#                     points_selector=point_ids
#                 )
#                 print(f"Deleted {len(point_ids)} existing points for document {mongo_id}")
            
#             # Re-insert with updated information
#             return self.insert_document(doc)
#         except Exception as e:
#             print(f"Error updating document {mongo_id}: {str(e)}")
#             return False

#     def delete_document(self, mongo_id: str) -> bool:
#         """Delete document from Qdrant by its MongoDB ID"""
#         try:
#             # First, find all points related to this document
#             filter_condition = Filter(
#                 must=[
#                     FieldCondition(key="mongo_id", match={"value": mongo_id})
#                 ]
#             )
            
#             search_result = self.client.scroll(
#                 collection_name=self.collection_name,
#                 filter=filter_condition,
#                 limit=100,
#                 with_payload=False,
#                 with_vectors=False
#             )
            
#             point_ids = [point.id for point in search_result[0]]
            
#             # Delete all found points
#             if point_ids:
#                 self.client.delete(
#                     collection_name=self.collection_name,
#                     points_selector=point_ids
#                 )
#                 print(f"Deleted {len(point_ids)} points for document {mongo_id}")
#                 return True
#             return False
#         except Exception as e:
#             print(f"Error deleting document {mongo_id}: {str(e)}")
#             return False

#     def search_similar(self, text: str, limit: int = 5) -> List[Dict[str, Any]]:
#         vector = self.get_text_embedding(text)
#         if not vector:
#             return []
        
#         vector = vector[:128] if len(vector) > 128 else vector + [0.0] * (128 - len(vector))
        
#         try:
#             results = self.client.search(
#                 collection_name=self.collection_name,
#                 query_vector=vector,
#                 limit=limit,
#                 with_payload=True,
#                 with_vectors=False
#             )
#             return [{
#                 'id': hit.id,
#                 'score': hit.score,
#                 'payload': hit.payload
#             } for hit in results]
#         except Exception as e:
#             print(f"Error searching similar documents: {str(e)}")
#             return []


# # Replace the duplicate search_by_medicine_and_label with this single implementation
# # qdrant.py - Update the QdrantService class
# # class QdrantService:
#     # ... (keep existing __init__ and other methods)

#     def search_by_medicine_and_label(self, medicine_name: str, label: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
#         """Search for documents with specific medicine_name and optionally a specific label"""
#         try:
#             # Create filter conditions
#             must_conditions = [
#                 FieldCondition(key="medicine_name", match={"value": medicine_name})
#             ]
            
#             if label:
#                 must_conditions.append(
#                     FieldCondition(key="label", match={"value": label})
#                 )
            
#             # Search with the filter
#             search_result = self.client.search(
#                 collection_name=self.collection_name,
#                 query_filter=Filter(must=must_conditions),
#                 limit=limit,
#                 with_payload=True,
#                 with_vectors=False
#             )
            
#             # Format results with scores
#             return [{
#                 'id': hit.id,
#                 'score': hit.score,
#                 'payload': hit.payload
#             } for hit in search_result]
            
#         except Exception as e:
#             print(f"Error in search_by_medicine_and_label: {str(e)}")
#             return []
    




#     # def search_by_medicine_and_label(self, medicine_name: str, label: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
#     #     """Search for documents with specific medicine_name and optionally a specific label"""
#     #     try:
#     #         conditions = [FieldCondition(key="medicine_name", match={"value": medicine_name})]
            
#     #         if label:
#     #             conditions.append(FieldCondition(key="label", match={"value": label}))
            
#     #         filter_condition = Filter(must=conditions)
            
#     #         results = self.client.scroll(
#     #             collection_name=self.collection_name,
#     #             filter=filter_condition,
#     #             limit=limit,
#     #             with_payload=True,
#     #             with_vectors=False
#     #         )
            
#     #         # Format the results
#     #         formatted_results = [{
#     #             'id': hit.id,
#     #             'payload': hit.payload
#     #         } for hit in results[0]]
            
#     #         return formatted_results
#     #     except Exception as e:
#     #         print(f"Error searching by medicine and label: {str(e)}")
#     #         return []

# # Initialize Qdrant service
# qdrant_service = QdrantService()








# qdrant_service.py
# import os
# import uuid
# from pymongo import MongoClient
# from qdrant_client import QdrantClient
# from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition
# from dotenv import load_dotenv
# import openai
# from urllib.parse import quote_plus
# from typing import List, Dict, Any, Optional

# # Load environment variables
# load_dotenv()

# class QdrantService:
#     def __init__(self):
#         # Qdrant setup
#         self.qdrant_url = os.getenv("QDRANT_URL")
#         self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
#         self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
#         self.collection_name = "Pharma"
#         self.vector_dimension = 1536  # Updated to 1536 dimensions
        
#         # Initialize collection
#         self._initialize_collection()
        
#         # OpenAI setup
#         openai.api_key = os.getenv("OPENAI_API_KEY")

#     def _initialize_collection(self):
#         """Initialize or verify the Qdrant collection exists with correct configuration"""
#         try:
#             collection_info = self.client.get_collection(self.collection_name)
#             print(f"Collection '{self.collection_name}' already exists.")
            
#             if collection_info.vectors_config.params.size != self.vector_dimension:
#                 print(f"Warning: Collection exists but has different vector size. Expected {self.vector_dimension}, found {collection_info.vectors_config.params.size}")
#         except Exception as e:
#             if "not found" in str(e):
#                 try:
#                     self.client.create_collection(
#                         collection_name=self.collection_name,
#                         vectors_config=VectorParams(size=self.vector_dimension, distance=Distance.COSINE))
#                     print(f"Collection '{self.collection_name}' created successfully.")
#                 except Exception as create_error:
#                     print(f"Collection creation failed: {create_error}")
#             else:
#                 print(f"Error checking collection: {e}")

#     def get_text_embedding(self, text: str) -> List[float]:
#         try:
#             response = openai.embeddings.create(
#                 model="text-embedding-ada-002",
#                 input=text
#             )
#             return response.data[0].embedding
#         except Exception as e:
#             print(f"Error in getting embedding: {str(e)}")
#             return []

#     def is_ready_for_qdrant(self, doc: Dict[str, Any]) -> bool:
#         """Check if document meets criteria for Qdrant upload"""
#         has_labels = bool(doc.get('labels')) and len(doc.get('labels', [])) > 0
#         has_medicine_name = bool(doc.get('medicine_name')) and doc.get('medicine_name', '').strip() != ''
#         has_text = bool(doc.get('text')) and doc.get('text', '').strip() != ''
        
#         if not all([has_labels, has_medicine_name, has_text]):
#             print(f"Document {doc.get('_id')} not ready for Qdrant - missing required fields")
#             print(f"Labels: {has_labels}, Medicine: {has_medicine_name}")
#             return False
#         return True

#     def insert_document(self, doc: Dict[str, Any]) -> bool:
#         """Insert document with individual points for each label and its reason"""
#         if not self.is_ready_for_qdrant(doc):
#             return False
        
#         text = doc.get('text', '')
#         medicine_name = doc.get('medicine_name', '')
#         labels = doc.get('labels', [])
#         label_reasons = doc.get('label_reason', {})
        
#         if not labels:
#             print(f"Document {doc.get('_id')} has no labels to store in Qdrant")
#             return False
        
#         # Get base vector for the document text
#         base_vector = self.get_text_embedding(text)
#         if not base_vector:
#             return False
        
#         # Ensure vector is exactly 1536 dimensions
#         base_vector = base_vector[:self.vector_dimension] if len(base_vector) > self.vector_dimension else base_vector + [0.0] * (self.vector_dimension - len(base_vector))
        
#         points = []
#         success = False
        
#         # Create individual points for each label
#         for label in labels:
#             # Create a unique ID for each medicine_name + label combination
#             point_id = str(uuid.uuid5(
#                 uuid.NAMESPACE_OID, 
#                 f"{str(doc.get('_id'))}_{medicine_name}_{label}"
#             ))
            
#             # Get the reason for this label, if available
#             reason = label_reasons.get(label, "")
            
#             point = PointStruct(
#                 id=point_id,
#                 vector=base_vector,
#                 payload={
#                     'mongo_id': str(doc.get('_id')),
#                     'medicine_name': medicine_name,
#                     'label': label,
#                     'label_reason': reason,
#                     'text': text
#                 }
#             )
#             points.append(point)
        
#         try:
#             if points:
#                 self.client.upsert(
#                     collection_name=self.collection_name,
#                     points=points
#                 )
#                 print(f"Successfully inserted {len(points)} label points for document {doc.get('_id')} into Qdrant")
#                 success = True
#             return success
#         except Exception as e:
#             print(f"Error inserting document {doc.get('_id')}: {str(e)}")
#             return False

#     def update_document(self, doc: Dict[str, Any]) -> bool:
#         """Update document by first deleting existing entries and then re-inserting"""
#         mongo_id = str(doc.get('_id'))
        
#         try:
#             # First, find all points related to this document
#             filter_condition = Filter(
#                 must=[
#                     FieldCondition(key="mongo_id", match={"value": mongo_id})
#                 ]
#             )
            
#             search_result = self.client.scroll(
#                 collection_name=self.collection_name,
#                 filter=filter_condition,
#                 limit=100,
#                 with_payload=False,
#                 with_vectors=False
#             )
            
#             point_ids = [point.id for point in search_result[0]]
            
#             # Delete all found points
#             if point_ids:
#                 self.client.delete(
#                     collection_name=self.collection_name,
#                     points_selector=point_ids
#                 )
#                 print(f"Deleted {len(point_ids)} existing points for document {mongo_id}")
            
#             # Re-insert with updated information
#             return self.insert_document(doc)
#         except Exception as e:
#             print(f"Error updating document {mongo_id}: {str(e)}")
#             return False

#     def delete_document(self, mongo_id: str) -> bool:
#         """Delete document from Qdrant by its MongoDB ID"""
#         try:
#             # First, find all points related to this document
#             filter_condition = Filter(
#                 must=[
#                     FieldCondition(key="mongo_id", match={"value": mongo_id})
#                 ]
#             )
            
#             search_result = self.client.scroll(
#                 collection_name=self.collection_name,
#                 filter=filter_condition,
#                 limit=100,
#                 with_payload=False,
#                 with_vectors=False
#             )
            
#             point_ids = [point.id for point in search_result[0]]
            
#             # Delete all found points
#             if point_ids:
#                 self.client.delete(
#                     collection_name=self.collection_name,
#                     points_selector=point_ids
#                 )
#                 print(f"Deleted {len(point_ids)} points for document {mongo_id}")
#                 return True
#             return False
#         except Exception as e:
#             print(f"Error deleting document {mongo_id}: {str(e)}")
#             return False

#     def search_similar(self, text: str, limit: int = 5) -> List[Dict[str, Any]]:
#         vector = self.get_text_embedding(text)
#         if not vector:
#             return []
        
#         vector = vector[:self.vector_dimension] if len(vector) > self.vector_dimension else vector + [0.0] * (self.vector_dimension - len(vector))
        
#         try:
#             results = self.client.search(
#                 collection_name=self.collection_name,
#                 query_vector=vector,
#                 limit=limit,
#                 with_payload=True,
#                 with_vectors=False
#             )
#             return [{
#                 'id': hit.id,
#                 'score': hit.score,
#                 'payload': hit.payload
#             } for hit in results]
#         except Exception as e:
#             print(f"Error searching similar documents: {str(e)}")
#             return []

#     def search_by_medicine_and_label(self, medicine_name: str, label: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
#         """Search for documents with specific medicine_name and optionally a specific label"""
#         try:
#             # Create filter conditions
#             must_conditions = [
#                 FieldCondition(key="medicine_name", match={"value": medicine_name})
#             ]
            
#             if label:
#                 must_conditions.append(
#                     FieldCondition(key="label", match={"value": label})
#                 )
            
#             # Search with the filter
#             search_result = self.client.search(
#                 collection_name=self.collection_name,
#                 query_filter=Filter(must=must_conditions),
#                 limit=limit,
#                 with_payload=True,
#                 with_vectors=False
#             )
            
#             # Format results with scores
#             return [{
#                 'id': hit.id,
#                 'score': hit.score,
#                 'payload': hit.payload
#             } for hit in search_result]
            
#         except Exception as e:
#             print(f"Error in search_by_medicine_and_label: {str(e)}")
#             return []

# # Initialize Qdrant service
# qdrant_service = QdrantService()

# qdrant_service.py
import os
import uuid
from pymongo import MongoClient
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition
from dotenv import load_dotenv
import openai
from urllib.parse import quote_plus
from typing import List, Dict, Any, Optional
from googletrans import Translator

# Load environment variables
load_dotenv()

class QdrantService:
    def __init__(self):
        # Qdrant setup
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")  # Default to localhost if not set
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        self.client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key if self.qdrant_api_key else None
        )
        self.collection_name = "Pharma"
        self.vector_dimension = 1536  # Using 1536 dimensions for OpenAI embeddings
        
        # Initialize collection
        self._initialize_collection()
        
        # OpenAI setup
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def _initialize_collection(self):
        """Initialize or verify the Qdrant collection exists with correct configuration"""
        try:
            # First try to get the collection info
            collection_info = self.client.get_collection(self.collection_name)
            print(f"Collection '{self.collection_name}' already exists.")
            
            # Check if the collection has the correct vector size
            if collection_info.vectors_config.params.size != self.vector_dimension:
                print(f"Warning: Collection exists but has different vector size. Expected {self.vector_dimension}, found {collection_info.vectors_config.params.size}")
                print("You'll need to recreate the collection with the correct dimensions.")
                return False
                
            return True
                
        except Exception as e:
            if "not found" in str(e).lower():
                print(f"Collection '{self.collection_name}' not found, creating it...")
                try:
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=self.vector_dimension, 
                            distance=Distance.COSINE
                        )
                    )
                    print(f"Collection '{self.collection_name}' created successfully with {self.vector_dimension} dimensions.")
                    return True
                except Exception as create_error:
                    print(f"Failed to create collection: {create_error}")
                    return False
            else:
                print(f"Error checking collection: {e}")
                return False

    def get_text_embedding(self, text: str) -> List[float]:
        """Get text embedding using OpenAI's API"""
        try:
            response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {str(e)}")
            return []

    def is_ready_for_qdrant(self, doc: Dict[str, Any]) -> bool:
        """Check if document has all required fields for Qdrant upload"""
        required_fields = {
            'labels': bool(doc.get('labels')) and len(doc.get('labels', [])) > 0,
            'medicine_name': bool(doc.get('medicine_name')) and doc.get('medicine_name', '').strip() != '',
            'text': bool(doc.get('text')) and doc.get('text', '').strip() != ''
        }
        
        if not all(required_fields.values()):
            print(f"Document {doc.get('_id')} missing required fields:")
            for field, present in required_fields.items():
                if not present:
                    print(f"- {field} is missing or empty")
            return False
        return True

    # def insert_document(self, doc: Dict[str, Any]) -> bool:
    #     """Insert document with individual points for each label"""
    #     if not self.is_ready_for_qdrant(doc):
    #         return False
        
    #     text = doc.get('text', '')
    #     medicine_name = doc.get('medicine_name', '')
    #     labels = doc.get('labels', [])
    #     label_reasons = doc.get('label_reason', {})
        
    #     # Get the embedding for the document text
    #     base_vector = self.get_text_embedding(text)
    #     if not base_vector:
    #         print(f"Failed to get embedding for document {doc.get('_id')}")
    #         return False
        
    #     # Ensure the vector has exactly 1536 dimensions
    #     if len(base_vector) != self.vector_dimension:
    #         print(f"Warning: Embedding has {len(base_vector)} dimensions, expected {self.vector_dimension}")
    #         base_vector = base_vector[:self.vector_dimension] if len(base_vector) > self.vector_dimension else base_vector + [0.0] * (self.vector_dimension - len(base_vector))
        
    #     points = []
    #     for label in labels:
    #         point_id = str(uuid.uuid5(
    #             uuid.NAMESPACE_OID, 
    #             f"{str(doc.get('_id'))}_{medicine_name}_{label}"
    #         ))
            
    #         reason = label_reasons.get(label, "")
            
    #         points.append(PointStruct(
    #             id=point_id,
    #             vector=base_vector,
    #             payload={
    #                 'mongo_id': str(doc.get('_id')),
    #                 'medicine_name': medicine_name,
    #                 'label': label,
    #                 'label_reason': reason,
    #                 'text': text
    #             }
    #         ))
        
    #     try:
    #         if points:
    #             self.client.upsert(
    #                 collection_name=self.collection_name,
    #                 points=points,
    #                 wait=True
    #             )
    #             print(f"Inserted {len(points)} points for document {doc.get('_id')}")
    #             return True
    #     except Exception as e:
    #         print(f"Error inserting document {doc.get('_id')}: {str(e)}")
        
    #     return False

    def _translate_to_english(self, text: str) -> str:
        """Translate text to English using Google Translate"""
        try:
            translator = Translator()
            translation = translator.translate(text, src='hi', dest='en')
            return translation.text
        except Exception as e:
            print(f"Translation failed: {str(e)}")
            return text  # Return original if translation fails

    def insert_document(self, doc: Dict[str, Any]) -> bool:
        """Insert document with individual points for each label and its reason"""
        if not self.is_ready_for_qdrant(doc):
            return False
        
        original_text = doc.get('text', '')
        # Translate text to English before storing
        english_text = self._translate_to_english(original_text)
        
        medicine_name = doc.get('medicine_name', '')
        labels = doc.get('labels', [])
        label_reasons = doc.get('label_reason', {})
        
        if not labels:
            print(f"Document {doc.get('_id')} has no labels to store in Qdrant")
            return False
        
        # Get base vector for the English text
        base_vector = self.get_text_embedding(english_text)
        if not base_vector:
            return False
        
        # Ensure vector is exactly 1536 dimensions
        base_vector = base_vector[:self.vector_dimension] if len(base_vector) > self.vector_dimension else base_vector + [0.0] * (self.vector_dimension - len(base_vector))
        
        points = []
        success = False
        
        # Create individual points for each label
        for label in labels:
            point_id = str(uuid.uuid5(
                uuid.NAMESPACE_OID, 
                f"{str(doc.get('_id'))}_{medicine_name}_{label}"
            ))
            
            # Get the reason for this label, if available
            reason = label_reasons.get(label, "")
            
            point = PointStruct(
                id=point_id,
                vector=base_vector,
                payload={
                    'mongo_id': str(doc.get('_id')),
                    'medicine_name': medicine_name,
                    'label': label,
                    'label_reason': reason,
                    # 'text': english_text,  # Store English text
                    # 'original_text': original_text  # Optionally keep original
                }
            )
            points.append(point)
        
        try:
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                print(f"Successfully inserted {len(points)} label points for document {doc.get('_id')} into Qdrant")
                success = True
            return success
        except Exception as e:
            print(f"Error inserting document {doc.get('_id')}: {str(e)}")
            return False

    def update_document(self, doc: Dict[str, Any]) -> bool:
        """Update document by deleting existing points and inserting new ones"""
        mongo_id = str(doc.get('_id'))
        
        # First delete existing points
        try:
            # Find all points for this document
            existing_points = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="mongo_id", match={"value": mongo_id})]
                ),
                limit=1000,
                with_payload=False,
                with_vectors=False
            )[0]
            
            if existing_points:
                point_ids = [point.id for point in existing_points]
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids,
                    wait=True
                )
                print(f"Deleted {len(point_ids)} existing points for document {mongo_id}")
        except Exception as e:
            print(f"Error deleting existing points for document {mongo_id}: {str(e)}")
            return False
        
        # Now insert the updated document
        return self.insert_document(doc)

    def delete_document(self, mongo_id: str) -> bool:
        """Delete all points for a document by its MongoDB ID"""
        try:
            # Find all points for this document
            existing_points = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="mongo_id", match={"value": mongo_id})]
                ),
                limit=1000,
                with_payload=False,
                with_vectors=False
            )[0]
            
            if existing_points:
                point_ids = [point.id for point in existing_points]
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids,
                    wait=True
                )
                print(f"Deleted {len(point_ids)} points for document {mongo_id}")
                return True
            return False
        except Exception as e:
            print(f"Error deleting document {mongo_id}: {str(e)}")
            return False

    def search_similar(self, text: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents based on text similarity"""
        vector = self.get_text_embedding(text)
        if not vector:
            return []
        
        # Ensure the vector has the correct dimension
        if len(vector) != self.vector_dimension:
            vector = vector[:self.vector_dimension] if len(vector) > self.vector_dimension else vector + [0.0] * (self.vector_dimension - len(vector))
        
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            return [{
                'id': hit.id,
                'score': hit.score,
                'payload': hit.payload
            } for hit in results]
        except Exception as e:
            print(f"Error searching similar documents: {str(e)}")
            return []

    def search_by_medicine_and_label(self, medicine_name: str, label: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for documents with specific medicine_name and optional label"""
        try:
            must_conditions = [
                FieldCondition(key="medicine_name", match={"value": medicine_name})
            ]
            
            if label:
                must_conditions.append(
                    FieldCondition(key="label", match={"value": label})
                )
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_filter=Filter(must=must_conditions),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            return [{
                'id': hit.id,
                'score': hit.score,
                'payload': hit.payload
            } for hit in results]
        except Exception as e:
            print(f"Error in search_by_medicine_and_label: {str(e)}")
            return []

# Initialize the service
qdrant_service = QdrantService()