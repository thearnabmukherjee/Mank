from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI
from dotenv import load_dotenv
import os
import numpy as np
from sklearn.decomposition import PCA
from sklearn.random_projection import GaussianRandomProjection
import joblib
import pathlib
import time
import logging
from typing import List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Read config from environment
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "Pharma")
ORIGINAL_DIM = 1536  # Dimension for text-embedding-3-small
TARGET_DIM = 128    # Target dimension for Qdrant collection
SAMPLE_SIZE = 30    # Number of embeddings to generate for training

# File paths
MODEL_DIR = pathlib.Path("models")
MODEL_DIR.mkdir(exist_ok=True)
PCA_MODEL_PATH = MODEL_DIR / "pca_reducer.joblib"

# Initialize clients
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

openai = OpenAI(api_key=OPENAI_API_KEY)

# PCA model for dimensionality reduction
pca_model = None

app = FastAPI()

# Request schema
class ChatRequest(BaseModel):
    query: str

# Optional train PCA schema
class TrainPCARequest(BaseModel):
    sample_texts: Optional[List[str]] = None
    force_retrain: bool = False

def verify_collection_dimensions():
    """Verify the collection exists and get its dimensions"""
    try:
        collections = client.get_collections()
        collection_names = [collection.name for collection in collections.collections]
        
        if COLLECTION_NAME not in collection_names:
            raise ValueError(f"Collection {COLLECTION_NAME} doesn't exist")
        
        collection_info = client.get_collection(COLLECTION_NAME)
        actual_dim = collection_info.config.params.vectors.size
        return actual_dim
    except Exception as e:
        logger.error(f"Error verifying collection: {str(e)}")
        raise

def embed_text(text: str) -> list[float]:
    """Get OpenAI embeddings for text"""
    try:
        response = openai.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        raise

def generate_sample_texts(n_samples=SAMPLE_SIZE):
    """Generate sample texts for PCA training"""
    # Sample texts to represent your domain - adjust based on your use case
    base_texts = [
        "What are the side effects of aspirin?",
        "Can I take ibuprofen with alcohol?",
        "What is the dosage for Codistaz?",
        "Is paracetamol safe during pregnancy?",
        "How does antibiotic resistance develop?",
        "What are the symptoms of diabetes?",
        "When should I take my blood pressure medication?",
        "How do I store insulin properly?",
        "What are the best treatments for migraine?",
        "Can I take multiple pain medications together?"
    ]
    
    # Generate more variations
    all_texts = []
    for text in base_texts:
        all_texts.append(text)
        all_texts.append(f"Tell me about {text.lower()}")
        all_texts.append(f"I need information on {text.lower()}")
    
    # Ensure we have enough unique texts
    while len(all_texts) < n_samples:
        all_texts.append(f"Query {len(all_texts)}: {np.random.choice(base_texts)}")
    
    # Take only what we need
    return all_texts[:n_samples]

def train_pca_model(custom_texts=None):
    """Create a dimensionality reduction model"""
    global pca_model
    
    logger.info("Starting dimensionality reduction model creation")
    
    # Method 1: Direct matrix projection (always works regardless of sample size)
    from sklearn.random_projection import GaussianRandomProjection
    
    logger.info(f"Creating random projection from {ORIGINAL_DIM} to {TARGET_DIM} dimensions")
    projection = GaussianRandomProjection(n_components=TARGET_DIM, random_state=42)
    
    # We need at least one sample to initialize the projection
    dummy_vector = np.random.rand(1, ORIGINAL_DIM)
    projection.fit(dummy_vector)
    
    # Save the model
    logger.info(f"Saving projection model to {PCA_MODEL_PATH}")
    joblib.dump(projection, PCA_MODEL_PATH)
    
    # Set the global model
    pca_model = projection
    
    logger.info("Dimensionality reduction model creation complete")
    return 0  # No explained variance for random projection

def load_or_create_pca_model():
    """Load existing PCA model or create a new one"""
    global pca_model
    if PCA_MODEL_PATH.exists():
        logger.info(f"Loading existing PCA model from {PCA_MODEL_PATH}")
        pca_model = joblib.load(PCA_MODEL_PATH)
    else:
        logger.info("No existing PCA model found, training new model")
        train_pca_model()

def reduce_dimensions(vector):
    """Reduce dimensions of the vector using PCA"""
    global pca_model
    
    # Ensure we have a model
    if pca_model is None:
        load_or_create_pca_model()
    
    # Convert to numpy array if it's not already
    vector_np = np.array(vector).reshape(1, -1)
    
    # Transform the vector
    reduced_vector = pca_model.transform(vector_np)[0].tolist()
    return reduced_vector

def extract_payload_filters(query: str) -> dict:
    """Simple pattern-based filter extraction"""
    filters = []
    if "codistaz" in query.lower():
        filters.append({"key": "medicine_name", "match": {"value": "Codistaz"}})
    # Add more rules as needed
    return {"must": filters} if filters else None

@app.on_event("startup")
async def startup_event():
    # Verify collection dimensions
    try:
        actual_dim = verify_collection_dimensions()
        if actual_dim != TARGET_DIM:
            logger.warning(
                f"Collection {COLLECTION_NAME} has dimension {actual_dim}, "
                f"but we expected {TARGET_DIM}. Will use dimensionality reduction."
            )
    except Exception as e:
        logger.error(f"Error on startup: {str(e)}")
        # Continue anyway, let the API calls handle errors
    
    # Load PCA model
    try:
        load_or_create_pca_model()
    except Exception as e:
        logger.error(f"Error loading PCA model: {str(e)}")
        logger.info("Will attempt to initialize model on first request")

@app.post("/chat")
async def chat_query(request: ChatRequest):
    query = request.query
    
    try:
        # Get embedding from OpenAI
        embedded_vector = embed_text(query)
        
        # Reduce dimensions
        reduced_vector = reduce_dimensions(embedded_vector)
        
        # Extract filters
        filters = extract_payload_filters(query)
        
        # Search with reduced dimensions
        search_result = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=reduced_vector,
            limit=5,
            with_payload=True,
            query_filter=models.Filter(**filters) if filters else None
        )
        
        results = []
        for hit in search_result:
            payload = hit.payload
            results.append({
                "medicine_name": payload.get("medicine_name"),
                "label": payload.get("label"),
                "label_reason": payload.get("label_reason"),
                "score": hit.score
            })
        
        return {"matches": results}
    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.post("/train-projection")
async def train_projection_endpoint(request: TrainPCARequest, background_tasks: BackgroundTasks):
    """Endpoint to train or retrain the dimensionality reduction model"""
    global pca_model
    
    # Check if model exists and we're not forcing a retrain
    if PCA_MODEL_PATH.exists() and not request.force_retrain:
        return {
            "status": "existing",
            "message": "Projection model already exists. Use force_retrain=true to recreate."
        }
    
    # Train in background to avoid blocking the API
    background_tasks.add_task(train_pca_model)
    
    return {
        "status": "creating",
        "message": "Dimensionality reduction model creation started in background"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Qdrant connection
        collections = client.get_collections()
        
        # Check if PCA model is loaded
        pca_status = "loaded" if pca_model is not None else "not_loaded"
        
        return {
            "status": "healthy",
            "qdrant_status": "connected",
            "pca_model": pca_status,
            "collection_exists": COLLECTION_NAME in [c.name for c in collections.collections]
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)