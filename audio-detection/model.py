#!/usr/bin/env python3
"""
Model training and management module for audio keyword detection.
"""

import os
import numpy as np
import librosa
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from feature_extraction import extract_features

def load_training_data(training_dir):
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
    
    print(f"Found {len(keywords)} keyword classes: {', '.join(keywords)}")
    
    # Assign label indices
    for i, keyword in enumerate(keywords):
        label_mapping[i] = keyword
    
    # Process each keyword directory
    for i, keyword in enumerate(keywords):
        keyword_dir = os.path.join(training_dir, keyword)
        print(f"Loading {keyword} samples from {keyword_dir}...")
        
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
                        print(f"  Processing: {file}")
                        y_audio, sr = librosa.load(file_path, sr=None, duration=2.0)
                        
                        # Extract features
                        features = extract_features(y_audio, sr)
                        
                        # Add to our datasets
                        X.append(features)
                        y.append(i)
                        
                        # Increment counter
                        count += 1
                    except Exception as e:
                        print(f"  Error processing {file}: {str(e)}")
        
        print(f"  Loaded {count} samples for '{keyword}'")
    
    # Convert to numpy arrays before returning
    X_np = np.array(X)
    y_np = np.array(y)
    
    # Debug output
    print(f"X shape: {X_np.shape}")
    print(f"y shape: {y_np.shape}")
    
    return X_np, y_np, label_mapping

def train_model(X, y):
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
    print("Training Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    
    model.fit(X_scaled, y)
    
    # Calculate and print training accuracy
    accuracy = model.score(X_scaled, y)
    print(f"Training accuracy: {accuracy:.4f}")
    
    return model, scaler

def save_model(model, scaler, label_mapping, output_path):
    """
    Save the trained model and associated data.
    
    Args:
        model: Trained classifier
        scaler: Feature scaler
        label_mapping: Dictionary mapping indices to keyword names
        output_path: Path to save the model package
    """
    model_package = {
        'model': model,
        'scaler': scaler,
        'label_mapping': label_mapping
    }
    
    print(f"Saving model to {output_path}...")
    joblib.dump(model_package, output_path)
    print("Model saved successfully.")

def load_model(model_path):
    """
    Load a saved model.
    
    Args:
        model_path: Path to the saved model package
    
    Returns:
        tuple: (model, scaler, label_mapping)
    """
    print(f"Loading model from {model_path}...")
    model_package = joblib.load(model_path)
    
    model = model_package['model']
    scaler = model_package['scaler']
    label_mapping = model_package['label_mapping']
    
    return model, scaler, label_mapping