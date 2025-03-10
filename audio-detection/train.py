#!/usr/bin/env python3
"""
Training script for audio keyword detection.
This is a convenience wrapper around main.py functionality.
"""

import sys
import argparse
from utils import check_directory
from model import load_training_data, train_model, save_model

def train_model_from_directory(training_dir, model_path):
    """
    Train a model from a directory of samples.
    
    Args:
        training_dir: Directory containing keyword subdirectories
        model_path: Path to save the trained model
        
    Returns:
        int: 0 for success, 1 for failure
    """
    try:
        print(f"Training model from {training_dir}")
        print(f"Model will be saved to {model_path}")
        
        # Load training data
        X, y, label_mapping = load_training_data(training_dir)
        
        if len(X) == 0:
            print("Error: No valid training data found")
            return 1
        
        # Train the model
        print(f"Training with {len(X)} samples across {len(label_mapping)} classes")
        model, scaler = train_model(X, y)
        
        # Save the model
        save_model(model, scaler, label_mapping, model_path)
        
        print("Training completed successfully!")
        return 0
        
    except Exception as e:
        print(f"Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

def main():
    """Simple CLI for training."""
    parser = argparse.ArgumentParser(description="Train an audio keyword detection model")
    parser.add_argument('training_dir', help="Directory containing keyword subdirectories")
    parser.add_argument('--model', default="keyword_model.pkl", 
                        help="Path to save model (default: keyword_model.pkl)")
    
    args = parser.parse_args()
    
    # Check if training directory exists
    if not check_directory(args.training_dir):
        return 1
    
    return train_model_from_directory(args.training_dir, args.model)

if __name__ == "__main__":
    sys.exit(main())