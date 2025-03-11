"""
Tests for the detection strategies.
"""

import os
import unittest
import tempfile
import numpy as np
from unittest.mock import patch, MagicMock

# Import detector components
from core.detection.base import BaseDetector
from core.detection.whisper import WhisperDetector
from core.detection.classifier import ClassifierDetector
from core.detector_factory import DetectorFactory


class TestBaseDetector(unittest.TestCase):
    """Test cases for the BaseDetector."""
    
    def test_format_result(self):
        """Test that the format_result method correctly formats detection results."""
        # Create a concrete implementation for testing
        class ConcreteDetector(BaseDetector):
            def detect_keywords(self, audio_path, keywords, threshold):
                pass
                
            def get_supported_params(self):
                return {}
        
        detector = ConcreteDetector()
        
        # Test with empty result
        empty_result = {}
        formatted = detector.format_result(empty_result)
        self.assertIn("detections", formatted)
        self.assertIn("duration_seconds", formatted)
        
        # Test with partial result
        partial_result = {
            "detections": {
                "hello": {
                    "positions": [10, 50]
                }
            }
        }
        formatted = detector.format_result(partial_result)
        self.assertTrue(formatted["detections"]["hello"]["detected"])
        self.assertEqual(formatted["detections"]["hello"]["occurrences"], 2)
        self.assertEqual(formatted["detections"]["hello"]["positions"], [10, 50])
        self.assertEqual(formatted["detections"]["hello"]["confidence_scores"], [])


class TestDetectorFactory(unittest.TestCase):
    """Test cases for the DetectorFactory."""
    
    def test_create_whisper_detector(self):
        """Test creation of WhisperDetector."""
        with patch('core.detection.whisper.WhisperDetector.__init__', return_value=None) as mock_init:
            detector = DetectorFactory.create_detector("whisper")
            self.assertIsInstance(detector, WhisperDetector)
            mock_init.assert_called_once()
    
    def test_create_classifier_detector(self):
        """Test creation of ClassifierDetector."""
        with patch('core.detection.classifier.ClassifierDetector.__init__', return_value=None) as mock_init:
            detector = DetectorFactory.create_detector("classifier", model_path="test_model.pkl")
            self.assertIsInstance(detector, ClassifierDetector)
            mock_init.assert_called_once_with(model_path="test_model.pkl")
    
    def test_invalid_strategy(self):
        """Test that an invalid strategy raises ValueError."""
        with self.assertRaises(ValueError):
            DetectorFactory.create_detector("invalid_strategy")


class TestWhisperDetector(unittest.TestCase):
    """Test cases for the WhisperDetector."""
    
    @patch('core.detection.whisper.WhisperDetector._load_model')
    def test_init(self, mock_load_model):
        """Test initialization of WhisperDetector."""
        detector = WhisperDetector(model_size="tiny")
        self.assertEqual(detector.model_size, "tiny")
        mock_load_model.assert_called_once()
    
    @patch('core.detection.whisper.WhisperDetector._load_model')
    def test_detect_keywords_in_text(self, mock_load_model):
        """Test keyword detection in text."""
        detector = WhisperDetector()
        
        # Test with keywords present
        text = "Hello world, this is a test. Hello again!"
        keywords = ["hello", "test"]
        results = detector._detect_keywords_in_text(text, keywords)
        
        self.assertTrue(results["hello"]["detected"])
        self.assertEqual(results["hello"]["occurrences"], 2)
        self.assertEqual(len(results["hello"]["positions"]), 2)
        
        self.assertTrue(results["test"]["detected"])
        self.assertEqual(results["test"]["occurrences"], 1)
        self.assertEqual(len(results["test"]["positions"]), 1)
        
        # Test with keywords absent
        text = "This text does not contain any of the keywords."
        keywords = ["hello", "world"]
        results = detector._detect_keywords_in_text(text, keywords)
        
        self.assertFalse(results["hello"]["detected"])
        self.assertEqual(results["hello"]["occurrences"], 0)
        self.assertEqual(results["hello"]["positions"], [])
        
        self.assertFalse(results["world"]["detected"])
        self.assertEqual(results["world"]["occurrences"], 0)
        self.assertEqual(results["world"]["positions"], [])


class TestClassifierDetector(unittest.TestCase):
    """Test cases for the ClassifierDetector."""
    
    @patch('core.detection.classifier.ClassifierDetector._load_model')
    @patch('core.detection.classifier.ClassifierDetector._find_default_model')
    def test_init_with_model_path(self, mock_find_default, mock_load_model):
        """Test initialization with model path."""
        detector = ClassifierDetector(model_path="test_model.pkl")
        self.assertEqual(detector.model_path, "test_model.pkl")
        mock_load_model.assert_called_once()
        mock_find_default.assert_not_called()
    
    @patch('core.detection.classifier.ClassifierDetector._load_model')
    @patch('core.detection.classifier.ClassifierDetector._find_default_model', return_value="default_model.pkl")
    def test_init_without_model_path(self, mock_find_default, mock_load_model):
        """Test initialization without model path."""
        detector = ClassifierDetector()
        self.assertEqual(detector.model_path, "default_model.pkl")
        mock_find_default.assert_called_once()
        mock_load_model.assert_called_once()


if __name__ == '__main__':
    unittest.main()