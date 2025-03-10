#!/usr/bin/env python3
"""
Detection script for audio keyword detection.
This is a convenience wrapper around main.py functionality.
"""

import sys
import argparse
from utils import check_audio_file
from model import load_model
from detection import detect_keyword, print_detection_results

def detect_from_file(audio_path, model_path, keyword=None, threshold=0.5):
    """
    Detect keywords in an audio file.
    
    Args:
        audio_path: Path to the audio file
        model_path: Path to the trained model
        keyword: Specific keyword to detect (optional)
        threshold: Confidence threshold
        
    Returns:
        int: 0 for success, 1 for failure
    """
    try:
        # Load the model
        model, scaler, label_mapping = load_model(model_path)
        
        # Get available keywords
        available_keywords = list(label_mapping.values())
        print(f"Model loaded with {len(available_keywords)} keywords: {', '.join(available_keywords)}")
        
        # Detect keywords
        result, confidence = detect_keyword(
            audio_path, model, scaler, label_mapping,
            keyword=keyword,
            threshold=threshold
        )
        
        # Print results
        print_detection_results(
            result, confidence, keyword=keyword, threshold=threshold
        )
        
        return 0
        
    except Exception as e:
        print(f"Error during detection: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

def main():
    """Simple CLI for detection."""
    parser = argparse.ArgumentParser(description="Detect keywords in audio files")
    parser.add_argument('audio_file', help="Audio file to analyze")
    parser.add_argument('--model', default="keyword_model.pkl", 
                        help="Path to model file (default: keyword_model.pkl)")
    parser.add_argument('--keyword', help="Specific keyword to detect (optional)")
    parser.add_argument('--threshold', type=float, default=0.5, 
                       help="Confidence threshold (0.0-1.0, default: 0.5)")
    
    args = parser.parse_args()
    
    # Check if audio file exists
    if not check_audio_file(args.audio_file):
        return 1
        
    # Check if model file exists
    if not check_audio_file(args.model):  # Reusing this function to check if file exists
        return 1
    
    return detect_from_file(args.audio_file, args.model, 
                           keyword=args.keyword, threshold=args.threshold)

if __name__ == "__main__":
    sys.exit(main())