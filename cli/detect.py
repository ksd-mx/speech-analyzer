#!/usr/bin/env python3
"""
Detection script for audio keyword detection.
Provides a standalone interface for keyword detection without requiring the API.
"""

import os
import sys
import time
import argparse
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the detector factory
from core.detector_factory import DetectorFactory
from core.utils import check_audio_file

def detect_keywords_standalone(
    audio_path: str, 
    keywords: List[str], 
    strategy: str = "whisper",
    model_path: Optional[str] = None,
    threshold: float = 0.5
) -> bool:
    """
    Detect keywords in an audio file using the specified strategy.
    
    Args:
        audio_path: Path to the audio file
        keywords: List of keywords to detect
        strategy: Detection strategy ('whisper' or 'classifier')
        model_path: Path to the model file (for classifier strategy)
        threshold: Confidence threshold (0.0-1.0)
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Check if audio file exists
    if not check_audio_file(audio_path):
        return False
    
    try:
        start_time = time.time()
        
        # Create detector based on strategy
        detector = DetectorFactory.create_detector(
            strategy=strategy,
            model_path=model_path,
            model_size="small"
        )
        
        # Display info about detection
        logger.info(f"Detecting keywords {keywords} in {audio_path}")
        logger.info(f"Strategy: {strategy}")
        logger.info(f"Threshold: {threshold}")
        if model_path:
            logger.info(f"Model: {model_path}")
        
        # Detect keywords
        result = detector.detect_keywords(
            audio_path=audio_path,
            keywords=keywords,
            threshold=threshold
        )
        
        processing_time = time.time() - start_time
        
        # Display results
        print("\nKeyword Detection Results:")
        print(f"Duration: {result['duration_seconds']:.2f} seconds")
        print(f"Processing Time: {processing_time:.2f} seconds")
        
        print("\nDetected Keywords:")
        for keyword, data in result['detections'].items():
            if data['detected']:
                print(f"  ✓ '{keyword}' - {data['occurrences']} occurrences")
                
                # Print details for each occurrence
                for i in range(data['occurrences']):
                    if i < len(data['positions']) and i < len(data['confidence_scores']):
                        pos = data['positions'][i]
                        conf = data['confidence_scores'][i]
                        print(f"    - Position: {pos}, Confidence: {conf:.1%}")
            else:
                print(f"  ✗ '{keyword}' - not found")
        
        # Print transcription for Whisper strategy
        if result.get('transcription'):
            print("\nFull Transcription:")
            print(result['transcription'])
        
        return True
    
    except Exception as e:
        logger.error(f"Error during detection: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Detect keywords in audio files")
    parser.add_argument('audio_file', help="Audio file to analyze")
    parser.add_argument('--keywords', required=True, help="Comma-separated list of keywords to detect")
    parser.add_argument('--strategy', default="whisper", choices=["whisper", "vosk", "classifier"],
                      help="Detection strategy (whisper, vosk, or classifier)")
    parser.add_argument('--model', help="Path to model file (for classifier strategy)")
    parser.add_argument('--threshold', type=float, default=0.5, 
                       help="Confidence threshold (0.0-1.0, default: 0.5)")
    
    args = parser.parse_args()
    
    # Parse keywords
    keywords = [k.strip() for k in args.keywords.split(',')]
    
    # Run detection
    success = detect_keywords_standalone(
        args.audio_file,
        keywords,
        args.strategy,
        args.model,
        args.threshold
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())