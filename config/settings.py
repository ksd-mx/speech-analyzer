"""
Configuration settings for the Audio Keyword Detection System.
Loads settings from environment variables with sensible defaults.
"""

import os
from typing import Dict, Any, List, Optional

class Settings:
    """Centralized configuration settings."""
    
    # API Settings
    API_HOST: str = os.environ.get("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.environ.get("API_PORT", "8000"))
    API_DEBUG: bool = os.environ.get("API_DEBUG", "false").lower() == "true"
    
    # File Upload Settings
    UPLOAD_DIR: str = os.environ.get("UPLOAD_DIR", "/tmp/audio_uploads")
    MAX_UPLOAD_SIZE: int = int(os.environ.get("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))  # 50MB default
    ALLOWED_EXTENSIONS: List[str] = ["wav", "mp3", "ogg", "flac"]
    
    # Whisper Settings
    WHISPER_MODEL: str = os.environ.get("WHISPER_MODEL", "base")
    CACHE_MODELS: bool = os.environ.get("CACHE_MODELS", "true").lower() == "true"
    
    # VOSK Settings
    VOSK_MODEL_PATH: str = os.environ.get("VOSK_MODEL_PATH", "models/vosk-model-ar-0.22")
    VOSK_SAMPLE_RATE: int = int(os.environ.get("VOSK_SAMPLE_RATE", "16000"))
    
    # Classifier Settings
    DEFAULT_MODEL_DIR: str = os.environ.get("DEFAULT_MODEL_DIR", "models")
    DEFAULT_THRESHOLD: float = float(os.environ.get("DEFAULT_THRESHOLD", "0.5"))
    
    # Queue Settings
    QUEUE_ENABLED: bool = os.environ.get("QUEUE_ENABLED", "true").lower() == "true"
    QUEUE_TYPE: str = os.environ.get("QUEUE_TYPE", "mqtt").lower()
    DEFAULT_TOPIC: str = os.environ.get("DEFAULT_TOPIC", "keyword_detections")
    
    # Redis Settings
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    
    # MQTT Settings
    MQTT_BROKER_URL: str = os.environ.get("MQTT_BROKER_URL", "localhost")
    MQTT_PORT: int = int(os.environ.get("MQTT_PORT", "1883"))
    MQTT_CLIENT_ID: Optional[str] = os.environ.get("MQTT_CLIENT_ID", None)
    MQTT_USERNAME: Optional[str] = os.environ.get("MQTT_USERNAME", None)
    MQTT_PASSWORD: Optional[str] = os.environ.get("MQTT_PASSWORD", None)
    MQTT_QOS: int = int(os.environ.get("MQTT_QOS", "0"))
    MQTT_RETAIN: bool = os.environ.get("MQTT_RETAIN", "false").lower() == "true"
    
    @classmethod
    def get_queue_config(cls) -> Dict[str, Any]:
        """Get queue configuration dictionary."""
        config = {
            "queue_type": cls.QUEUE_TYPE,
            "enabled": cls.QUEUE_ENABLED
        }
        
        # Redis-specific configuration
        if cls.QUEUE_TYPE == "redis":
            config["redis_url"] = cls.REDIS_URL
        
        # MQTT-specific configuration
        elif cls.QUEUE_TYPE == "mqtt":
            config["broker_url"] = cls.MQTT_BROKER_URL
            config["port"] = cls.MQTT_PORT
            config["client_id"] = cls.MQTT_CLIENT_ID
            config["username"] = cls.MQTT_USERNAME
            config["password"] = cls.MQTT_PASSWORD
            config["qos"] = cls.MQTT_QOS
            config["retain"] = cls.MQTT_RETAIN
        
        return config
    
    @classmethod
    def get_detector_config(cls, strategy: str) -> Dict[str, Any]:
        """Get detector configuration based on strategy."""
        if strategy == "whisper":
            return {
                "model_size": cls.WHISPER_MODEL
            }
        elif strategy == "vosk":
            return {
                "model_path": cls.VOSK_MODEL_PATH,
                "sample_rate": cls.VOSK_SAMPLE_RATE
            }
        elif strategy == "classifier":
            return {
                "model_dir": cls.DEFAULT_MODEL_DIR,
                "threshold": cls.DEFAULT_THRESHOLD
            }
        else:
            return {}

# Create a global settings instance
settings = Settings()