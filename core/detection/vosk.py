"""
VOSK-based keyword detection strategy.
Uses VOSK model for speech-to-text transcription and then
performs text search for keyword detection.
"""

import os
import json
import wave
import logging
from typing import List, Dict, Any, Optional
from vosk import Model, KaldiRecognizer

from .base import BaseDetector

# Configure logging
logger = logging.getLogger(__name__)

class VoskDetector(BaseDetector):
    """
    Detector that uses VOSK speech-to-text for keyword detection.
    Optimized for Arabic language support and offline operation.
    """
    
    def __init__(self, model_path: str = "models/vosk-model-ar-0.22", sample_rate: int = 16000):
        """
        Initialize the VOSK detector.
        
        Args:
            model_path: Path to VOSK model directory
            sample_rate: Audio sample rate (default 16000 for VOSK models)
        """
        super().__init__()
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the VOSK model from the specified path"""
        if self.model is not None:
            return
            
        try:
            logger.info(f"Loading VOSK model from: {self.model_path}")
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"VOSK model not found at: {self.model_path}")
                
            self.model = Model(self.model_path)
            logger.info("VOSK model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load VOSK model: {str(e)}")
            raise RuntimeError(f"VOSK model loading failed: {str(e)}")
    
    def _validate_audio_format(self, wf: wave.Wave_read) -> float:
        """
        Validate audio format and return duration in seconds.
        
        Args:
            wf: Wave file object
            
        Returns:
            float: Duration in seconds
            
        Raises:
            ValueError: If audio format is invalid
        """
        if wf.getnchannels() != 1:
            raise ValueError("Audio must be mono for VOSK processing")
        if wf.getsampwidth() != 2:
            raise ValueError("Audio must be 16-bit for VOSK processing")
        if wf.getcomptype() != "NONE":
            raise ValueError("Audio must be uncompressed for VOSK processing")
            
        return wf.getnframes() / wf.getframerate()
    
    def _transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using VOSK.
        
        Args:
            audio_path: Path to audio file (must be WAV format)
            
        Returns:
            Dict containing:
            - text: Transcription text
            - duration_seconds: Audio duration
            - words: List of word-level timings (if available)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            with wave.open(audio_path, "rb") as wf:
                duration = self._validate_audio_format(wf)
                rec = KaldiRecognizer(self.model, wf.getframerate())
                rec.SetWords(True)  # Enable word-level timing information
                
                result = {
                    "text": "",
                    "duration_seconds": duration,
                    "words": []
                }
                
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    if rec.AcceptWaveform(data):
                        part_result = json.loads(rec.Result())
                        if part_result.get("text", ""):
                            result["text"] += " " + part_result["text"]
                            if "result" in part_result:
                                result["words"].extend(part_result["result"])
                
                # Get final result
                part_result = json.loads(rec.FinalResult())
                if part_result.get("text", ""):
                    result["text"] += " " + part_result["text"]
                    if "result" in part_result:
                        result["words"].extend(part_result["result"])
                
                result["text"] = result["text"].strip()
                return result
                
        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}")
            raise RuntimeError(f"Audio processing error: {str(e)}")
    
    def detect_keywords(self, audio_path: str, keywords: List[str], threshold: float = 0.5) -> Dict[str, Any]:
        """
        Detect keywords in an audio file using VOSK transcription.
        
        Args:
            audio_path: Path to the audio file
            keywords: List of keywords to detect (case insensitive)
            threshold: Confidence threshold (unused for VOSK, kept for interface compatibility)
            
        Returns:
            Dict containing detection results with structure:
            {
                "transcription": str,
                "duration_seconds": float,
                "detections": {
                    "keyword1": {
                        "detected": bool,
                        "occurrences": int,
                        "positions": List[int],
                        "confidence_scores": List[float]
                    },
                    ...
                }
            }
        """
        if not keywords:
            raise ValueError("Keywords list cannot be empty")
            
        # Ensure model is loaded
        if self.model is None:
            self._load_model()
        
        logger.info(f"Processing audio with VOSK: {audio_path}")
        result = self._transcribe_audio(audio_path)
        text = result["text"]
        duration = result["duration_seconds"]
        
        logger.info(f"Detecting keywords in transcription: {keywords}")
        detections = self._detect_keywords_in_text(text, keywords)
        
        return self.format_result({
            "transcription": text,
            "duration_seconds": duration,
            "detections": detections
        })
    
    def _detect_keywords_in_text(self, text: str, keywords: List[str]) -> Dict[str, Any]:
        """
        Detect keywords in text and return detection results.
        
        Args:
            text: Text to search in
            keywords: Keywords to detect
            
        Returns:
            Dict of keyword detection results
        """
        text_lower = text.lower()
        results = {}
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            count = text_lower.count(keyword_lower)
            
            if count > 0:
                # Find all positions of the keyword
                positions = []
                start_idx = 0
                while True:
                    pos = text_lower.find(keyword_lower, start_idx)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start_idx = pos + len(keyword_lower)
                
                results[keyword] = {
                    "detected": True,
                    "occurrences": count,
                    "positions": positions,
                    "confidence_scores": [1.0] * count  # VOSK doesn't provide word confidence
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
            Dict containing:
            - name: Detector name
            - description: Detector description
            - models: Available model options
            - parameters: Supported parameters
        """
        return {
            "name": "vosk",
            "description": "VOSK speech-to-text detector (offline, supports Arabic)",
            "models": ["vosk-model-ar-0.22", "vosk-model-small-en-us-0.22"],
            "parameters": {
                "model_path": {
                    "description": "Path to VOSK model directory",
                    "required": True
                },
                "sample_rate": {
                    "description": "Audio sample rate (typically 16000 for VOSK)",
                    "default": 16000
                },
                "threshold": {
                    "description": "Confidence threshold (not used by VOSK)",
                    "default": 0.5
                }
            }
        }