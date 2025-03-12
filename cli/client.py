#!/usr/bin/env python3
"""
Command-line client for interacting with the audio keyword detection API.
"""

import os
import sys
import argparse
import requests
import json
import time
import uuid
import signal
from typing import List, Dict, Any, Optional

from queueing.queue_subscriber import QueueSubscriber

# Get API URL from environment variable or use default
API_URL = os.environ.get("AUDIO_DETECTION_API_URL", "http://localhost:8000")

def health_check() -> bool:
    """
    Check if the API is up and running.
    
    Returns:
        bool: True if API is available, False otherwise
    """
    try:
        response = requests.get(f"{API_URL}/health")
        response.raise_for_status()
        result = response.json()
        
        print("API Health Check:")
        print(f"  Status: {result['status']}")
        print(f"  Version: {result['version']}")
        print(f"  API: {result['api']}")
        print(f"  Connected to: {API_URL}")
        
        return True
    except Exception as e:
        print(f"Error: API is not available at {API_URL} - {str(e)}")
        return False

def list_strategies() -> bool:
    """
    List available detection strategies.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        response = requests.get(f"{API_URL}/keywords/strategies")
        response.raise_for_status()
        strategies = response.json()
        
        print("\nAvailable Detection Strategies:")
        for name, info in strategies.items():
            print(f"\n{name.upper()}:")
            print(f"  Description: {info['description']}")
            
            print("  Available Models:")
            if info.get('models'):
                for model in info['models']:
                    print(f"    - {model}")
            else:
                print("    - No models available")
        
        return True
    except Exception as e:
        print(f"Error: Failed to list strategies - {str(e)}")
        return False

def detect_keywords(file_path: str, keywords: str, strategy: str = "whisper", 
                  threshold: float = 0.5, model: Optional[str] = None) -> bool:
    """
    Detect keywords in an audio file.
    
    Args:
        file_path: Path to the audio file
        keywords: Comma-separated list of keywords to detect
        strategy: Detection strategy to use ('whisper' or 'classifier')
        threshold: Confidence threshold (0.0-1.0)
        model: Model name/path for classifier strategy
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}")
        return False
    
    if not keywords:
        print("Error: No keywords provided")
        return False
    
    print(f"Detecting keywords in file: {file_path}")
    print(f"Keywords to detect: {keywords}")
    print(f"Strategy: {strategy}")
    print(f"Threshold: {threshold}")
    if model:
        print(f"Model: {model}")
    print(f"Using API at: {API_URL}")
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {
                "strategy": strategy,
                "keywords": keywords,
                "threshold": str(threshold)
            }
            
            if model:
                data["model"] = model
            
            response = requests.post(f"{API_URL}/keywords/detect", files=files, data=data)
            response.raise_for_status()
            result = response.json()
            
            print("\nKeyword Detection Result:")
            print(f"  Job ID: {result['job_id']}")
            print(f"  Strategy: {result['strategy']}")
            print(f"  Duration: {result['duration_seconds']:.2f} seconds")
            print(f"  Processing Time: {result['processing_time_seconds']:.2f} seconds")
            
            print("\nDetected Keywords:")
            for detection in result['detections']:
                keyword = detection['keyword']
                if detection['detected']:
                    print(f"  ✓ '{keyword}' - {detection['occurrences']} occurrences")
                    
                    # Print details for each occurrence
                    if detection['occurrences'] > 0:
                        for i in range(detection['occurrences']):
                            pos = detection['positions'][i] if i < len(detection['positions']) else "unknown"
                            conf = detection['confidence_scores'][i] if i < len(detection['confidence_scores']) else 0.0
                            print(f"    - Position: {pos}, Confidence: {conf:.1%}")
                else:
                    print(f"  ✗ '{keyword}' - not found")
            
            # Print transcription for Whisper strategy
            if result.get('transcription'):
                print("\nFull Transcription:")
                print(result['transcription'])
            
            return True
            
    except requests.HTTPError as e:
        if e.response.status_code == 500:
            error_detail = e.response.json().get('detail', 'Unknown error')
            print(f"Server Error: {error_detail}")
        else:
            print(f"HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def subscribe_to_topic(topic: str, queue_type: Optional[str] = None) -> bool:
    """
    Subscribe to a queue topic for detection results.
    
    Args:
        topic: Topic to subscribe to
        queue_type: Queue type to use (redis, mqtt, or logging)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Configure the subscriber
        config = {}
        if queue_type:
            config["queue_type"] = queue_type
        
        # Create the subscriber
        subscriber = QueueSubscriber(config)
        
        # Define a custom callback for received messages
        def message_callback(topic, message):
            timestamp = message.get('timestamp', 'Unknown time')
            job_id = message.get('job_id', 'Unknown job')
            
            print(f"\n[{timestamp}] Received message on topic '{topic}':")
            print(f"  Job ID: {job_id}")
            
            if not message.get('success', False):
                print(f"  Status: Failed - {message.get('error', 'Unknown error')}")
                return
            
            print(f"  Status: Success")
            print(f"  Strategy: {message.get('strategy', 'unknown')}")
            print(f"  File: {message.get('filename', 'unknown')}")
            print(f"  Duration: {message.get('duration_seconds', 0):.2f} seconds")
            print(f"  Processing Time: {message.get('processing_time_seconds', 0):.2f} seconds")
            
            if 'detections' in message:
                print("\n  Detected Keywords:")
                for detection in message['detections']:
                    keyword = detection['keyword']
                    if detection['detected']:
                        print(f"    ✓ '{keyword}' - {detection['occurrences']} occurrences")
                    else:
                        print(f"    ✗ '{keyword}' - not found")
            
            sys.stdout.flush()  # Ensure output is displayed immediately
        
        # Subscribe to the topic
        print(f"Subscribing to topic: {topic}")
        if queue_type:
            print(f"Using queue type: {queue_type}")
        
        success = subscriber.subscribe(topic, message_callback)
        if not success:
            print(f"Failed to subscribe to topic: {topic}")
            return False
        
        print("Subscription active. Waiting for messages...")
        print("Press Ctrl+C to stop.")
        
        # Run the subscriber
        subscriber.run_forever()
        
        return True
    except KeyboardInterrupt:
        print("\nSubscription stopped by user.")
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def print_usage():
    """Print usage information."""
    print("Audio Keyword Detection Client")
    print("==============================")
    print("\nCommands:")
    print("  health                     Check API health")
    print("  strategies                 List available detection strategies")
    print("  detect <file> <keywords>   Detect keywords in audio file")
    print("  subscribe <topic>          Subscribe to detection results")
    print("\nExamples:")
    print("  client.py health")
    print("  client.py strategies")
    print("  client.py detect recording.mp3 \"hello,world\"")
    print("  client.py detect recording.mp3 \"hello,world\" --strategy classifier --model my_model.pkl")
    print("  client.py subscribe keyword_detections")
    print("  client.py subscribe keyword_detections --queue-type redis")
    print("\nConfiguration:")
    print(f"  API URL: {API_URL} (set with AUDIO_DETECTION_API_URL environment variable)")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Audio Keyword Detection Client")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Health check command
    health_parser = subparsers.add_parser("health", help="Check API health")
    
    # List strategies command
    strategies_parser = subparsers.add_parser("strategies", help="List available detection strategies")
    
    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect keywords in audio file")
    detect_parser.add_argument("file", help="Audio file to analyze")
    detect_parser.add_argument("keywords", help="Comma-separated list of keywords to detect")
    detect_parser.add_argument("--strategy", default="whisper", help="Detection strategy (whisper or classifier)")
    detect_parser.add_argument("--threshold", type=float, default=0.5, help="Confidence threshold (0.0-1.0)")
    detect_parser.add_argument("--model", help="Model name/path for classifier strategy")
    
    # Subscribe command
    subscribe_parser = subparsers.add_parser("subscribe", help="Subscribe to detection results")
    subscribe_parser.add_argument("topic", default="keyword_detections", nargs="?", help="Topic to subscribe to")
    subscribe_parser.add_argument("--queue-type", choices=["redis", "mqtt", "logging"], 
                                help="Queue type to use (defaults to environment config)")
    
    args = parser.parse_args()
    
    if args.command == "health":
        return 0 if health_check() else 1
    
    elif args.command == "strategies":
        return 0 if list_strategies() else 1
    
    elif args.command == "detect":
        return 0 if detect_keywords(
            args.file, args.keywords, args.strategy, args.threshold, args.model
        ) else 1
    
    elif args.command == "subscribe":
        return 0 if subscribe_to_topic(args.topic, args.queue_type) else 1
    
    else:
        print_usage()
        return 1

if __name__ == "__main__":
    sys.exit(main())