#!/usr/bin/env python3
"""
Training script for audio keyword detection.
Builds a classifier model from a directory of audio samples.
"""

import os
import sys
import time
import argparse
import logging
import numpy as np
import librosa
import joblib
from typing import List, Dict, Any, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import feature extraction
from core.feature_extraction import extract_features
from core.utils import check_directory

def load_training_data(training_dir: str) -> Tuple[np.ndarray, np.ndarray, Dict[int, str]]:
    """
    Load training data from the directory structure.
    
    Args:
        training_dir: Directory containing subdirectories for each keyword
        
    Returns:
        tuple: (X, y, label_mapping) where X is features, y is labels,
               and label_mapping maps indices to keyword names
    """
    X = []  # Feature vectors
    y = []  # Labels
    label_mapping = {}  # Mapping from label index to keyword name
    
    # Get list of keyword directories
    keywords = [d for d in os.listdir(training_dir) 
               if os.path.isdir(os.path.join(training_dir, d))]
    
    if not keywords:
        raise ValueError(f"No keyword directories found in {training_dir}")
    
    logger.info(f"Found {len(keywords)} keyword classes: {', '.join(keywords)}")
    
    # Assign label indices
    for i, keyword in enumerate(keywords):
        label_mapping[i] = keyword
    
    # Process each keyword directory
    for i, keyword in enumerate(keywords):
        keyword_dir = os.path.join(training_dir, keyword)
        logger.info(f"Loading {keyword} samples from {keyword_dir}...")
        
        # Audio file extensions to look for
        audio_extensions = ['.wav', '.mp3', '.ogg', '.flac']
        
        # Counter for loaded samples
        count = 0
        
        # Walk through the directory
        for root, _, files in os.walk(keyword_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in audio_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        # Load the audio file
                        logger.info(f"  Processing: {file}")
                        y_audio, sr = librosa.load(file_path, sr=None, duration=2.0)
                        
                        # Extract features
                        features = extract_features(y_audio, sr)
                        
                        # Add to our datasets
                        X.append(features)
                        y.append(i)
                        
                        # Increment counter
                        count += 1
                    except Exception as e:
                        logger.error(f"  Error processing {file}: {str(e)}")
        
        logger.info(f"  Loaded {count} samples for '{keyword}'")
    
    # Convert to numpy arrays before returning
    X_np = np.array(X)
    y_np = np.array(y)
    
    # Debug output
    logger.info(f"X shape: {X_np.shape}")
    logger.info(f"y shape: {y_np.shape}")
    
    return X_np, y_np, label_mapping

def train_model(X: np.ndarray, y: np.ndarray) -> Tuple[Any, StandardScaler]:
    """
    Train a classifier on the extracted features.
    
    Args:
        X: Feature matrix
        y: Labels
    
    Returns:
        tuple: (model, scaler) trained model and feature scaler
    """
    # Create a scaler to normalize the features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Create and train the model
    logger.info("Training Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    
    model.fit(X_scaled, y)
    
    # Calculate and print training accuracy
    accuracy = model.score(X_scaled, y)
    logger.info(f"Training accuracy: {accuracy:.4f}")
    
    return model, scaler

def save_model(model: Any, scaler: StandardScaler, label_mapping: Dict[int, str], output_path: str) -> bool:
    """
    Save the trained model and associated data.
    
    Args:
        model: Trained classifier
        scaler: Feature scaler
        label_mapping: Dictionary mapping indices to keyword names
        output_path: Path to save the model package
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        model_package = {
            'model': model,
            'scaler': scaler,
            'label_mapping': label_mapping
        }
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        logger.info(f"Saving model to {output_path}...")
        joblib.dump(model_package, output_path)
        logger.info("Model saved successfully.")
        return True
    except Exception as e:
        logger.error(f"Error saving model: {str(e)}")
        return False

def train_model_from_directory(training_dir: str, model_path: str) -> bool:
    """
    Train a model from a directory of samples.
    
    Args:
        training_dir: Directory containing keyword subdirectories
        model_path: Path to save the trained model
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        start_time = time.time()
        
        logger.info(f"Training model from {training_dir}")
        logger.info(f"Model will be saved to {model_path}")
        
        # Load training data
        X, y, label_mapping = load_training_data(training_dir)
        
        if len(X) == 0:
            logger.error("No valid training data found")
            return False
        
        # Train the model
        logger.info(f"Training with {len(X)} samples across {len(label_mapping)} classes")
        model, scaler = train_model(X, y)
        
        # Save the model
        if not save_model(model, scaler, label_mapping, model_path):
            return False
        
        elapsed_time = time.time() - start_time
        logger.info(f"Training completed successfully in {elapsed_time:.2f} seconds!")
        return True
        
    except Exception as e:
        logger.error(f"Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Command-line interface for training."""
    parser = argparse.ArgumentParser(description="Train an audio keyword detection model")
    parser.add_argument('training_dir', help="Directory containing keyword subdirectories")
    parser.add_argument('--model', default="models/keyword_model.pkl", 
                      help="Path to save model (default: models/keyword_model.pkl)")
    parser.add_argument('--verbose', action='store_true', help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if training directory exists
    if not check_directory(args.training_dir):
        return 1
    
    # Train the model
    success = train_model_from_directory(args.training_dir, args.model)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())