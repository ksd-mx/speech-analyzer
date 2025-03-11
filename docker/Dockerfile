FROM python:3.9-bullseye

# Add build arguments for proxy settings
ARG http_proxy
ARG https_proxy
ARG HTTP_PROXY
ARG HTTPS_PROXY

# Set environment variables if provided
ENV http_proxy=${http_proxy}
ENV https_proxy=${https_proxy}
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}

# Configure apt to use proxy if provided
RUN if [ ! -z "${http_proxy}" ]; then \
    echo "Acquire::http::Proxy \"${http_proxy}\";" > /etc/apt/apt.conf.d/proxy.conf && \
    echo "Acquire::https::Proxy \"${https_proxy}\";" >> /etc/apt/apt.conf.d/proxy.conf; \
    fi

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

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for uploads, models, etc.
RUN mkdir -p /tmp/audio_uploads
RUN mkdir -p /app/models

# Set working directory for importing modules
ENV PYTHONPATH=/app

# Copy application code
COPY . /app/

# Environment variables
ENV WHISPER_MODEL=small
ENV UPLOAD_DIR=/tmp/audio_uploads
ENV QUEUE_TYPE=mqtt
ENV QUEUE_ENABLED=true

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]