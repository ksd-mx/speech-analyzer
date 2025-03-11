"""
Detection strategies for audio keyword detection
"""

from .base import BaseDetector
from .whisper import WhisperDetector
from .classifier import ClassifierDetector

__all__ = ['BaseDetector', 'WhisperDetector', 'ClassifierDetector']