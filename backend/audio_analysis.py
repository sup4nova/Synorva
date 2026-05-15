# backend/audio_analysis.py
from pathlib import Path
from dotenv import load_dotenv
import os
import numpy as np
import librosa


load_dotenv()

TARGET_SR = int(os.getenv("TARGET_SR", 22050))
READ_SECONDS = int(os.getenv("READ_SECONDS", 30))

def extract_audio_features(path):
    """analyze an audio file and return a dictionary of extracted features"""
    y, sr = librosa.load(path, sr=TARGET_SR, mono=True, duration=READ_SECONDS)

    zcr = np.mean(librosa.feature.zero_crossing_rate(y=y))
    rms = np.mean(librosa.feature.rms(y=y))
    centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))
    tempo = float(librosa.beat.tempo(y=y, sr=sr, aggregate=np.median))
    mfcc_means = np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13), axis=1)
    chroma_means = np.mean(librosa.feature.chroma_stft(y=y, sr=sr), axis=1)

    features = {
        "tempo_bpm": tempo,
        "zcr_mean": zcr,
        "rms_mean": rms,
        "centroid_mean": centroid,
        "rolloff_mean": rolloff,
    }

    for i, v in enumerate(mfcc_means, 1):
        features[f"mfcc{i}_mean"] = v
    for i, v in enumerate(chroma_means, 1):
        features[f"chroma{i}_mean"] = v

    return features
