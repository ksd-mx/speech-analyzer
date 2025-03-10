# Speech Audio Analysis

A self-hosted voice recognition system for analyzing speech audio content, built on OpenAI's Whisper model with flexible message queuing for asynchronous processing.

## Overview

Speech Audio Analysis is a containerized service that provides:

- High-quality speech-to-text transcription of audio recordings
- Keyword detection in audio files with occurrence counts and positions
- Flexible message queuing for asynchronous result processing (MQTT, Redis, or Logging)
- Easy deployment using Docker with support for Apple Silicon

The system exposes a RESTful API and leverages message queuing through MQTT or Redis, making it suitable for both real-time analysis and batch processing workflows.

## Features

- **Transcription Service**: Convert speech to text with language detection
- **Keyword Detection**: Search audio for specific phrases with occurrence counts
- **Flexible Message Queue**: Publish results to MQTT or Redis topics for asynchronous consumption
- **Multiple Model Support**: Choose from different Whisper model sizes based on accuracy needs
- **Hardware Acceleration**: Support for MPS (Metal Performance Shaders) on Apple Silicon
- **Containerized**: Easy deployment with Docker and Docker Compose
- **Client Tools**: Python clients for making requests and subscribing to results

## Architecture

The system consists of:

1. **API Server**: FastAPI application that processes audio files
2. **Message Queue**: MQTT broker (default) or Redis for distributing results
3. **Client Tools**: 
   - `client.py`: Command-line tool for sending requests to the API
   - `mqtt_subscriber.py`: Tool for subscribing to and viewing results from MQTT
   - `subscriber.py`: Tool for subscribing to and viewing results from Redis (if using Redis)
4. **Queue Strategy Pattern**: Flexible implementation that allows switching between message queue backends

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Audio files for analysis (MP3, WAV, etc.)
- Python 3.9+ (for client tools)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/speech-audio-analysis.git
   cd speech-audio-analysis
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Verify the installation:
   ```bash
   python client.py health
   ```
   
   You should see output like:
   ```
   API Health Check:
     Status: ok
     Model: small
     Device: cpu
     Timestamp: 2025-03-06 14:30:45
     Queue Status: connected
     Connected to: http://localhost:8000
   ```

## Usage

### Using the Client Script

#### Transcribing Audio

```bash
python client.py transcribe path/to/recording.mp3
```

Example output:
```
Transcribing file: path/to/recording.mp3
Using API at: http://localhost:8000

Transcription Result:
  Language: en
  Duration: 65.21 seconds
  Processing Time: 12.45 seconds

Text:
Welcome to the annual conference on climate science. Today we'll be discussing the latest research findings on global temperature trends. I'm pleased to introduce our keynote speaker, Dr. Sarah Johnson, who will present her groundbreaking work on atmospheric carbon measurements.
```

#### Detecting Keywords

```bash
python client.py detect path/to/recording.mp3 "climate,research,temperature"
```

Example output:
```
Detecting keywords in file: path/to/recording.mp3
Keywords to detect: climate,research,temperature
Using API at: http://localhost:8000

Keyword Detection Result:
  Duration: 65.21 seconds
  Processing Time: 13.12 seconds

Detected Keywords:
  ✓ 'climate' - 2 occurrences
  ✓ 'research' - 1 occurrences
  ✓ 'temperature' - 1 occurrences

Full Transcription:
Welcome to the annual conference on climate science. Today we'll be discussing the latest research findings on global temperature trends. I'm pleased to introduce our keynote speaker, Dr. Sarah Johnson, who will present her groundbreaking work on atmospheric carbon measurements.
```

### Subscribing to Results

To receive real-time notifications when jobs are processed (using MQTT, which is the default):

```bash
python mqtt_subscriber.py transcriptions
```

Example output:
```
Subscribing to topic: transcriptions
Waiting for messages... (Ctrl+C to quit)
Connected to MQTT broker at localhost:1883

==== New Message ====
Topic: transcriptions
Job ID: 3f7b8c1d-a2e4-4d5f-9e6b-7c8d9e0f1a2b

Transcription Result:
Language: en
Duration: 65.21 seconds
Processing Time: 12.45 seconds

Text:
Welcome to the annual conference on climate science. Today we'll be discussing the latest research findings...
=====================
```

If using Redis instead (set `QUEUE_TYPE=redis` in environment):

```bash
python subscriber.py subscribe transcriptions
```

#### Viewing Result History (Redis only)

```bash
python subscriber.py history transcriptions
```

Example output:
```
Recent messages for topic 'transcriptions':

--- Message 1 ---
Job ID: 3f7b8c1d-a2e4-4d5f-9e6b-7c8d9e0f1a2b
Timestamp: 2025-03-06 15:30:45
Language: en
Text: Welcome to the annual conference on climate science. Today we'll be discussing the latest research findings...

--- Message 2 ---
Job ID: 9e0f1a2b-3f7b-8c1d-a2e4-4d5f9e6b7c8d
Timestamp: 2025-03-06 14:20:30
Language: fr
Text: Bienvenue à notre conférence sur les nouvelles technologies d'intelligence artificielle...
```

### Using the API Directly

The API can be called directly using standard HTTP requests:

#### Health Check

```bash
curl http://localhost:8000/health
```

Example response:
```json
{
  "status": "ok",
  "model": "small",
  "device": "cpu",
  "timestamp": "2025-03-06 14:30:45",
  "queue_status": "connected"
}
```

#### Transcribe Audio

```bash
curl -X POST http://localhost:8000/transcribe \
  -F "file=@path/to/recording.mp3" \
  -F "model=small" \
  -F "topic=transcriptions"
```

Example response:
```json
{
  "success": true,
  "text": "Welcome to the annual conference on climate science. Today we'll be discussing the latest research findings...",
  "language": "en",
  "duration_seconds": 65.21,
  "processing_time_seconds": 12.45,
  "job_id": "3f7b8c1d-a2e4-4d5f-9e6b-7c8d9e0f1a2b"
}
```

#### Detect Keywords

```bash
curl -X POST http://localhost:8000/detect-keywords \
  -F "file=@path/to/recording.mp3" \
  -F "keywords=climate,research,temperature" \
  -F "model=small" \
  -F "topic=keyword_detections"
```

Example response:
```json
{
  "success": true,
  "transcription": "Welcome to the annual conference on climate science. Today we'll be discussing the latest research findings on global temperature trends...",
  "detected_keywords": {
    "climate": {
      "detected": true,
      "occurrences": 2,
      "positions": [29, 115]
    },
    "research": {
      "detected": true,
      "occurrences": 1,
      "positions": [67]
    },
    "temperature": {
      "detected": true,
      "occurrences": 1,
      "positions": [88]
    }
  },
  "duration_seconds": 65.21,
  "processing_time_seconds": 13.12,
  "job_id": "9e0f1a2b-3f7b-8c1d-a2e4-4d5f9e6b7c8d"
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| WHISPER_MODEL | Whisper model size (tiny, base, small, medium, large) | small |
| CACHE_MODELS | Enable model caching | true |
| UPLOAD_DIR | Directory to store uploaded files | /tmp/whisper_uploads |
| WHISPER_API_URL | API URL for client tools | http://localhost:8000 |
| QUEUE_TYPE | Message queue type (mqtt, redis, logging) | mqtt |
| QUEUE_ENABLED | Enable message queue | true |
| MQTT_BROKER_URL | MQTT broker hostname | mosquitto |
| MQTT_PORT | MQTT broker port | 1883 |
| MQTT_USERNAME | MQTT username | |
| MQTT_PASSWORD | MQTT password | |
| MQTT_QOS | MQTT quality of service | 0 |
| MQTT_RETAIN | MQTT retain messages | false |
| REDIS_URL | Redis connection string | redis://redis:6379/0 |

### Docker Configuration

The `docker-compose.yaml` file can be modified to:
- Change resource limits
- Change exposed ports
- Adjust message queue configuration
- Switch to different Whisper models

Example configuration in docker-compose.yaml:
```yaml
services:
  whisper-api:
    platform: linux/arm64  # Specifically for Apple Silicon
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - whisper-data:/tmp/whisper_uploads
      - ./app.py:/app/app.py
      - ./queue_strategy.py:/app/queue_strategy.py
      - ./queue_manager.py:/app/queue_manager.py
    environment:
      # Whisper configuration
      - WHISPER_MODEL=small
      - CACHE_MODELS=true
      - UPLOAD_DIR=/tmp/whisper_uploads
      
      # Queue configuration
      - QUEUE_TYPE=mqtt # Options: redis, mqtt, logging
      - QUEUE_ENABLED=true
      
      # MQTT settings
      - MQTT_BROKER_URL=mosquitto
      - MQTT_PORT=1883
    mem_limit: 8g          # Increase for larger models
    mem_reservation: 2g
    depends_on:
      - redis
      - mosquitto
```

## API Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| /health | GET | Check service health | None |
| /transcribe | POST | Transcribe audio file | file (required), model (optional), topic (optional) |
| /detect-keywords | POST | Detect keywords in audio file | file (required), keywords (required, comma-separated), model (optional), topic (optional) |

## Message Format

### Transcription Result

```json
{
  "success": true,
  "text": "Transcribed text content...",
  "language": "en",
  "duration_seconds": 65.21,
  "processing_time_seconds": 12.45,
  "job_id": "3f7b8c1d-a2e4-4d5f-9e6b-7c8d9e0f1a2b",
  "filename": "recording.mp3",
  "timestamp": "2025-03-06 15:30:45"
}
```

### Keyword Detection Result

```json
{
  "success": true,
  "transcription": "Transcribed text content...",
  "detected_keywords": {
    "keyword1": {
      "detected": true,
      "occurrences": 3,
      "positions": [12, 45, 78]
    },
    "keyword2": {
      "detected": false,
      "occurrences": 0,
      "positions": []
    }
  },
  "duration_seconds": 65.21,
  "processing_time_seconds": 13.12,
  "job_id": "9e0f1a2b-3f7b-8c1d-a2e4-4d5f9e6b7c8d",
  "filename": "recording.mp3",
  "timestamp": "2025-03-06 15:45:30"
}
```

## Architecture Details

### Queue Strategy Pattern

The system implements a Strategy Pattern for message queuing, allowing easy switching between different queue implementations:

- **MQTT**: Default and preferred for pub/sub messaging
- **Redis**: Alternative with support for message history
- **Logging**: Fallback option for development/debugging

The queue implementation can be changed by setting the `QUEUE_TYPE` environment variable.

## Performance Considerations

- The system's performance depends on the Whisper model size and available hardware
- Model size trade-offs:
  - **tiny**: Fastest but least accurate
  - **base**: Good balance for short clips
  - **small**: Recommended default for most use cases
  - **medium**: Higher accuracy but slower
  - **large**: Highest accuracy but significantly slower
- Processing times increase with audio length and model size
- For batch processing of numerous files, consider configuring a higher memory limit
- MPS acceleration on Apple Silicon improves performance significantly

## Supported Audio Formats

The system supports various audio formats including:
- MP3
- WAV
- M4A
- FLAC
- OGG

## Troubleshooting

### Common Issues

1. **API Connection Failure**:
   - Check if the Docker containers are running: `docker-compose ps`
   - Verify the API port is accessible: `curl http://localhost:8000/health`

2. **Out of Memory Errors**:
   - Increase the memory limit in `docker-compose.yaml`
   - Use a smaller Whisper model

3. **Slow Processing**:
   - Consider using a smaller model for faster results
   - Check system resource usage during processing

4. **Queue Connection Issues**:
   - For MQTT: Verify the MQTT broker is running: `docker-compose logs mosquitto`
   - For Redis: Verify Redis is running: `docker-compose logs redis`
   - Check connection parameters in environment variables

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for the speech recognition model
- [FastAPI](https://fastapi.tiangolo.com/) for the API framework
- [MQTT](https://mqtt.org/) and [Eclipse Mosquitto](https://mosquitto.org/) for the primary message queue
- [Redis](https://redis.io/) for the alternative message queue