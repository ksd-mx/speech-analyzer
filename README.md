# Audio Keyword Detection System

A powerful, flexible system for detecting keywords in audio recordings using multiple detection strategies. This system can identify specific keywords in audio files, providing information about occurrences, positions, and confidence levels.

![Banner](https://via.placeholder.com/1200x300/4A90E2/FFFFFF?text=Audio+Keyword+Detection+System)

## Features

- **Multiple Detection Strategies**: 
  - **Whisper-based detection**: Utilizes OpenAI's Whisper model for speech-to-text transcription
  - **ML Classifier-based detection**: Direct audio fingerprinting for keyword identification
  
- **Unified API**: Single interface for all detection methods

- **Flexible Deployment**: Run as a standalone CLI tool or as a REST API service

- **Distributed Architecture**: Queue-based result distribution using MQTT or Redis

- **Detailed Analytics**: Information about keyword occurrences, positions, and confidence levels

- **Built for Scale**: Docker ready with optimized resource usage

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Training Models](#training-models)
  - [Command Line Interface](#command-line-interface)
  - [API Usage](#api-usage)
  - [Docker Deployment](#docker-deployment)
- [Architecture](#architecture)
- [Reference](#reference)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites

- Python 3.9 or later
- FFmpeg (for audio processing)
- Redis (optional, for Redis queue strategy)
- MQTT broker (optional, for MQTT queue strategy)

### Setup

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/audio-detection-system.git
cd audio-detection-system
```

2. **Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

## Quick Start

Here's how to quickly get started with the audio keyword detection system:

### Train a Model

```bash
# Train a classifier model using a directory of audio samples
python -m cli.train training_data --model models/keyword_model.pkl
```

### Detect Keywords

```bash
# Using classifier strategy
python -m cli.detect path/to/audio.wav --keywords "hello,world" --strategy classifier --model models/keyword_model.pkl

# Using Whisper strategy
python -m cli.detect path/to/audio.wav --keywords "hello,world" --strategy whisper
```

### Start the API Server

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

### Use the API

```bash
curl -X POST http://localhost:8000/keywords/detect \
  -F "file=@path/to/audio.wav" \
  -F "strategy=whisper" \
  -F "keywords=hello,world"
```

## Usage

### Training Models

The system can be trained to recognize specific keywords using a directory structure where each subdirectory represents a keyword class:

```
training_data/
├── keyword1/
│   ├── sample1.wav
│   ├── sample2.wav
│   └── ...
├── keyword2/
│   ├── sample1.wav
│   ├── sample2.wav
│   └── ...
└── negative/
    ├── sample1.wav
    ├── sample2.wav
    └── ...
```

Train a model with:

```bash
python -m cli.train training_data --model models/my_model.pkl
```

This extracts features from audio samples and trains a random forest classifier.

### Command Line Interface

#### Detect Keywords in Audio Files

```bash
# Basic usage
python -m cli.detect audio_file.wav --keywords "word1,word2" --strategy whisper

# With classifier strategy and a trained model
python -m cli.detect audio_file.wav --keywords "word1,word2" --strategy classifier --model models/my_model.pkl

# Adjust confidence threshold
python -m cli.detect audio_file.wav --keywords "word1,word2" --threshold 0.7
```

#### Client Tool for API Interaction

```bash
# Check API health
python -m cli.client health

# List available detection strategies
python -m cli.client strategies

# Detect keywords using the API
python -m cli.client detect audio_file.wav "word1,word2" --strategy whisper

# Subscribe to detection results
python -m cli.client subscribe keyword_detections
```

### API Usage

#### Start the API Server

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

#### API Endpoints

- `GET /health`: Health check endpoint
- `GET /keywords/strategies`: List available detection strategies
- `POST /keywords/detect`: Detect keywords in an audio file

#### Example API Request

```bash
curl -X POST http://localhost:8000/keywords/detect \
  -F "file=@audio_file.wav" \
  -F "strategy=whisper" \
  -F "keywords=word1,word2" \
  -F "threshold=0.6" \
  -F "topic=my_custom_topic"
```

#### Example API Response

```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "strategy": "whisper",
  "transcription": "This is an example transcription with word1 and word2 in it.",
  "detections": [
    {
      "keyword": "word1",
      "detected": true,
      "occurrences": 1,
      "positions": [27],
      "confidence_scores": [0.95]
    },
    {
      "keyword": "word2",
      "detected": true,
      "occurrences": 1, 
      "positions": [37],
      "confidence_scores": [0.92]
    }
  ],
  "duration_seconds": 3.45,
  "processing_time_seconds": 1.23
}
```

### Docker Deployment

The system is Docker-ready and can be deployed using Docker Compose:

```bash
# Start all services
cd docker
docker-compose up -d

# Or use the provided script
./scripts/run.sh
```

The Docker setup includes:
- The Audio Detection API service
- Redis for queue management (optional)
- Mosquitto MQTT broker for message distribution (optional)

## Architecture

The system is built using the strategy pattern to provide a unified interface for different detection approaches:

```
                 +---------------------+
                 |  DetectorFactory    |
                 +---------------------+
                 | create_detector()   |
                 +----------+----------+
                            |
                            v
              +-------------+-------------+
              |   AudioKeywordDetector   |
              +-------------------------+
              | detect_keywords()       |
              +-------------+-----------+
                            |
                            |
          +----------------+-----------------+
          |                                  |
+---------v-----------+          +-----------v---------+
| WhisperDetector     |          | ClassifierDetector  |
+---------------------+          +---------------------+
| detect_keywords()   |          | detect_keywords()   |
+---------------------+          +---------------------+
```

### Directory Structure

```
audio-detection-system/
├── api/                    # FastAPI application
├── cli/                    # Command-line interface
├── config/                 # Configuration management
├── core/                   # Core detection logic
│   └── detection/          # Detection strategies
├── docker/                 # Docker configuration
├── models/                 # Trained model storage
├── queueing/               # Queue management
├── scripts/                # Utility scripts
└── tests/                  # Unit and integration tests
```

## Reference

### Detection Strategies

#### Whisper Strategy

Uses OpenAI's Whisper model to transcribe audio and then perform text search for keywords. Advantages:
- High accuracy for transcription
- Can detect keywords in context
- Works with any vocabulary

#### Classifier Strategy

Uses a trained machine learning model to detect keywords directly from audio features. Advantages:
- Faster processing
- Works offline
- Better for short, specific keywords
- Lower resource usage

### Configuration Options

Configuration can be set using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | API host | 0.0.0.0 |
| `API_PORT` | API port | 8000 |
| `WHISPER_MODEL` | Whisper model size | base |
| `QUEUE_TYPE` | Queue strategy (mqtt, redis, logging) | mqtt |
| `MQTT_BROKER_URL` | MQTT broker URL | localhost |
| `REDIS_URL` | Redis URL | redis://redis:6379/0 |

See `config/settings.py` for a complete list of options.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.