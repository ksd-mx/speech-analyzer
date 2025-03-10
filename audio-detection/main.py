#!/usr/bin/env python3
"""
Audio Keyword Detection System

A simplified keyword detection system that actually works.
"""

import sys
import argparse
import traceback

# Import modules
from utils import suppress_warnings, check_directory, check_audio_file
from model import load_training_data, train_model, save_model, load_model
from detection import detect_keyword, print_detection_results

# Suppress warnings
suppress_warnings()

def main():
    """Main entry point for the command line interface."""
    parser = argparse.ArgumentParser(description="Audio Keyword Detection System")
    
    # Define argument groups
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--train', help="Train a model using data from specified directory")
    mode_group.add_argument('--detect', help="Detect keywords in the specified audio file")
    
    # Model arguments
    parser.add_argument('--model', required=True, help="Path to save/load model")
    
    # Detection arguments
    parser.add_argument('--keyword', help="Specific keyword to detect (optional)")
    parser.add_argument('--threshold', type=float, default=0.5, 
                       help="Confidence threshold for detection (0.0-1.0)")
    
    args = parser.parse_args()
    
    # Training mode
    if args.train:
        if not check_directory(args.train):
            return 1
            
        try:
            # Load training data
            X, y, label_mapping = load_training_data(args.train)
            
            if len(X) == 0:
                print("Error: No valid training data found")
                return 1
            
            # Train the model
            print(f"Training with {len(X)} samples across {len(label_mapping)} classes")
            model, scaler = train_model(X, y)
            
            # Save the model
            save_model(model, scaler, label_mapping, args.model)
            
        except Exception as e:
            print(f"Error during training: {str(e)}")
            traceback.print_exc()
            return 1
    
    # Detection mode
    elif args.detect:
        if not check_audio_file(args.detect):
            return 1
            
        if not check_audio_file(args.model):  # Reusing this function to check if file exists
            return 1
        
        try:
            # Load the model
            model, scaler, label_mapping = load_model(args.model)
            
            # Detect keywords
            result, confidence = detect_keyword(
                args.detect, model, scaler, label_mapping,
                keyword=args.keyword,
                threshold=args.threshold
            )
            
            # Print results
            print_detection_results(
                result, confidence, keyword=args.keyword, threshold=args.threshold
            )
            
        except Exception as e:
            print(f"Error during detection: {str(e)}")
            traceback.print_exc()
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())