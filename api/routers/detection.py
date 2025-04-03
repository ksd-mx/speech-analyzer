"""
Router for keyword detection endpoints
"""

import os
import time
import uuid
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from ..schemas.models import (
    KeywordDetectionRequest, 
    KeywordDetectionResponse, 
    KeywordDetectionResult
)

# Import detector factory
from core.detector_factory import DetectorFactory

# Import queue manager
from queueing.queue_manager import QueueManager

# Import settings
from config.settings import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(
    prefix="/keywords",
    tags=["keyword detection"],
    responses={404: {"description": "Not found"}},
)

# Initialize Queue Manager
queue_manager = QueueManager()

# Helper function to get a queue manager
def get_queue_manager():
    return queue_manager

@router.post("/detect", response_model=KeywordDetectionResponse)
async def detect_keywords(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    strategy: str = Form("whisper"),
    keywords: str = Form(...),  # Comma-separated list of keywords
    threshold: float = Form(0.5),
    model: Optional[str] = Form(None),
    topic: Optional[str] = Form("keyword_detections"),
    metadata: Optional[str] = Form(None),  # JSON string of metadata
    queue_manager: QueueManager = Depends(get_queue_manager)
):
    """
    Detect keywords in an audio file using the specified strategy
    """
    start_time = time.time()
    job_id = str(uuid.uuid4())
    
    # Parse metadata from JSON string if provided
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
            logger.info(f"Received metadata: {metadata_dict}")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata format. Must be valid JSON.")
    
    try:
        # Parse keywords from comma-separated string
        keyword_list = [k.strip() for k in keywords.split(',')]
        if not keyword_list:
            raise HTTPException(status_code=400, detail="No keywords provided")
        
        # Create temporary file path for the uploaded file
        upload_dir = os.environ.get("UPLOAD_DIR", "/tmp/audio_uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        file_extension = os.path.splitext(file.filename)[1]
        temp_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, temp_filename)
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Clean up file after processing
        background_tasks.add_task(lambda: os.remove(file_path) if os.path.exists(file_path) else None)
        
        # Create detector based on strategy
        if strategy == "whisper":
            # Use model_size from settings for Whisper
            detector = DetectorFactory.create_detector(
                strategy=strategy,
                model_size=settings.WHISPER_MODEL  # Use from settings instead of hardcoding
            )
        elif strategy == "vosk":
            # Use model_path from settings or provided model for VOSK
            detector = DetectorFactory.create_detector(
                strategy=strategy,
                model_path=model or settings.VOSK_MODEL_PATH,
                sample_rate=settings.VOSK_SAMPLE_RATE  # Also pass sample_rate
            )
        else:  # classifier
            detector = DetectorFactory.create_detector(
                strategy=strategy,
                model_path=model
            )
        
        # Detect keywords
        logger.info(f"Detecting keywords {keyword_list} using {strategy} strategy")
        result = detector.detect_keywords(
            audio_path=file_path,
            keywords=keyword_list,
            threshold=threshold
        )
        
        # Get audio duration
        duration_seconds = result.get("duration_seconds", 0)
        
        # Format results for API response
        detections = []
        for keyword, data in result.get("detections", {}).items():
            detection = KeywordDetectionResult(
                keyword=keyword,
                detected=data.get("detected", False),
                occurrences=data.get("occurrences", 0),
                positions=data.get("positions", []),
                confidence_scores=data.get("confidence_scores", [])
            )
            detections.append(detection)
        
        processing_time = time.time() - start_time
        
        # Prepare response
        response = {
            "success": True,
            "job_id": job_id,
            "strategy": strategy,
            "transcription": result.get("transcription"),
            "detections": detections,
            "duration_seconds": duration_seconds,
            "processing_time_seconds": processing_time,
            "metadata": metadata_dict  # Add metadata to response
        }

        # Convert to JSON-serializable format
        serializable_response = jsonable_encoder(response)
        
        # Publish to queue
        queue_data = {
            **serializable_response,
            "filename": file.filename,
            "timestamp": time.time()
            # Metadata is already included from serializable_response
        }
        queue_manager.publish(topic, queue_data)
        
        return serializable_response
        
    except Exception as e:
        logger.error(f"Keyword detection error: {str(e)}")
        
        # Publish error to queue
        error_data = {
            "success": False,
            "error": str(e),
            "job_id": job_id,
            "metadata": metadata_dict,  # Include metadata in error response
            "timestamp": time.time()
        }
        queue_manager.publish(topic, error_data)
        
        raise HTTPException(status_code=500, detail=f"Keyword detection failed: {str(e)}")

@router.get("/strategies")
async def list_strategies():
    """
    List available detection strategies
    """
    strategies = {
        "whisper": {
            "description": "Uses Whisper speech-to-text for keyword detection",
            "models": ["tiny", "base", "small", "medium", "large"]
        },
        "vosk": {
            "description": "Uses VOSK speech-to-text for keyword detection (offline, supports Arabic)",
            "models": ["vosk-model-ar-0.22", "vosk-model-small-en-us-0.22"]
        },
        "classifier": {
            "description": "Uses a trained classifier for direct audio keyword detection",
            "models": [f for f in os.listdir("models") if f.endswith(".pkl")] if os.path.exists("models") else []
        }
    }
    
    return strategies