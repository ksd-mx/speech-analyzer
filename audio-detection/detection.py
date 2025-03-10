#!/usr/bin/env python3
"""
Keyword detection module for audio processing.
"""

import numpy as np
import librosa

from feature_extraction import extract_features

def detect_keyword(audio_path, model, scaler, label_mapping, keyword=None, threshold=0.5):
    """
    Detect keywords in an audio file.
    
    Args:
        audio_path: Path to audio file
        model: Trained classifier
        scaler: Feature scaler
        label_mapping: Dictionary mapping indices to keyword names
        keyword: Specific keyword to detect (optional)
        threshold: Confidence threshold (0.0-1.0)
    
    Returns:
        tuple: (result, confidence) where result is the detected keyword,
               a boolean (if keyword specified), or None (if no detection)
    """
    # If a specific keyword was requested, get its index
    keyword_idx = None
    if keyword:
        # Create reverse mapping from keyword to index
        rev_mapping = {v: k for k, v in label_mapping.items()}
        if keyword in rev_mapping:
            keyword_idx = rev_mapping[keyword]
        else:
            print(f"Warning: Requested keyword '{keyword}' not found in model.")
            print(f"Available keywords: {', '.join(label_mapping.values())}")
    
    try:
        # Load audio file
        y, sr = librosa.load(audio_path, sr=None)
        duration = len(y) / sr
        print(f"Loaded audio: {audio_path} (duration: {duration:.2f}s)")
        
        # Extract features
        features = extract_features(y, sr)
        
        # Scale features
        features_scaled = scaler.transform([features])
        
        # Get prediction
        probabilities = model.predict_proba(features_scaled)[0]
        
        # Get the highest confidence prediction
        pred_idx = np.argmax(probabilities)
        confidence = probabilities[pred_idx]
        pred_keyword = label_mapping[pred_idx]
        
        # If a specific keyword was requested
        if keyword_idx is not None:
            req_confidence = probabilities[keyword_idx]
            
            # Print both results
            print(f"Highest confidence: '{pred_keyword}' with {confidence:.1%}")
            print(f"Requested keyword '{keyword}': {req_confidence:.1%}")
            
            # Return based on the requested keyword
            if req_confidence >= threshold:
                return True, req_confidence
            else:
                return False, req_confidence
        else:
            # Return based on highest confidence
            if confidence >= threshold:
                return pred_keyword, confidence
            else:
                return None, confidence
        
    except Exception as e:
        print(f"Error during detection: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, 0.0

def print_detection_results(result, confidence, keyword=None, threshold=0.5):
    """
    Print detection results in a user-friendly format.
    
    Args:
        result: Detection result (keyword string, boolean, or None)
        confidence: Detection confidence
        keyword: Requested keyword (if any)
        threshold: Confidence threshold used
    """
    print("\n--- Detection Results ---")
    
    if keyword:
        # Result is a boolean in this case
        if result:
            print(f"✅ MATCH: '{keyword}' detected with {confidence:.1%} confidence")
        else:
            print(f"❌ NO MATCH: '{keyword}' not detected (confidence: {confidence:.1%})")
    else:
        # Result is a keyword string or None
        if result:
            print(f"✅ DETECTED: '{result}' with {confidence:.1%} confidence")
        else:
            print(f"❌ No keywords detected with confidence above {threshold:.1%}")
            print(f"Best match had {confidence:.1%} confidence")