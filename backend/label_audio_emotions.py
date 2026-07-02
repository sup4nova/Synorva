# backend/label_audio_emotions.py
# Converts raw acoustic features into valence, arousal, and emotion labels.
# Called by build_audio_dataset.py (bulk) and main.py (on-demand).
# No ML model - pure weighted heuristics on z-scored audio features.

import numpy as np
import pandas as pd

# The 8 emotion categories used across the whole Synorva project
EMOTIONS = ["aggressive", "tense", "euphoric", "uplifting", "melancholic", "warm", "dark", "dreamy"]


# --- Normalisation ---

def _zscore(series: pd.Series) -> pd.Series:
    """
    Standardise a feature column to mean=0, std=1.
    This lets tempo (BPM), loudness (RMS), frequency (Hz), etc.
    be combined with weights without any one scale dominating.
    Returns a zero series if std is 0 (constant column) to avoid NaN.
    """
    mu = series.mean()
    sd = series.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mu) / sd


# --- Mode detection ---

def _estimate_mode_valence(chroma_row: np.ndarray) -> float:
    """
    Estimate whether audio sounds major (happy) or minor (sad) from its chroma vector.

    Strategy: dot-product the 12-bin chroma fingerprint against simplified major and
    minor chord templates, rotated across all 12 keys. The best-matching key wins.

    Major template: root (0), major third (4), fifth (7)
    Minor template: root (0), minor third (3), fifth (7)

    Returns a score in [-1, +1]:
      +1 -> strongly major (happy/bright)
      -1 -> strongly minor (sad/dark)
       0 -> ambiguous / atonal
    """
    major_template = np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0], dtype=float)
    minor_template = np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0], dtype=float)

    maj_scores, min_scores = [], []
    for k in range(12):   # test all 12 key transpositions
        maj_scores.append(np.dot(chroma_row, np.roll(major_template, k)))
        min_scores.append(np.dot(chroma_row, np.roll(minor_template, k)))

    maj  = max(maj_scores)
    minr = max(min_scores)

    # Normalised difference: positive = major-leaning, negative = minor-leaning
    return 0.0 if (maj + minr) == 0 else float((maj - minr) / (maj + minr))


# --- Valence / Arousal computation ---

def compute_valence_arousal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive valence and arousal scores for every row in the features DataFrame.

    Arousal  (calm <-> energetic):
      Weighted sum of tempo, loudness, spectral brightness, ZCR, high MFCC bands.
      Fast + loud + bright + noisy -> high arousal.

    Valence  (sad <-> happy):
      Dominated by major/minor mode, then brightness.
      High mid-MFCC (nasal/harsh texture) pulls valence down.

    All inputs are z-scored first so weights are on a comparable scale.
    """
    # Z-score base features
    tempo_z      = _zscore(df["tempo_bpm"])
    rms_z        = _zscore(df["rms_mean"])
    centroid_z   = _zscore(df["centroid_mean"])
    rolloff_z    = _zscore(df["rolloff_mean"])
    zcr_z        = _zscore(df["zcr_mean"])

    # Combined perceptual brightness: centroid (where energy sits) + rolloff (tail cutoff)
    brightness_z = 0.6 * centroid_z + 0.4 * rolloff_z

    # Mode score from chroma
    chroma_cols = [f"chroma{i}_mean" for i in range(1, 13)]
    chroma_mat  = df[chroma_cols].to_numpy(dtype=float)

    # Normalise each row so the 12 bins sum to 1 (relative pitch-class weights)
    row_sums = chroma_mat.sum(axis=1, keepdims=True)
    chroma_mat = np.where(row_sums > 0, chroma_mat / row_sums, chroma_mat)

    mode_score = np.array([_estimate_mode_valence(row) for row in chroma_mat])
    mode_z     = pd.Series(mode_score, index=df.index)

    # MFCC bands
    # Z-score each MFCC coefficient independently
    mfcc_cols = [c for c in df.columns if c.startswith("mfcc") and c.endswith("_mean")]
    mfcc_z    = {c: _zscore(df[c]) for c in mfcc_cols}

    def _avg(cols):
        """Average z-scored MFCC values across a list of coefficient names."""
        cols = [c for c in cols if c in mfcc_z]
        if not cols:
            return pd.Series(np.zeros(len(df)), index=df.index)
        return sum(mfcc_z[c] for c in cols) / float(len(cols))

    # Low band  (mfcc1-5):  warmth, body - pulls valence slightly positive
    # Mid band  (mfcc6-10): nasal, presence - pulls valence slightly negative (tension)
    # High band (mfcc11-13): shrill brightness - pulls valence negative (harshness)
    mfcc_low_z  = _avg([f"mfcc{i}_mean" for i in range(1,  6)])
    mfcc_mid_z  = _avg([f"mfcc{i}_mean" for i in range(6,  11)])
    mfcc_high_z = _avg([f"mfcc{i}_mean" for i in range(11, 14)])

    # Weighted combination
    arousal = (
        0.40 * tempo_z       # fast tempo = energetic
      + 0.25 * rms_z         # loud = energetic
      + 0.20 * brightness_z  # bright spectrum = stimulating
      + 0.10 * zcr_z         # noisy/percussive = energetic
      + 0.04 * mfcc_high_z   # harsh texture adds a little energy
      + 0.01 * mfcc_mid_z
    )

    valence = (
        0.55 * mode_z        # major key is the strongest happiness signal
      + 0.22 * brightness_z  # bright spectrum reads as cheerful
      + 0.06 * mfcc_low_z    # warm body adds slight positivity
      - 0.08 * mfcc_mid_z    # nasal tension reduces happiness
      - 0.05 * mfcc_high_z   # harsh highs reduce happiness
    )

    return pd.DataFrame({"valence": valence, "arousal": arousal}, index=df.index)


# --- Emotion mapping ---

def map_to_emotion(valence: float, arousal: float) -> str:
    """
    Map a (valence, arousal) point to one of 8 emotion labels.

    Uses hard threshold zones for clear cases, then falls back to
    nearest-centroid assignment for ambiguous middle-ground values.

    Emotion space layout (approximate):
                    HIGH AROUSAL
         aggressive  |  euphoric
    SAD -------------|------------- HAPPY
         melancholic  |  warm
                    LOW AROUSAL
    """
    v, a = valence, arousal

    # Clear-cut zones
    if a > 0.9  and v >  0.4:   return "euphoric"     # very energetic + happy
    if a > 0.9  and v < -0.5:   return "aggressive"   # very energetic + angry
    if a >= 0.3 and v >=  0.35: return "uplifting"    # energetic + positive
    if a >= 0.3 and v <= -0.25: return "tense"        # energetic + negative
    if a <= -0.35 and v <= -0.35: return "melancholic" # calm + sad
    if a <= -0.35 and v >=  0.2:  return "warm"       # calm + happy

    # Middle zones
    if -0.35 < a < 0.35  and v <= -0.5:              return "dark"    # neutral energy + very sad
    if -0.35 < a < 0.25  and -0.2 <= v <= 0.5:       return "dreamy"  # low-mid energy + neutral/warm

    # Fallback: nearest centroid
    # For points that fall between zones, find the closest emotion center
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

def label_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add valence, arousal, and emotion columns to an audio features DataFrame.
    Returns a new DataFrame (original is not modified).
    """
    va = compute_valence_arousal(df)
    df = df.copy()
    df["valence"] = va["valence"]
    df["arousal"]  = va["arousal"]
    df["emotion"]  = [map_to_emotion(v, a) for v, a in zip(df["valence"], df["arousal"])]
    return df