"""
Pydantic models for API request and response schemas
"""

from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field

# Request Models
class KeywordDetectionBase(BaseModel):
    """Base model for keyword detection requests"""
    keywords: List[str] = Field(..., description="List of keywords to detect")
    threshold: float = Field(0.5, description="Confidence threshold (0.0-1.0)")
    
class KeywordDetectionRequest(KeywordDetectionBase):
    """Complete request model for keyword detection"""
    strategy: str = Field("whisper", description="Detection strategy: whisper or classifier")
    model: Optional[str] = Field(None, description="Model name for classifier strategy")
    topic: Optional[str] = Field("keyword_detections", description="Queue topic for results")

# Response Models
class KeywordOccurrence(BaseModel):
    """Model for a single keyword occurrence"""
    position: int = Field(..., description="Position in audio/text")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    
class KeywordDetectionResult(BaseModel):
    """Model for detection results for a single keyword"""
    keyword: str = Field(..., description="The detected keyword")
    detected: bool = Field(..., description="Whether the keyword was detected")
    occurrences: int = Field(0, description="Number of occurrences")
    positions: List[int] = Field([], description="Positions in audio/text")
    confidence_scores: List[float] = Field([], description="Confidence scores for each occurrence")

class KeywordDetectionResponse(BaseModel):
    """Response model for keyword detection"""
    success: bool = Field(..., description="Whether the request was successful")
    job_id: str = Field(..., description="Unique job identifier")
    strategy: str = Field(..., description="Strategy used for detection")
    transcription: Optional[str] = Field(None, description="Full transcription (for whisper strategy)")
    detections: List[KeywordDetectionResult] = Field(..., description="Detection results for each keyword")
    duration_seconds: float = Field(..., description="Duration of the audio file")
    processing_time_seconds: float = Field(..., description="Time taken to process the request")

# Health Check Response
class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    api: str = Field(..., description="API name")