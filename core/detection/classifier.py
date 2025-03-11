"""
Classifier-based keyword detection strategy.
Uses a trained machine learning model to directly detect keywords in audio.
"""

import os
import time
import logging
import numpy as np
import librosa
import joblib
from typing import List, Dict, Any, Optional, Tuple

from .base import BaseDetector
from core.feature_extraction import extract_features

# Configure logging
logger = logging.getLogger(__name__)

class ClassifierDetector(BaseDetector):
    """
    Detector that uses a trained classifier for keyword detection.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize the classifier detector.
        
        Args:
            model_path: Path to the trained model file (.pkl)
        """
        super().__init__()
        self.model_path = model_path or self._find_default_model()
        self.model = None
        self.scaler = None
        self.label_mapping = None
        self._load_model()
    
    def _find_default_model(self) -> str:
        """
        Find a default model in the models directory.
        
        Returns:
            str: Path to the default model
        """
        models_dir = os.path.join(os.getcwd(), "models")
        if not os.path.exists(models_dir):
            raise ValueError("No models directory found")
            
        model_files = [f for f in os.listdir(models_dir) if f.endswith(".pkl")]
        if not model_files:
            raise ValueError("No model files found in models directory")
            
        # Return the first model file found
        return os.path.join(models_dir, model_files[0])
    
    def _load_model(self):
        """Load the trained model"""
        if not os.path.exists(self.model_path):
            raise ValueError(f"Model file not found: {self.model_path}")
        
        try:
            logger.info(f"Loading model from {self.model_path}")
            start_time = time.time()
            
            model_package = joblib.load(self.model_path)
            
            self.model = model_package['model']
            self.scaler = model_package['scaler']
            self.label_mapping = model_package['label_mapping']
            
            # Create a reverse mapping from keyword to index
            self.rev_mapping = {v: k for k, v in self.label_mapping.items()}
            
            load_time = time.time() - start_time
            logger.info(f"Model loaded in {load_time:.2f} seconds")
            logger.info(f"Available keywords: {', '.join(self.label_mapping.values())}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise
    
    def detect_keywords(self, audio_path: str, keywords: List[str], threshold: float = 0.5) -> Dict[str, Any]:
        """
        Detect keywords in an audio file using a trained classifier.
        
        Args:
            audio_path: Path to the audio file
            keywords: List of keywords to detect
            threshold: Confidence threshold (0.0-1.0)
            
        Returns:
            Dict containing detection results
        """
        start_time = time.time()
        
        # Ensure model is loaded
        if self.model is None:
            self._load_model()
        
        # Load audio file
        try:
            y, sr = librosa.load(audio_path, sr=None)
            duration = len(y) / sr
            logger.info(f"Loaded audio: {audio_path} (duration: {duration:.2f}s)")
        except Exception as e:
            logger.error(f"Error loading audio file: {str(e)}")
            raise
        
        # Extract features
        features = extract_features(y, sr)
        
        # Scale features
        features_scaled = self.scaler.transform([features])
        
        # Get prediction probabilities
        probabilities = self.model.predict_proba(features_scaled)[0]
        
        # Process results for each requested keyword
        detections = {}
        
        # Verify each keyword in the request
        for keyword in keywords:
            if keyword in self.rev_mapping:
                # Get the index for this keyword
                keyword_idx = self.rev_mapping[keyword]
                # Get the confidence score
                confidence = probabilities[keyword_idx]
                
                if confidence >= threshold:
                    # Keyword detected
                    detections[keyword] = {
                        "detected": True,
                        "occurrences": 1,  # Classifier detects presence, not count
                        "positions": [0],  # Position is not applicable for audio classifier
                        "confidence_scores": [float(confidence)]
                    }
                else:
                    # Keyword not detected with sufficient confidence
                    detections[keyword] = {
                        "detected": False,
                        "occurrences": 0,
                        "positions": [],
                        "confidence_scores": [float(confidence)]  # Still include confidence
                    }
            else:
                # Keyword not in model vocabulary
                logger.warning(f"Keyword '{keyword}' not found in model vocabulary")
                detections[keyword] = {
                    "detected": False,
                    "occurrences": 0,
                    "positions": [],
                    "confidence_scores": [],
                    "error": "Keyword not in model vocabulary"
                }
        
        processing_time = time.time() - start_time
        logger.info(f"Detection completed in {processing_time:.2f} seconds")
        
        # Format and return results
        detection_result = {
            "transcription": None,  # No transcription for classifier-based detection
            "duration_seconds": duration,
            "detections": detections
        }
        
        return self.format_result(detection_result)
    
    def get_supported_params(self) -> Dict[str, Any]:
        """
        Get information about parameters supported by this detector.
        
        Returns:
            Dict containing information about supported parameters
        """
        # Get available keywords from the model
        available_keywords = list(self.label_mapping.values()) if self.label_mapping else []
        
        return {
            "name": "classifier",
            "description": "Uses a trained classifier for direct audio keyword detection",
            "models": [os.path.basename(self.model_path)] if self.model_path else [],
            "available_keywords": available_keywords,
            "parameters": {
                "threshold": {
                    "description": "Confidence threshold for detection",
                    "default": 0.5,
                    "range": [0.0, 1.0]
                }
            }
        }