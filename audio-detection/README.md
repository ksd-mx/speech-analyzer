# Audio Keyword Detection System

A simplified keyword detection system for recognizing spoken words or sounds in audio files.

## Project Structure

```
audio_keyword_detector/
├── main.py                  # Main entry point with command-line interface
├── train.py                 # Convenience script for training models
├── detect.py                # Convenience script for detecting keywords
├── feature_extraction.py    # Feature extraction functionality
├── model.py                 # Model training and loading utilities
├── detection.py             # Keyword detection functionality
└── utils.py                 # Shared utility functions and constants
```

## Installation

1. Clone this repository
2. Install required packages:
   ```
   pip install numpy librosa scikit-learn joblib
   ```

## Usage

### Training a model

To train a model, organize your audio samples in folders, with each folder named after the keyword:

```
training_data/
  hello/
    sample1.wav
    sample2.wav
  goodbye/
    sample1.wav
    sample2.wav
```

Then run:

```bash
python train.py training_data --model my_model.pkl
```

### Detecting keywords

To detect keywords in an audio file:

```bash
python detect.py my_audio.wav --model my_model.pkl
```

To look for a specific keyword:

```bash
python detect.py my_audio.wav --model my_model.pkl --keyword hello --threshold 0.7
```

## Advanced Usage

For more advanced options, use the main script:

```bash
python main.py --train training_data --model my_model.pkl
python main.py --detect my_audio.wav --model my_model.pkl --keyword hello --threshold 0.7
```

## How It Works

1. **Feature Extraction**: The system extracts audio features like MFCCs, spectral centroid, and energy
2. **Training**: A Random Forest classifier learns to recognize patterns for each keyword
3. **Detection**: New audio is analyzed and compared against the trained model to find matches

## Contributing

Feel free to submit issues and pull requests!