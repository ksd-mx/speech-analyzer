import os
import time
import uuid
import torch
import whisper
import json
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import shutil

# Import our new queue manager
from queue_manager import QueueManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Voice Recognition API",
    description="Self-hosted API for speech recognition and keyword detection using Whisper",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/whisper_uploads")
CACHE_MODELS = os.environ.get("CACHE_MODELS", "true").lower() == "true"

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Model cache
model_cache = {}

# Initialize Queue Manager
queue_manager = QueueManager()

# Pydantic models for API
class TranscriptionResponse(BaseModel):
    success: bool
    text: str
    language: str
    duration_seconds: float
    processing_time_seconds: float
    job_id: str

class KeywordDetectionRequest(BaseModel):
    keywords: List[str]

class KeywordMatch(BaseModel):
    detected: bool
    occurrences: int
    positions: List[int] = []

class KeywordDetectionResponse(BaseModel):
    success: bool
    transcription: str
    detected_keywords: dict
    duration_seconds: float
    processing_time_seconds: float
    job_id: str

class HealthResponse(BaseModel):
    status: str
    model: str
    device: str
    timestamp: str
    queue_status: Optional[str] = None

# Helper functions
def get_model(model_name=WHISPER_MODEL):
    """Get whisper model, using cache if enabled"""
    if CACHE_MODELS and model_name in model_cache:
        logger.info(f"Using cached {model_name} model")
        return model_cache[model_name]
    
    logger.info(f"Loading {model_name} model...")
    start_time = time.time()
    
    # Use MPS if available (for Apple Silicon) with fallback to CPU
    device = torch.device("cpu")
    try:
        if torch.backends.mps.is_available():
            device = torch.device("mps")
            logger.info("Using MPS (Metal Performance Shaders) acceleration")
        else:
            logger.info("MPS not available, using CPU")
    except Exception as e:
        logger.warning(f"Error setting up MPS device: {str(e)}. Falling back to CPU.")
    
    try:
        model = whisper.load_model(model_name, device=device)
        
        load_time = time.time() - start_time
        logger.info(f"Model loaded in {load_time:.2f} seconds")
        
        if CACHE_MODELS:
            model_cache[model_name] = model
            
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        # If MPS failed, try again with CPU
        if device.type == "mps":
            logger.info("Retrying model load with CPU")
            device = torch.device("cpu")
            model = whisper.load_model(model_name, device=device)
            
            load_time = time.time() - start_time
            logger.info(f"Model loaded on CPU in {load_time:.2f} seconds")
            
            if CACHE_MODELS:
                model_cache[model_name] = model
                
            return model
        else:
            raise

def save_upload_file(upload_file: UploadFile) -> str:
    """Save an upload file to disk and return the path"""
    # Generate a unique filename
    file_extension = os.path.splitext(upload_file.filename)[1]
    temp_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, temp_filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    logger.info(f"Saved uploaded file to {file_path}")
    return file_path

def cleanup_file(file_path: str):
    """Remove a temporary file"""
    if os.path.exists(file_path) and UPLOAD_DIR in file_path:
        os.remove(file_path)
        logger.info(f"Cleaned up file {file_path}")

def detect_keywords_in_text(text: str, keywords: List[str]):
    """Detect keywords in transcribed text"""
    text_lower = text.lower()
    keywords_lower = [keyword.lower() for keyword in keywords]
    
    results = {}
    for keyword in keywords_lower:
        if keyword in text_lower:
            # Count occurrences
            count = text_lower.count(keyword)
            
            # Find positions (rough approximation)
            positions = []
            start_pos = 0
            for i in range(count):
                pos = text_lower.find(keyword, start_pos)
                if pos != -1:
                    positions.append(pos)
                    start_pos = pos + len(keyword)
            
            results[keyword] = {
                "detected": True,
                "occurrences": count,
                "positions": positions
            }
        else:
            results[keyword] = {
                "detected": False,
                "occurrences": 0,
                "positions": []
            }
    
    return results

def publish_to_queue(topic: str, data: Dict[str, Any]) -> bool:
    """Publish message to queue using the queue manager"""
    return queue_manager.publish(topic, data)

# API endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint that also tests model loading"""
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    
    response = {
        "status": "ok",
        "model": WHISPER_MODEL,
        "device": device,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Add queue status
    response["queue_status"] = queue_manager.status
    
    return response

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model: Optional[str] = Form(WHISPER_MODEL),
    topic: Optional[str] = Form("transcriptions")
):
    """Transcribe an audio file to text"""
    start_time = time.time()
    job_id = str(uuid.uuid4())
    
    try:
        # Save the uploaded file
        file_path = save_upload_file(file)
        background_tasks.add_task(cleanup_file, file_path)
        
        # Load the model
        whisper_model = get_model(model)
        
        # Transcribe the audio
        logger.info(f"Transcribing {file.filename}...")
        result = whisper_model.transcribe(file_path)
        
        processing_time = time.time() - start_time
        logger.info(f"Transcription completed in {processing_time:.2f} seconds")
        
        # Prepare response
        response = {
            "success": True,
            "text": result["text"],
            "language": result["language"],
            "duration_seconds": result.get("duration", 0),
            "processing_time_seconds": processing_time,
            "job_id": job_id
        }
        
        # Publish to queue
        queue_data = {
            **response,
            "filename": file.filename,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        publish_to_queue(topic, queue_data)
        
        return response
    
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        
        # Publish error to queue
        error_data = {
            "success": False,
            "error": str(e),
            "job_id": job_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        publish_to_queue(topic, error_data)
        
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/detect-keywords", response_model=KeywordDetectionResponse)
async def detect_keywords(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    keywords: str = Form(...),  # Comma-separated list of keywords
    model: Optional[str] = Form(WHISPER_MODEL),
    topic: Optional[str] = Form("keyword_detections")
):
    """Detect keywords in an audio file"""
    start_time = time.time()
    job_id = str(uuid.uuid4())
    
    try:
        # Parse keywords from comma-separated string
        keyword_list = [k.strip() for k in keywords.split(',')]
        if not keyword_list:
            raise HTTPException(status_code=400, detail="No keywords provided")
        
        # Save the uploaded file
        file_path = save_upload_file(file)
        background_tasks.add_task(cleanup_file, file_path)
        
        # Load the model
        whisper_model = get_model(model)
        
        # Transcribe the audio with better decode options for accuracy
        logger.info(f"Transcribing {file.filename} for keyword detection...")
        options = dict(beam_size=5, best_of=5)
        result = whisper_model.transcribe(file_path, **options)
        
        # Detect keywords in the transcription
        logger.info(f"Detecting keywords: {keyword_list}")
        keyword_results = detect_keywords_in_text(result["text"], keyword_list)
        
        processing_time = time.time() - start_time
        logger.info(f"Keyword detection completed in {processing_time:.2f} seconds")
        
        # Prepare response
        response = {
            "success": True,
            "transcription": result["text"],
            "detected_keywords": keyword_results,
            "duration_seconds": result.get("duration", 0),
            "processing_time_seconds": processing_time,
            "job_id": job_id
        }
        
        # Publish to queue
        queue_data = {
            **response,
            "filename": file.filename,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        publish_to_queue(topic, queue_data)
        
        return response
    
    except Exception as e:
        logger.error(f"Keyword detection error: {str(e)}")
        
        # Publish error to queue
        error_data = {
            "success": False,
            "error": str(e),
            "job_id": job_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        publish_to_queue(topic, error_data)
        
        raise HTTPException(status_code=500, detail=f"Keyword detection failed: {str(e)}")

# Application entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)