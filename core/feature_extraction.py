#!/usr/bin/env python3
"""
Feature extraction module for audio keyword detection.
"""

import numpy as np
import librosa

def extract_features(y, sr):
    """
    Basic feature extraction that works reliably.
    
    Args:
        y: Audio time series
        sr: Sampling rate
    
    Returns:
        numpy.ndarray: Feature vector
    """
    # Initialize empty list for features
    features = []
    
    # Basic statistics of the raw audio
    features.append(float(np.mean(y)))
    features.append(float(np.std(y)))
    features.append(float(np.max(y)))
    features.append(float(np.min(y)))
    
    # Simple spectral features
    if len(y) > 0:
        # Spectral centroid
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        features.append(float(np.mean(centroid)))
        
        # Spectral rolloff
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
        features.append(float(np.mean(rolloff)))
        
        # Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(y)
        features.append(float(np.mean(zcr)))
        
        # RMS energy
        rms = librosa.feature.rms(y=y)
        features.append(float(np.mean(rms)))
    else:
        # Add zeros if the audio is empty
        features.extend([0.0, 0.0, 0.0, 0.0])
    
    # MFCC features
    try:
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=8)
        for i in range(mfccs.shape[0]):
            features.append(float(np.mean(mfccs[i])))
    except:
        # If MFCC calculation fails, add zeros
        features.extend([0.0] * 8)
    
    # Return as a numpy array
    return np.array(features)