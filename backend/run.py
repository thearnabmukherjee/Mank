import uvicorn
from multiprocessing import Process
from backend import app as backend_app
from visuals import app as visuals_app

def run_backend():
    uvicorn.run(backend_app, host="0.0.0.0", port=8000)

def run_visuals():
    uvicorn.run(visuals_app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    # Initialize Qdrant service
    # from qdrant_service import qdrant_service
    # qdrant_service.initialize_collection()
    
    # Create processes for each service
    backend_process = Process(target=run_backend)
    visuals_process = Process(target=run_visuals)
    
    # Start processes
    backend_process.start()
    visuals_process.start()
    
    # Wait for processes to complete
    backend_process.join()
    visuals_process.join()