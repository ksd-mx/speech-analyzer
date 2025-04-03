#!/usr/bin/env python3
"""
Script to compare performance between Whisper and VOSK detectors
"""

import argparse
import time
from pathlib import Path
from core.detector_factory import DetectorFactory

def compare_detectors(audio_path: str, keywords: list):
    """Compare detection performance between Whisper and VOSK"""
    print(f"\nComparing detectors on file: {audio_path}")
    print(f"Keywords: {', '.join(keywords)}\n")
    
    # Test Whisper
    print("=== Testing Whisper ===")
    whisper_start = time.time()
    whisper = DetectorFactory.create_detector("whisper", model_size="small")
    whisper_result = whisper.detect_keywords(audio_path, keywords, threshold=0.5)
    whisper_time = time.time() - whisper_start
    
    print(f"Processing time: {whisper_time:.2f}s")
    print(f"Transcription: {whisper_result.get('transcription')}")
    print("Detections:")
    for kw, data in whisper_result.get('detections', {}).items():
        print(f"  {kw}: {data.get('detected')} (confidence: {data.get('confidence_scores')})")
    
    # Test VOSK
    print("\n=== Testing VOSK ===")
    vosk_start = time.time()
    vosk = DetectorFactory.create_detector("vosk")
    vosk_result = vosk.detect_keywords(audio_path, keywords, threshold=0.5)
    vosk_time = time.time() - vosk_start
    
    print(f"Processing time: {vosk_time:.2f}s")
    print(f"Transcription: {vosk_result.get('transcription')}")
    print("Detections:")
    for kw, data in vosk_result.get('detections', {}).items():
        print(f"  {kw}: {data.get('detected')} (confidence: {data.get('confidence_scores')})")
    
    # Summary
    print("\n=== Summary ===")
    print(f"Whisper time: {whisper_time:.2f}s")
    print(f"VOSK time: {vosk_time:.2f}s")
    print(f"Speed difference: {abs(whisper_time-vosk_time):.2f}s ({'Whisper' if whisper_time > vosk_time else 'VOSK'} is faster)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare Whisper and VOSK detectors")
    parser.add_argument("audio_file", help="Path to audio file to test")
    parser.add_argument("keywords", help="Comma-separated list of keywords to detect")
    args = parser.parse_args()
    
    compare_detectors(
        audio_path=args.audio_file,
        keywords=[k.strip() for k in args.keywords.split(",")]
    )