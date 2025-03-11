#!/usr/bin/env python3
"""
Utility functions for audio keyword detection.
"""

import os
import warnings

# Configure warnings
def suppress_warnings():
    """Suppress unnecessary warnings."""
    warnings.filterwarnings("ignore")

def check_audio_file(file_path):
    """
    Check if an audio file exists and has a valid extension.
    
    Args:
        file_path: Path to the audio file
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not os.path.isfile(file_path):
        print(f"Error: Audio file '{file_path}' not found")
        return False
        
    valid_extensions = ['.wav', '.mp3', '.ogg', '.flac']
    if not any(file_path.lower().endswith(ext) for ext in valid_extensions):
        print(f"Warning: File '{file_path}' may not be a valid audio file")
        # Still return True as we'll let librosa try to load it
    
    return True

def check_directory(dir_path, create=False):
    """
    Check if a directory exists, optionally create it.
    
    Args:
        dir_path: Path to the directory
        create: If True, create the directory if it doesn't exist
    
    Returns:
        bool: True if directory exists or was created, False otherwise
    """
    if os.path.exists(dir_path):
        if not os.path.isdir(dir_path):
            print(f"Error: '{dir_path}' exists but is not a directory")
            return False
        return True
    elif create:
        try:
            os.makedirs(dir_path)
            print(f"Created directory: {dir_path}")
            return True
        except Exception as e:
            print(f"Error creating directory '{dir_path}': {str(e)}")
            return False
    else:
        print(f"Error: Directory '{dir_path}' not found")
        return False