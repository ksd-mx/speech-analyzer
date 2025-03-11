"""
Whisper-based keyword detection strategy.
Uses OpenAI's Whisper model for speech-to-text transcription and then
performs text search for keyword detection.
"""

import os
import time
import torch
import whisper
import logging
from typing import List, Dict, Any, Optional

from .base import BaseDetector

# Configure logging
logger = logging.getLogger(__name__)

class WhisperDetector(BaseDetector):
    """
    Detector that uses Whisper speech-to-text for keyword detection.
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize the Whisper detector.
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        """
        super().__init__()
        self.model_size = model_size
        self.model = None
        self.device = self._get_device()
        self._load_model()
    
    def _get_device(self) -> torch.device:
        """
        Determine the appropriate device for model inference.
        
        Returns:
            torch.device: Device to use for model inference
        """
        device = torch.device("cpu")
        try:
            if torch.cuda.is_available():
                device = torch.device("cuda")
                logger.info("Using CUDA for Whisper")
            elif torch.backends.mps.is_available():
                device = torch.device("mps")
                logger.info("Using MPS (Metal Performance Shaders) acceleration")
            else:
                logger.info("Using CPU for Whisper")
        except Exception as e:
            logger.warning(f"Error setting up device: {str(e)}. Falling back to CPU.")
        
        return device
    
    def _load_model(self):
        """Load the Whisper model"""
        if self.model is not None:
            return
            
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            start_time = time.time()
            
            self.model = whisper.load_model(self.model_size, device=self.device)
            
            load_time = time.time() - start_time
            logger.info(f"Model loaded in {load_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            # If device failed, try again with CPU
            if self.device.type != "cpu":
                logger.info("Retrying model load with CPU")
                self.device = torch.device("cpu")
                self.model = whisper.load_model(self.model_size, device=self.device)
                
                load_time = time.time() - start_time
                logger.info(f"Model loaded on CPU in {load_time:.2f} seconds")
    
    def detect_keywords(self, audio_path: str, keywords: List[str], threshold: float = 0.5) -> Dict[str, Any]:
        """
        Detect keywords in an audio file using Whisper transcription.
        
        Args:
            audio_path: Path to the audio file
            keywords: List of keywords to detect
            threshold: Confidence threshold (unused for Whisper, but required by interface)
            
        Returns:
            Dict containing detection results
        """
        start_time = time.time()
        
        # Ensure model is loaded
        if self.model is None:
            self._load_model()
        
        # Transcribe the audio
        logger.info(f"Transcribing audio: {audio_path}")
        options = dict(beam_size=5, best_of=5)
        result = self.model.transcribe(audio_path, **options)
        
        # Get transcription and audio duration
        transcription = result["text"]
        duration_seconds = result.get("duration", 0)
        
        # Detect keywords in the transcription
        logger.info(f"Detecting keywords: {keywords}")
        detections = self._detect_keywords_in_text(transcription, keywords)
        
        processing_time = time.time() - start_time
        logger.info(f"Detection completed in {processing_time:.2f} seconds")
        
        # Format and return results
        detection_result = {
            "transcription": transcription,
            "duration_seconds": duration_seconds,
            "detections": detections
        }
        
        return self.format_result(detection_result)
    
    def _detect_keywords_in_text(self, text: str, keywords: List[str]) -> Dict[str, Any]:
        """
        Detect keywords in transcribed text.
        
        Args:
            text: The transcribed text
            keywords: List of keywords to detect
            
        Returns:
            Dict mapping keywords to detection results
        """
        text_lower = text.lower()
        results = {}
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Check if keyword exists in text
            if keyword_lower in text_lower:
                # Count occurrences
                count = text_lower.count(keyword_lower)
                
                # Find positions
                positions = []
                confidence_scores = []
                start_pos = 0
                
                for _ in range(count):
                    pos = text_lower.find(keyword_lower, start_pos)
                    if pos != -1:
                        positions.append(pos)
                        confidence_scores.append(1.0)  # Whisper doesn't provide word-level confidence
                        start_pos = pos + len(keyword_lower)
                
                results[keyword] = {
                    "detected": True,
                    "occurrences": count,
                    "positions": positions,
                    "confidence_scores": confidence_scores
                }
            else:
                results[keyword] = {
                    "detected": False,
                    "occurrences": 0,
                    "positions": [],
                    "confidence_scores": []
                }
        
        return results
    
    def get_supported_params(self) -> Dict[str, Any]:
        """
        Get information about parameters supported by this detector.
        
        Returns:
            Dict containing information about supported parameters
        """
        return {
            "name": "whisper",
            "description": "Uses Whisper speech-to-text for keyword detection",
            "models": ["tiny", "base", "small", "medium", "large"],
            "parameters": {
                "threshold": {
                    "description": "Unused for Whisper strategy",
                    "default": 0.5
                }
            }
        }