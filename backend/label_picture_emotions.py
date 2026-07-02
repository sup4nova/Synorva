# backend/label_picture_emotions.py
# Converts visual image features into valence, arousal, and emotion labels.
# Called by build_picture_dataset.py (bulk) and main.py (on-demand via label_image_dataframe).
# Mirror of label_audio_emotions.py - same 8 emotions, same (valence, arousal) space,
# different input features (visual instead of acoustic).

import numpy as np
import pandas as pd

# Same 8 emotion categories as the audio pipeline - ensures multimodal consistency
EMOTIONS = ["aggressive", "tense", "euphoric", "uplifting",
            "melancholic", "warm", "dark", "dreamy"]


# --- Normalisation ---

def _z(series: pd.Series) -> pd.Series:
    """
    Z-score standardisation: subtract mean, divide by std.
    Returns a zero series if std is 0 (constant column) to avoid NaN propagation.
    """
    mu = series.mean()
    sd = series.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mu) / sd


# --- Valence / Arousal computation ---

def compute_valence_arousal_images(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive valence and arousal from visual features using weighted heuristics.

    Arousal (calm <-> energetic):
      Driven by visual intensity: contrast, edge density, sharpness, colorfulness.
      High-contrast, sharp, detailed images feel energetic and stimulating.

    Valence (sad <-> happy):
      Driven by warmth and positivity: brightness, warm hues, saturation, faces.
      Bright, warm, saturated images with human presence feel pleasant.
      High edge density slightly reduces valence (visual busyness = tension).

    All features are z-scored first so weights operate on a common scale.
    """
    # Z-score all input features
    bright_z   = _z(df["brightness_mean"])   # how light/dark overall (HSV value)
    sat_z      = _z(df["saturation_mean"])   # color intensity
    contrast_z = _z(df["contrast_std"])      # RMS of per-channel RGB std
    color_z    = _z(df["colorfulness"])      # Hasler-Susstrunk metric
    warm_z     = _z(df["warmth"])            # warm hue fraction minus cool hue fraction
    sharp_z    = _z(df["sharpness"])         # Laplacian variance (focus quality)
    edge_z     = _z(df["edge_density"])      # Canny edge pixel ratio
    faces_z    = _z(df["faces_ratio"])       # fraction of image area covered by faces

    # Arousal: visual energy / scene intensity
    arousal = (
        0.28 * contrast_z   # high contrast = visually striking
      + 0.22 * edge_z       # busy edges = complex, stimulating
      + 0.18 * sharp_z      # sharp focus = attention-grabbing
      + 0.18 * color_z      # vivid palette = energising
      + 0.10 * sat_z        # saturated colors = lively
      + 0.04 * bright_z     # brightness has minor effect on energy
    )

    # Valence: perceived warmth and positivity
    valence = (
        0.40 * bright_z     # bright images feel cheerful (strongest signal)
      + 0.25 * warm_z       # warm hues (red/orange) feel welcoming
      + 0.15 * sat_z        # rich color reads as positive
      + 0.10 * faces_z      # human faces add social warmth
      + 0.10 * color_z      # colorful = lively = slightly happier
      - 0.05 * edge_z       # excessive detail / busy edges read as tense
    )

    return pd.DataFrame({"valence": valence, "arousal": arousal}, index=df.index)


# --- Emotion mapping ---

def map_to_emotion(v: float, a: float) -> str:
    """
    Map a (valence, arousal) coordinate to one of 8 emotion labels.

    Uses hard threshold zones for clear cases, nearest-centroid fallback otherwise.
    Identical to the audio version - both pipelines share the same emotion space.

    Emotion space layout:
                    HIGH AROUSAL
         aggressive  |  euphoric
    SAD -------------+------------- HAPPY
         melancholic  |  warm
                    LOW AROUSAL
    """
    # Hard threshold zones (unambiguous regions)
    if a >  0.9 and v >  0.4:    return "euphoric"     # very energetic + very happy
    if a >  0.9 and v < -0.5:    return "aggressive"   # very energetic + very negative
    if a >= 0.3 and v >=  0.35:  return "uplifting"    # energetic + positive
    if a >= 0.3 and v <= -0.25:  return "tense"        # energetic + negative
    if a <= -0.35 and v <= -0.35: return "melancholic" # calm + sad
    if a <= -0.35 and v >=  0.2:  return "warm"        # calm + happy

    # Soft middle zones
    if -0.35 < a <  0.35 and v <= -0.5:              return "dark"    # neutral energy + very sad/bleak
    if -0.35 < a <  0.25 and -0.2 <= v <= 0.5:       return "dreamy"  # low-mid energy + neutral/warm

    # Fallback: nearest emotion centroid
    centers = {
        "euphoric":    ( 0.70,  1.05),
        "aggressive":  (-0.70,  1.05),
        "uplifting":   ( 0.55,  0.50),
        "tense":       (-0.45,  0.55),
        "warm":        ( 0.45, -0.60),
        "melancholic": (-0.65, -0.70),
        "dark":        (-0.65,  0.00),
        "dreamy":      ( 0.20, -0.10),
    }
    best = min(
        centers.items(),
        key=lambda kv: (v - kv[1][0])**2 + (a - kv[1][1])**2
    )
    return best[0]


# --- Public entry point ---

def label_image_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add valence, arousal, and emotion columns to an image features DataFrame.
    Returns a new DataFrame (original is not modified).
    Called by build_picture_dataset.py after feature extraction.
    """
    va     = compute_valence_arousal_images(df)
    labeled = df.copy()
    labeled["valence"] = va["valence"]
    labeled["arousal"] = va["arousal"]
    labeled["emotion"] = [
        map_to_emotion(v, a) for v, a in zip(labeled["valence"], labeled["arousal"])
    ]
    return labeled
