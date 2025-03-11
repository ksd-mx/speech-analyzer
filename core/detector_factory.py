"""
Factory for creating detector instances based on the requested strategy.
"""

import os
import logging
from typing import Dict, Any, Optional

from core.detection.base import BaseDetector
from core.detection.whisper import WhisperDetector
from core.detection.classifier import ClassifierDetector

# Configure logging
logger = logging.getLogger(__name__)

class DetectorFactory:
    """
    Factory class for creating detector instances.
    """
    
    @staticmethod
    def create_detector(strategy: str, **kwargs) -> BaseDetector:
        """
        Create a detector instance based on the requested strategy.
        
        Args:
            strategy: The detection strategy to use ('whisper' or 'classifier')
            **kwargs: Additional parameters for the detector
            
        Returns:
            BaseDetector: An instance of the requested detector
            
        Raises:
            ValueError: If the requested strategy is not supported
        """
        strategy = strategy.lower()
        
        if strategy == "whisper":
            model_size = kwargs.get("model_size", "base")
            logger.info(f"Creating WhisperDetector with model_size={model_size}")
            return WhisperDetector(model_size=model_size)
            
        elif strategy == "classifier":
            model_path = kwargs.get("model_path")
            logger.info(f"Creating ClassifierDetector with model_path={model_path}")
            return ClassifierDetector(model_path=model_path)
            
        else:
            supported_strategies = ["whisper", "classifier"]
            raise ValueError(f"Unsupported detection strategy: {strategy}. "
                            f"Supported strategies: {', '.join(supported_strategies)}")
    
    @staticmethod
    def list_available_strategies() -> Dict[str, Any]:
        """
        List available detection strategies and their parameters.
        
        Returns:
            Dict containing information about available strategies
        """
        # This could be extended to dynamically discover available strategies
        strategies = {
            "whisper": {
                "description": "Uses Whisper speech-to-text for keyword detection",
                "models": ["tiny", "base", "small", "medium", "large"]
            },
            "classifier": {
                "description": "Uses a trained classifier for direct audio keyword detection",
                "models": []
            }
        }
        
        # Try to find available classifier models
        models_dir = os.path.join(os.getcwd(), "models")
        if os.path.exists(models_dir):
            model_files = [f for f in os.listdir(models_dir) if f.endswith(".pkl")]
            strategies["classifier"]["models"] = model_files
        
        return strategies