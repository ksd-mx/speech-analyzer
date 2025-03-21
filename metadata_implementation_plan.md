# Metadata Implementation Plan for Speech Analyzer

## Overview

This document outlines a plan to implement metadata support in the Speech Analyzer system. The goal is to allow passing flexible metadata through the API and queue system, without requiring changes to the core detection algorithms.

## Current Architecture

The current system follows these main processing steps:

1. API endpoint (`/keywords/detect`) receives audio files and detection parameters
2. Detector is created and invoked to analyze the audio
3. Results are formatted and returned via API
4. Results are also published to a message queue

## Implementation Requirements

- Add support for flexible, schema-less metadata
- Pass metadata from API request to response
- Include metadata in queue messages
- Accept metadata as a JSON string through form fields
- No modifications needed to the detector implementations

## Implementation Details

### 1. API Schema Updates

**File: `api/schemas/models.py`**

Add metadata field to the request and response models:

```python
class KeywordDetectionRequest(KeywordDetectionBase):
    """Complete request model for keyword detection"""
    strategy: str = Field("whisper", description="Detection strategy: whisper or classifier")
    model: Optional[str] = Field(None, description="Model name for classifier strategy")
    topic: Optional[str] = Field("keyword_detections", description="Queue topic for results")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Custom metadata to track with the request")

class KeywordDetectionResponse(BaseModel):
    """Response model for keyword detection"""
    success: bool = Field(..., description="Whether the request was successful")
    job_id: str = Field(..., description="Unique job identifier")
    strategy: str = Field(..., description="Strategy used for detection")
    transcription: Optional[str] = Field(None, description="Full transcription (for whisper strategy)")
    detections: List[KeywordDetectionResult] = Field(..., description="Detection results for each keyword")
    duration_seconds: float = Field(..., description="Duration of the audio file")
    processing_time_seconds: float = Field(..., description="Time taken to process the request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Custom metadata passed with the request")
```

### 2. API Endpoint Updates

**File: `api/routers/detection.py`**

Update the `/keywords/detect` endpoint to handle metadata:

```python
@router.post("/keywords/detect", response_model=KeywordDetectionResponse)
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
```

### 3. Test Updates

**File: `tests/test_api.py`**

Add test cases for metadata handling:

```python
def test_detect_keywords_with_metadata(self):
    """Test the detect keywords endpoint with metadata."""
    # Mock detector
    mock_detector = MagicMock()
    mock_detector.detect_keywords.return_value = {
        "transcription": "Hello world test",
        "duration_seconds": 1.5,
        "detections": {
            "hello": {
                "detected": True,
                "occurrences": 1,
                "positions": [0],
                "confidence_scores": [0.95]
            }
        }
    }
    mock_create_detector.return_value = mock_detector
    
    # Create test file
    file_content = b"mock audio content"
    
    # Prepare form data with metadata
    form_data = {
        "strategy": "whisper",
        "keywords": "hello",
        "threshold": "0.5",
        "metadata": json.dumps({
            "timestamp": "2025-03-21T12:00:00Z",
            "framerate": 30,
            "source": "camera1"
        })
    }
    
    # Make request
    with patch('api.routers.detection.open', mock_open()):
        with patch('api.routers.detection.QueueManager.publish', return_value=True):
            response = self.client.post(
                "/keywords/detect",
                files={"file": ("test.wav", file_content)},
                data=form_data
            )
    
    # Assert response
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertTrue(data["success"])
    
    # Verify metadata was preserved
    self.assertIn("metadata", data)
    self.assertEqual(data["metadata"]["timestamp"], "2025-03-21T12:00:00Z")
    self.assertEqual(data["metadata"]["framerate"], 30)
    self.assertEqual(data["metadata"]["source"], "camera1")
```

## API Documentation

Update the API endpoint documentation to include metadata:

### POST /keywords/detect

**Form Parameters:**
- `file`: Audio file for detection (Required)
- `strategy`: Detection strategy to use (Default: "whisper")
- `keywords`: Comma-separated list of keywords to detect (Required)
- `threshold`: Confidence threshold for detection (Default: 0.5)
- `model`: Model name/path for classifier strategy (Optional)
- `topic`: Queue topic for publishing results (Default: "keyword_detections")
- `metadata`: JSON string containing custom metadata (Optional)

**Example Request:**
```
POST /keywords/detect
Content-Type: multipart/form-data

file=@audio.wav
strategy=whisper
keywords=hello,world
threshold=0.6
metadata={"timestamp":"2025-03-21T12:00:00Z","source":"camera1","framerate":30}
```

**Example Response:**
```json
{
  "success": true,
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "strategy": "whisper",
  "transcription": "Hello world test",
  "detections": [
    {
      "keyword": "hello",
      "detected": true,
      "occurrences": 1,
      "positions": [0],
      "confidence_scores": [0.95]
    },
    {
      "keyword": "world",
      "detected": true,
      "occurrences": 1,
      "positions": [6],
      "confidence_scores": [0.85]
    }
  ],
  "duration_seconds": 1.5,
  "processing_time_seconds": 0.25,
  "metadata": {
    "timestamp": "2025-03-21T12:00:00Z",
    "source": "camera1",
    "framerate": 30
  }
}
```

## Example Usage

### Python Client Example:

```python
import requests
import json

url = "http://localhost:8000/keywords/detect"
files = {"file": open("sample.wav", "rb")}
metadata = {
    "timestamp": "2025-03-21T12:00:00Z",
    "framerate": 30,
    "source": "camera1",
    "output_path": "/path/to/save/results"
}

data = {
    "strategy": "whisper",
    "keywords": "hello,world",
    "threshold": 0.6,
    "metadata": json.dumps(metadata)  # Convert to JSON string
}

response = requests.post(url, files=files, data=data)
result = response.json()

# Access metadata in response
print(f"Metadata: {result['metadata']}")
```

### cURL Example:

```bash
curl -X POST "http://localhost:8000/keywords/detect" \
  -F "file=@sample.wav" \
  -F "strategy=whisper" \
  -F "keywords=hello,world" \
  -F "threshold=0.6" \
  -F 'metadata={"timestamp":"2025-03-21T12:00:00Z","framerate":30,"source":"camera1"}'
```

## Implementation Considerations

1. **Validation**: The implementation accepts any JSON object as metadata without schema validation. If needed, add validation rules later.

2. **Size Limits**: Consider implementing size limits for metadata to prevent abuse.

3. **Performance Impact**: Since metadata is only passed around and not processed, there should be negligible performance impact.

4. **Backward Compatibility**: The implementation is backward compatible with existing clients that don't provide metadata.

5. **Security**: Ensure user-provided metadata is properly sanitized before storing or displaying, especially if it might contain user-supplied content.

6. **Documentation**: Update API documentation to include the new metadata parameter and its usage.

## Next Steps

1. Implement the changes in Code mode
2. Add unit tests to verify metadata is correctly passed through the system
3. Update API documentation
4. Test with real-world use cases