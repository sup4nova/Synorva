# backend/audio_analysis.py
# Extracts acoustic features from an audio file.
# Called by build_audio_dataset.py for every sample in data/raw_audio/.
# Output feeds label_audio_emotions.py → audio_features.csv

from pathlib import Path
from dotenv import load_dotenv
import os
import numpy as np
import librosa


load_dotenv()

# Audio load settings — overridable via .env
TARGET_SR = int(os.getenv("TARGET_SR", 22050))    # sample rate (Hz)
READ_SECONDS = int(os.getenv("READ_SECONDS", 30)) # max duration read per file


def extract_audio_features(path):
    # Load audio as mono, capped at READ_SECONDS to avoid loading full tracks
    y, sr = librosa.load(path, sr=TARGET_SR, mono=True, duration=READ_SECONDS)

    zcr      = np.mean(librosa.feature.zero_crossing_rate(y=y))               # noisiness / brightness proxy
    rms      = np.mean(librosa.feature.rms(y=y))                              # average loudness / energy
    centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))         # perceived brightness (Hz)
    rolloff  = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))          # frequency below which 85% energy sits
    tempo    = float(librosa.beat.tempo(y=y, sr=sr, aggregate=np.median))     # BPM

    # Timbre fingerprint — 13 coefficients describing the "color" of the sound
    mfcc_means   = np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13), axis=1)

    # Pitch class energy — 12 values (C, C#, D … B), used for major/minor mode detection
    chroma_means = np.mean(librosa.feature.chroma_stft(y=y, sr=sr), axis=1)

    features = {
        # NOTE: "file" key is set by the caller (build_audio_dataset) as the
        # relative path from AUDIO_DIR so subdirectory names are preserved.
        "tempo_bpm":      tempo,
        "zcr_mean":       zcr,
        "rms_mean":       rms,
        "centroid_mean":  centroid,
        "rolloff_mean":   rolloff,
    }

    # Flatten arrays into named columns: mfcc1_mean … mfcc13_mean
    for i, v in enumerate(mfcc_means, 1):
        features[f"mfcc{i}_mean"] = v

    # Flatten arrays into named columns: chroma1_mean … chroma12_mean
    for i, v in enumerate(chroma_means, 1):
        features[f"chroma{i}_mean"] = v

    return features
