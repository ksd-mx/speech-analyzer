#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import os
import sys
import time
import signal
import uuid

# Configuration
MQTT_BROKER_URL = os.environ.get("MQTT_BROKER_URL", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", None)
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", None)
MQTT_CLIENT_ID = os.environ.get("MQTT_CLIENT_ID", f"mosque-audio-sub-{uuid.uuid4().hex[:8]}")

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

def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker"""
    if rc == 0:
        print(f"Connected to MQTT broker at {MQTT_BROKER_URL}:{MQTT_PORT}")
        if userdata.get("topic"):
            client.subscribe(userdata["topic"])
            print(f"Subscribed to topic: {userdata['topic']}")
    else:
        print(f"Connection failed with code {rc}")
        global running
        running = False

def on_message(client, userdata, msg):
    """Callback for when a message is received"""
    try:
        data = json.loads(msg.payload.decode())
        print("\n==== New Message ====")
        print(f"Topic: {msg.topic}")
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
        print(f"Received non-JSON message: {msg.payload}")

def subscribe_to_topic(topic):
    """Subscribe to a MQTT topic and print incoming messages"""
    print(f"Subscribing to topic: {topic}")
    print("Waiting for messages... (Ctrl+C to quit)")
    
    try:
        # Create userdata dictionary to pass to callbacks
        userdata = {"topic": topic}
        
        # Set up the client
        client = mqtt.Client(client_id=MQTT_CLIENT_ID, userdata=userdata)
        client.on_connect = on_connect
        client.on_message = on_message
        
        # Set username and password if provided
        if MQTT_USERNAME and MQTT_PASSWORD:
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
        # Connect to the broker
        client.connect(MQTT_BROKER_URL, MQTT_PORT, 60)
        
        # Start the loop
        client.loop_start()
        
        # Keep the script running until interrupted
        while running:
            time.sleep(0.1)
            
        # Clean up
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        print(f"Error: {str(e)}")

def print_usage():
    print("MQTT Subscriber Client")
    print("=====================")
    print("\nUsage:")
    print("  python mqtt_subscriber.py <topic>")
    print("\nExamples:")
    print("  python mqtt_subscriber.py transcriptions")
    print("  python mqtt_subscriber.py keyword_detections")
    print("\nDefault topics:")
    print("  - transcriptions")
    print("  - keyword_detections")
    print("\nConfiguration:")
    print(f"  MQTT Broker: {MQTT_BROKER_URL}:{MQTT_PORT}")
    print(f"  Client ID: {MQTT_CLIENT_ID}")
    print("  (Set environment variables MQTT_BROKER_URL and MQTT_PORT to change)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    topic = sys.argv[1]
    subscribe_to_topic(topic)