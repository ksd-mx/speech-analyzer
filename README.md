# Mosque Audio Analysis

A self-hosted voice recognition system for analyzing mosque audio content, built on OpenAI's Whisper model with a lightweight message queue.

## Overview

Mosque Audio Analysis is a containerized service that enables:

- Speech-to-text transcription of audio recordings
- Keyword detection in audio files
- Message queuing for asynchronous result processing
- Easy deployment using Docker

The system provides a RESTful API and a message queue for processing results, making it suitable for batch processing or integration with other systems.

## Features

- **Transcription Service**: Convert audio recordings to text with language detection
- **Keyword Detection**: Search audio for specific phrases or words
- **Message Queue**: Publish results to topics for asynchronous consumption
- **Multiple Model Support**: Choose from different Whisper model sizes based on accuracy needs
- **Hardware Acceleration**: Support for MPS (Metal Performance Shaders) on Apple Silicon
- **Containerized**: Easy deployment with Docker
- **Client Tools**: Python clients for making requests and consuming results

## Architecture

The system consists of:

1. **API Server**: FastAPI application that processes audio files
2. **Redis Queue**: Lightweight message broker for distributing results
3. **Client Tools**: Command-line tools for interacting with the API and queue

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Audio files for analysis (MP3, WAV, etc.)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mosque-audio-analysis.git
   cd mosque-audio-analysis
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Verify the installation:
   ```bash
   python client.py health
   ```

### Usage

#### Transcribing Audio

```bash
python client.py transcribe path/to/recording.mp3
```

#### Detecting Keywords

```bash
python client.py detect path/to/recording.mp3 "adhan,salat,allahu akbar"
```

#### Subscribing to Results

```bash
python subscriber.py subscribe transcriptions
```

#### Viewing Result History

```bash
python subscriber.py history transcriptions
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| WHISPER_MODEL | Whisper model size (tiny, base, small, medium, large) | base |
| CACHE_MODELS | Enable model caching | true |
| REDIS_ENABLED | Enable Redis message queue | true |
| REDIS_URL | Redis connection string | redis://redis:6379/0 |
| UPLOAD_DIR | Directory to store uploaded files | /tmp/whisper_uploads |

### Docker Configuration

Edit the `docker-compose.yaml` file to change resource limits, ports, or other settings.

## Topics and Message Format

### Default Topics

- `transcriptions`: Results from speech-to-text operations
- `keyword_detections`: Results from keyword detection operations

### Message Format

```json
{
  "success": true,
  "job_id": "3f7b8c1d-a2e4-4d5f-9e6b-7c8d9e0f1a2b",
  "text": "Transcribed text content...",
  "language": "en",
  "duration_seconds": 75.5,
  "processing_time_seconds": 12.3,
  "filename": "recording.mp3",
  "timestamp": "2025-02-26 15:30:45"
}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /health | GET | Check service health |
| /transcribe | POST | Transcribe audio file |
| /detect-keywords | POST | Detect keywords in audio file |

## Performance Considerations

- The system performance depends on the Whisper model size and available hardware
- For larger audio files, consider using smaller models
- Processing times increase with audio length and model size

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for the speech recognition model
- [FastAPI](https://fastapi.tiangolo.com/) for the API framework
- [Redis](https://redis.io/) for the message queue