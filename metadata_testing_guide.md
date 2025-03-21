# Metadata Testing Guide

This guide provides instructions and commands for testing the newly implemented metadata feature in the Speech Analyzer system.

## Test Setup

Before running the tests, make sure you have:

1. Installed all requirements from `requirements.txt`
2. Have a test audio file (WAV format)
3. Started the API server (if testing the API)

## Testing the API Endpoint

### Using cURL

The simplest way to test the metadata feature is using cURL:

```bash
curl -X POST http://localhost:8000/keywords/detect \
  -F "file=@your_audio_file.wav" \
  -F "strategy=whisper" \
  -F "keywords=hello,world" \
  -F "threshold=0.5" \
  -F 'metadata={"timestamp":"2025-03-21T12:00:00Z","framerate":30,"source":"camera1","output_path":"/storage/results/"}'
```

### Using Python Requests

Here's a Python script you can use to test the metadata feature:

```python
#!/usr/bin/env python3
"""
Test script for metadata functionality in the Audio Keyword Detection API.
"""

import requests
import json
import sys
import os

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
    
    # Example metadata
    metadata = {
        "timestamp": "2025-03-21T12:00:00Z",
        "framerate": 30,
        "source": "camera1",
        "output_path": "/storage/results/",
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
    
    print(f"Sending request with metadata: {json.dumps(metadata, indent=2)}")
    
    try:
        # Make the request
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
        else:
            print(f"\n❌ ERROR: Request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"\n❌ ERROR: Exception occurred: {str(e)}")
    finally:
        files["file"].close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_metadata.py <audio_file.wav> [keywords] [strategy] [threshold]")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    keywords = sys.argv[2] if len(sys.argv) > 2 else "hello,world" 
    strategy = sys.argv[3] if len(sys.argv) > 3 else "whisper"
    threshold = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    
    test_metadata_feature(audio_file, keywords, strategy, threshold)
```

Save this script to a file (e.g., `test_metadata.py`), make it executable, and run it with:

```bash
python test_metadata.py your_audio_file.wav "hello,world" whisper 0.5
```

## Testing with Unit Tests

You can also run the unit tests we've added for the metadata feature:

```bash
cd tests
python -m unittest test_api.py
```

This will run all tests, including the new `test_detect_keywords_with_metadata` test that verifies:
1. Metadata can be passed through form fields as a JSON string
2. The API correctly parses the metadata
3. The metadata is included in the response

## Common Issues & Solutions

### Invalid JSON Error

If you see this error:
```
{"detail":"Invalid metadata format. Must be valid JSON."}
```

It means the JSON string you provided for metadata is malformed. Common issues include:
- Missing quotes around keys
- Using single quotes for keys inside the JSON string
- Incorrect escaping of special characters

Ensure your JSON is properly formatted:
```json
{
  "timestamp": "2025-03-21T12:00:00Z", 
  "framerate": 30,
  "source": "camera1"
}
```

### Missing Metadata in Response

If metadata is missing from the response, check:
1. The API endpoint implementation in `api/routers/detection.py`
2. That JSON parsing is working correctly
3. That the response includes the metadata field

### Important Notes on Threshold Values

When testing, pay attention to the threshold values:

- Always set a detection confidence threshold appropriate for your use case
- For Whisper strategy: values closer to 0.5 are often sufficient (default)
- For Classifier strategy: higher values (0.6-0.8) may be needed for better precision
- Lower thresholds increase recall but may produce more false positives
- Higher thresholds increase precision but may miss some occurrences

## Queue Verification (Optional)

To verify that metadata is also passed through the queue system, you can use the queue subscriber:

```bash
# Start a subscription client
python -m cli.client subscribe keyword_detections --queue-type mqtt
```

Then perform a detection request with metadata, and verify that the metadata appears in the queue messages received by the subscription client.