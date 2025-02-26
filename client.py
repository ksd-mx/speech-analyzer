#!/usr/bin/env python3
import sys
import requests
import json
import os

# Get API URL from environment variable or use default
API_URL = os.environ.get("WHISPER_API_URL", "http://localhost:8000")

def health_check():
    """Check if the API is up and running"""
    try:
        response = requests.get(f"{API_URL}/health")
        response.raise_for_status()
        result = response.json()
        
        print("API Health Check:")
        print(f"  Status: {result['status']}")
        print(f"  Model: {result['model']}")
        print(f"  Device: {result['device']}")
        print(f"  Timestamp: {result['timestamp']}")
        print(f"  Connected to: {API_URL}")
        
        return True
    except Exception as e:
        print(f"Error: API is not available at {API_URL} - {str(e)}")
        return False

def transcribe_audio(file_path):
    """Transcribe an audio file"""
    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}")
        return
    
    print(f"Transcribing file: {file_path}")
    print(f"Using API at: {API_URL}")
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            response = requests.post(f"{API_URL}/transcribe", files=files)
            response.raise_for_status()
            result = response.json()
            
            print("\nTranscription Result:")
            print(f"  Language: {result['language']}")
            print(f"  Duration: {result['duration_seconds']:.2f} seconds")
            print(f"  Processing Time: {result['processing_time_seconds']:.2f} seconds")
            print("\nText:")
            print(result['text'])
            
    except requests.HTTPError as e:
        if e.response.status_code == 500:
            error_detail = e.response.json().get('detail', 'Unknown error')
            print(f"Server Error: {error_detail}")
        else:
            print(f"HTTP Error: {e}")
    except Exception as e:
        print(f"Error: {str(e)}")

def detect_keywords(file_path, keywords):
    """Detect keywords in an audio file"""
    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}")
        return
    
    if not keywords:
        print("Error: No keywords provided")
        return
    
    print(f"Detecting keywords in file: {file_path}")
    print(f"Keywords to detect: {keywords}")
    print(f"Using API at: {API_URL}")
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {"keywords": keywords}
            response = requests.post(f"{API_URL}/detect-keywords", files=files, data=data)
            response.raise_for_status()
            result = response.json()
            
            print("\nKeyword Detection Result:")
            print(f"  Duration: {result['duration_seconds']:.2f} seconds")
            print(f"  Processing Time: {result['processing_time_seconds']:.2f} seconds")
            
            print("\nDetected Keywords:")
            for keyword, info in result['detected_keywords'].items():
                if info['detected']:
                    print(f"  ✓ '{keyword}' - {info['occurrences']} occurrences")
                else:
                    print(f"  ✗ '{keyword}' - not found")
            
            print("\nFull Transcription:")
            print(result['transcription'])
            
    except requests.HTTPError as e:
        if e.response.status_code == 500:
            error_detail = e.response.json().get('detail', 'Unknown error')
            print(f"Server Error: {error_detail}")
        else:
            print(f"HTTP Error: {e}")
    except Exception as e:
        print(f"Error: {str(e)}")

def print_usage():
    """Print usage information"""
    print("Usage:")
    print("  python client.py health")
    print("  python client.py transcribe <audio_file>")
    print("  python client.py detect <audio_file> <keywords>")
    print("\nExamples:")
    print("  python client.py health")
    print("  python client.py transcribe recording.mp3")
    print("  python client.py detect recording.mp3 \"hello,world,important\"")
    print("\nConfiguration:")
    print(f"  API URL: {API_URL} (set with WHISPER_API_URL environment variable)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "health":
        health_check()
    
    elif command == "transcribe" and len(sys.argv) >= 3:
        transcribe_audio(sys.argv[2])
    
    elif command == "detect" and len(sys.argv) >= 4:
        detect_keywords(sys.argv[2], sys.argv[3])
    
    else:
        print_usage()
        sys.exit(1)