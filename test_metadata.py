#!/usr/bin/env python3
"""
Test script for metadata functionality in the Audio Keyword Detection API.
"""

import requests
import json
import sys
import os
import argparse
from datetime import datetime

def test_metadata_feature(audio_file, keywords="hello,world", strategy="whisper", threshold=0.5):
    """
    Test metadata functionality with the API.
    
    Args:
        audio_file: Path to audio file
        keywords: Comma-separated list of keywords
        strategy: Detection strategy (whisper or classifier)
        threshold: Detection threshold
    """
    if not os.path.exists(audio_file):
        print(f"Error: Audio file '{audio_file}' not found.")
        return
    
    # Example metadata with various useful fields
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "framerate": 30,
        "source": "test_script",
        "output_path": f"/storage/results/{os.path.basename(audio_file)}",
        "custom_field": "Testing metadata feature"
    }
    
    # Prepare the request
    url = "http://localhost:8000/keywords/detect"
    files = {"file": open(audio_file, "rb")}
    data = {
        "strategy": strategy,
        "keywords": keywords,
        "threshold": str(threshold),
        "metadata": json.dumps(metadata)
    }
    
    print(f"Sending request to: {url}")
    print(f"Detection parameters:")
    print(f"  - File: {audio_file}")
    print(f"  - Keywords: {keywords}")
    print(f"  - Strategy: {strategy}")
    print(f"  - Threshold: {threshold}")
    print(f"\nMetadata being sent:")
    print(json.dumps(metadata, indent=2))
    
    try:
        # Make the request
        print("\nSending request...")
        response = requests.post(url, files=files, data=data)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            print("\nAPI Response:")
            print(json.dumps(result, indent=2))
            
            # Verify metadata in response
            if "metadata" in result and result["metadata"] == metadata:
                print("\n✅ SUCCESS: Metadata correctly passed through the system!")
            else:
                print("\n❌ ERROR: Metadata not properly returned in response")
                if "metadata" not in result:
                    print("  - Metadata field missing from response")
                else:
                    print("  - Metadata in response doesn't match sent metadata")
                    
            # Report on detection results
            detection_count = sum(d['detected'] for d in result.get('detections', []))
            if detection_count > 0:
                print(f"\nDetected {detection_count} keywords in the audio file.")
                for detection in result.get('detections', []):
                    if detection['detected']:
                        keyword = detection['keyword']
                        occurrences = detection['occurrences']
                        confidence = max(detection['confidence_scores']) if detection['confidence_scores'] else 0
                        print(f"  - '{keyword}': {occurrences} occurrences (confidence: {confidence:.2f})")
            else:
                print("\nNo keywords were detected in the audio file.")
                
        else:
            print(f"\n❌ ERROR: Request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Connection error. Is the API server running?")
        print("  Start the server with: uvicorn api.app:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"\n❌ ERROR: Exception occurred: {str(e)}")
    finally:
        files["file"].close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test metadata functionality in the Speech Analyzer API")
    parser.add_argument("audio_file", help="Path to the audio file for testing")
    parser.add_argument("--keywords", default="hello,world", help="Comma-separated list of keywords to detect")
    parser.add_argument("--strategy", default="whisper", choices=["whisper", "classifier"], 
                        help="Detection strategy (whisper or classifier)")
    parser.add_argument("--threshold", type=float, default=0.5, 
                        help="Detection confidence threshold (0.0-1.0)")
    
    args = parser.parse_args()
    
    test_metadata_feature(args.audio_file, args.keywords, args.strategy, args.threshold)