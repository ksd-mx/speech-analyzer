import redis
import json
import os
import sys
import time
import signal

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Flag to control subscription loop
running = True

def signal_handler(sig, frame):
    """Handle termination signals to gracefully exit"""
    global running
    print("\nShutting down...")
    running = False

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def subscribe_to_topic(topic):
    """Subscribe to a Redis topic and print incoming messages"""
    print(f"Subscribing to topic: {topic}")
    print("Waiting for messages... (Ctrl+C to quit)")
    
    try:
        # Connect to Redis
        r = redis.from_url(REDIS_URL)
        r.ping()  # Test connection
        print(f"Connected to Redis at {REDIS_URL}")
        
        # Create a pubsub object
        pubsub = r.pubsub()
        pubsub.subscribe(topic)
        
        # Process messages
        for message in pubsub.listen():
            if not running:
                break
                
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"].decode("utf-8"))
                    print("\n==== New Message ====")
                    print(f"Job ID: {data.get('job_id', 'N/A')}")
                    
                    if data.get("success", False):
                        # For transcription results
                        if "text" in data:
                            print(f"\nTranscription Result:")
                            print(f"Language: {data.get('language', 'N/A')}")
                            print(f"Duration: {data.get('duration_seconds', 0):.2f} seconds")
                            print(f"Processing Time: {data.get('processing_time_seconds', 0):.2f} seconds")
                            print(f"\nText:")
                            print(data.get("text", ""))
                        
                        # For keyword detection results
                        elif "detected_keywords" in data:
                            print(f"\nKeyword Detection Result:")
                            print(f"Duration: {data.get('duration_seconds', 0):.2f} seconds")
                            print(f"Processing Time: {data.get('processing_time_seconds', 0):.2f} seconds")
                            
                            print(f"\nDetected Keywords:")
                            for keyword, info in data.get("detected_keywords", {}).items():
                                if info.get("detected", False):
                                    print(f"  ✓ '{keyword}' - {info.get('occurrences', 0)} occurrences")
                                else:
                                    print(f"  ✗ '{keyword}' - not found")
                            
                            print(f"\nTranscription:")
                            print(data.get("transcription", ""))
                    else:
                        # Error message
                        print(f"Error: {data.get('error', 'Unknown error')}")
                    
                    print("=====================")
                except json.JSONDecodeError:
                    print(f"Received non-JSON message: {message['data']}")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'pubsub' in locals():
            pubsub.unsubscribe()
            print("Unsubscribed from topic")

def get_history(topic, limit=10):
    """Get recent messages from a topic's history"""
    try:
        # Connect to Redis
        r = redis.from_url(REDIS_URL)
        r.ping()  # Test connection
        
        # Get messages from the history list
        list_key = f"history:{topic}"
        messages = r.lrange(list_key, 0, limit - 1)
        
        if not messages:
            print(f"No history found for topic: {topic}")
            return
            
        print(f"Recent messages for topic '{topic}':")
        for i, msg_data in enumerate(messages):
            try:
                data = json.loads(msg_data)
                print(f"\n--- Message {i+1} ---")
                print(f"Job ID: {data.get('job_id', 'N/A')}")
                print(f"Timestamp: {data.get('timestamp', 'N/A')}")
                if "text" in data:
                    print(f"Language: {data.get('language', 'N/A')}")
                    print(f"Text: {data.get('text', '')[:100]}...")
                elif "detected_keywords" in data:
                    keywords = data.get("detected_keywords", {})
                    detected = sum(1 for k, v in keywords.items() if v.get("detected", False))
                    print(f"Keywords: {detected} detected out of {len(keywords)}")
            except json.JSONDecodeError:
                print(f"Message {i+1}: [Invalid JSON format]")
        
    except Exception as e:
        print(f"Error: {str(e)}")

def print_usage():
    print("Redis Subscriber Client")
    print("=======================")
    print("\nUsage:")
    print("  subscribe <topic>    Subscribe to real-time messages on a topic")
    print("  history <topic>      View recent messages from a topic")
    print("\nExamples:")
    print("  python subscriber.py subscribe transcriptions")
    print("  python subscriber.py history keyword_detections")
    print("\nDefault topics:")
    print("  - transcriptions")
    print("  - keyword_detections")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    topic = sys.argv[2]
    
    if command == "subscribe":
        subscribe_to_topic(topic)
    elif command == "history":
        get_history(topic)
    else:
        print_usage()
        sys.exit(1)