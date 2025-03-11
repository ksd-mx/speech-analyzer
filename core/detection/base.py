"""
Abstract base class for keyword detection strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseDetector(ABC):
    """
    Abstract base class that defines the interface for all keyword detection strategies.
    All concrete detector implementations must inherit from this class.
    """
    
    def __init__(self):
        """Initialize the detector"""
        self.name = self.__class__.__name__
    
    @abstractmethod
    def detect_keywords(self, audio_path: str, keywords: List[str], threshold: float) -> Dict[str, Any]:
        """
        Detect keywords in an audio file.
        
        Args:
            audio_path: Path to the audio file
            keywords: List of keywords to detect
            threshold: Confidence threshold (0.0-1.0)
            
        Returns:
            Dict containing detection results with standardized structure:
            {
                "transcription": Optional[str],  # Full transcription (for transcription-based strategies)
                "duration_seconds": float,       # Audio duration
                "detections": {                  # Results for each keyword
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
        pass
    
    @abstractmethod
    def get_supported_params(self) -> Dict[str, Any]:
        """
        Get information about parameters supported by this detector.
        
        Returns:
            Dict containing information about supported parameters
        """
        pass
    
    def format_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the result to ensure it conforms to the expected structure.
        
        Args:
            result: Raw detection result
            
        Returns:
            Dict containing formatted detection results
        """
        # Ensure all required keys exist
        if "detections" not in result:
            result["detections"] = {}
            
        if "duration_seconds" not in result:
            result["duration_seconds"] = 0.0
            
        # Format each keyword detection result
        for keyword, data in result.get("detections", {}).items():
            if "detected" not in data:
                data["detected"] = len(data.get("positions", [])) > 0
                
            if "occurrences" not in data:
                data["occurrences"] = len(data.get("positions", []))
                
            if "positions" not in data:
                data["positions"] = []
                
            if "confidence_scores" not in data:
                data["confidence_scores"] = []
        
        return result