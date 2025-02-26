FROM python:3.9-bullseye

WORKDIR /app

# Install system dependencies including FFmpeg and audio libraries
RUN apt-get update && apt-get install -y \
    ffmpeg \
    portaudio19-dev \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements first
COPY requirements.txt .

# Install dependencies exactly as they are
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create upload directory
RUN mkdir -p /tmp/whisper_uploads

# Environment variables
ENV WHISPER_MODEL=base
ENV UPLOAD_DIR=/tmp/whisper_uploads
ENV CACHE_MODELS=true

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]