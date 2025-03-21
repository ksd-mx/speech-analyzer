"""
Tests for the API endpoints.
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import UploadFile

# Import API components
from api.app import app
from api.schemas.models import KeywordDetectionResponse, KeywordDetectionResult


class TestAPI(unittest.TestCase):
    """Test cases for the API endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)
        self.assertIn("api", data)
    
    @patch('api.routers.detection.DetectorFactory.create_detector')
    @patch('api.routers.detection.os.makedirs')
    @patch('api.routers.detection.open')
    def test_detect_keywords(self, mock_open, mock_makedirs, mock_create_detector):
        """Test the detect keywords endpoint."""
        # Mock detector
        mock_detector = MagicMock()
        mock_detector.detect_keywords.return_value = {
            "transcription": "Hello world test",
            "duration_seconds": 1.5,
            "detections": {
                "hello": {
                    "detected": True,
                    "occurrences": 1,
                    "positions": [0],
                    "confidence_scores": [0.95]
                },
                "test": {
                    "detected": True,
                    "occurrences": 1,
                    "positions": [12],
                    "confidence_scores": [0.85]
                }
            }
        }
        mock_create_detector.return_value = mock_detector
        
        # Create test file
        file_content = b"mock audio content"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.wav"
        
        # Prepare form data
        form_data = {
            "strategy": "whisper",
            "keywords": "hello,test",
            "threshold": "0.5"
        }
        
        # Mock file reading
        mock_open.return_value.__enter__.return_value.write.return_value = None
        
        # Make request
        with patch('api.routers.detection.QueueManager.publish', return_value=True):
            response = self.client.post(
                "/keywords/detect",
                files={"file": ("test.wav", file_content)},
                data=form_data
            )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["strategy"], "whisper")
        self.assertEqual(data["transcription"], "Hello world test")
        self.assertEqual(data["duration_seconds"], 1.5)
        self.assertEqual(len(data["detections"]), 2)
        
        # Verify keywords in response
        keywords_in_response = [d["keyword"] for d in data["detections"]]
        self.assertIn("hello", keywords_in_response)
        self.assertIn("test", keywords_in_response)
        
        # Verify detector was called correctly
        mock_detector.detect_keywords.assert_called_once()
        call_args = mock_detector.detect_keywords.call_args[1]
        self.assertIn("audio_path", call_args)
        self.assertEqual(call_args["keywords"], ["hello", "test"])
        self.assertEqual(call_args["threshold"], 0.5)
    
    @patch('api.routers.detection.DetectorFactory.create_detector')
    @patch('api.routers.detection.os.makedirs')
    @patch('api.routers.detection.open')
    def test_detect_keywords_with_metadata(self, mock_open, mock_makedirs, mock_create_detector):
        """Test the detect keywords endpoint with metadata."""
        # Mock detector
        mock_detector = MagicMock()
        mock_detector.detect_keywords.return_value = {
            "transcription": "Hello world test",
            "duration_seconds": 1.5,
            "detections": {
                "hello": {
                    "detected": True,
                    "occurrences": 1,
                    "positions": [0],
                    "confidence_scores": [0.95]
                }
            }
        }
        mock_create_detector.return_value = mock_detector
        
        # Create test file
        file_content = b"mock audio content"
        
        # Prepare metadata
        test_metadata = {
            "timestamp": "2025-03-21T12:00:00Z",
            "framerate": 30,
            "source": "camera1",
            "output_path": "/path/to/save/results"
        }
        
        # Prepare form data with metadata
        form_data = {
            "strategy": "whisper",
            "keywords": "hello",
            "threshold": "0.5",
            "metadata": json.dumps(test_metadata)  # Convert to JSON string
        }
        
        # Mock file reading
        mock_open.return_value.__enter__.return_value.write.return_value = None
        
        # Make request
        with patch('api.routers.detection.QueueManager.publish', return_value=True):
            response = self.client.post(
                "/keywords/detect",
                files={"file": ("test.wav", file_content)},
                data=form_data
            )
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        
        # Verify metadata was preserved
        self.assertIn("metadata", data)
        self.assertEqual(data["metadata"]["timestamp"], "2025-03-21T12:00:00Z")
        self.assertEqual(data["metadata"]["framerate"], 30)
        self.assertEqual(data["metadata"]["source"], "camera1")
        self.assertEqual(data["metadata"]["output_path"], "/path/to/save/results")
    
    def test_list_strategies(self):
        """Test the list strategies endpoint."""
        with patch('api.routers.detection.DetectorFactory.list_available_strategies') as mock_list:
            mock_list.return_value = {
                "whisper": {
                    "description": "Uses Whisper speech-to-text for keyword detection",
                    "models": ["tiny", "base", "small"]
                },
                "classifier": {
                    "description": "Uses a trained classifier for direct audio keyword detection",
                    "models": ["keyword_model.pkl"]
                }
            }
            
            response = self.client.get("/keywords/strategies")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("whisper", data)
            self.assertIn("classifier", data)
            self.assertIn("models", data["whisper"])
            self.assertIn("models", data["classifier"])


if __name__ == '__main__':
    unittest.main()