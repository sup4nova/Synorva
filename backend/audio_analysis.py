# backend/audio_analysis.py

# Take an audio file and extract numbers that describe how it "feels" musically.
# those numbers are then used by label_audio_emotions.py to compute valence and arousal :
# this file converts a WAV or MP3 into a row of ~30 numeric columns.


from pathlib import Path
from dotenv import load_dotenv
import os
import numpy as np
import librosa


load_dotenv()

TARGET_SR = int(os.getenv("TARGET_SR", 22050))
READ_SECONDS = int(os.getenv("READ_SECONDS", 30))

_NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

def _detect_key(y, sr):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    best_score, best_key = -np.inf, 'C'
    for i, note in enumerate(_NOTES):
        rot = np.roll(chroma, -i)
        maj = float(np.corrcoef(rot, _MAJOR)[0, 1])
        minr = float(np.corrcoef(rot, _MINOR)[0, 1])
        if maj > best_score:
            best_score, best_key = maj, note
        if minr > best_score:
            best_score, best_key = minr, note + 'm'
    return best_key

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
        "file": Path(path).name,
        "tempo_bpm": tempo,
        "key": _detect_key(y, sr),
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
