# backend/label_audio_emotions.py
import numpy as np
import pandas as pd

# final emotion labels (8 moods)
EMOTIONS = ["aggressive", "tense", "euphoric", "uplifting", "melancholic", "warm", "dark", "dreamy"]

# normalize values so we can compare them (tempo, volume, etc.)
def _zscore(series: pd.Series) -> pd.Series:
    mu = series.mean()
    sd = series.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mu) / sd


# check if the song sounds more major (happy) or minor (sad)
def _estimate_mode_valence(chroma_row: np.ndarray) -> float:
    major_template = np.array([1,0,0,0,1,0,0,1,0,0,0,0], dtype=float)  # 0,4,7
    minor_template = np.array([1,0,0,1,0,0,0,1,0,0,0,0], dtype=float)  # 0,3,7

    maj_scores, min_scores = [], []
    for k in range(12):  # test all key transpositions
        maj_scores.append(np.dot(chroma_row, np.roll(major_template, k)))
        min_scores.append(np.dot(chroma_row, np.roll(minor_template, k)))

    maj = max(maj_scores)
    minr = max(min_scores)

    # >0 means major (happy), <0 means minor (sad)
    return 0.0 if (maj + minr) == 0 else float((maj - minr) / (maj + minr))


# compute the two emotion axes: valence (happy-sad) and arousal (calm-energetic)
def compute_valence_arousal(df: pd.DataFrame) -> pd.DataFrame:
    # base features
    tempo_z    = _zscore(df["tempo_bpm"])
    rms_z      = _zscore(df["rms_mean"])
    centroid_z = _zscore(df["centroid_mean"])
    rolloff_z  = _zscore(df["rolloff_mean"])
    zcr_z      = _zscore(df["zcr_mean"])
    brightness_z = 0.6 * centroid_z + 0.4 * rolloff_z  # overall brightness

    # check mode (major/minor) using chroma
    chroma_cols = [f"chroma{i}_mean" for i in range(1, 13)]
    chroma_mat = df[chroma_cols].to_numpy(dtype=float)
    chroma_mat = np.where(
        chroma_mat.sum(axis=1, keepdims=True) > 0,
        chroma_mat / chroma_mat.sum(axis=1, keepdims=True),
        chroma_mat
    )
    mode_score = np.array([_estimate_mode_valence(row) for row in chroma_mat])
    mode_z = pd.Series(mode_score, index=df.index)

    # use all MFCCs (sound color)
    mfcc_cols = [c for c in df.columns if c.startswith("mfcc") and c.endswith("_mean")]
    mfcc_z = {c: _zscore(df[c]) for c in mfcc_cols}

    # summarize MFCCs in 3 simple bands
    def _avg(cols):
        cols = [c for c in cols if c in mfcc_z]
        if not cols:
            return pd.Series(np.zeros(len(df)), index=df.index)
        return sum(mfcc_z[c] for c in cols) / float(len(cols))

    mfcc_low_z  = _avg([f"mfcc{i}_mean" for i in range(1, 6)])     # low = warmth/body
    mfcc_mid_z  = _avg([f"mfcc{i}_mean" for i in range(6, 11)])    # mid = nasal/presence
    mfcc_high_z = _avg([f"mfcc{i}_mean" for i in range(11, 14)])   # high = brightness/edge

    # energy / excitement axis
    arousal = (
        0.40*tempo_z + 0.25*rms_z + 0.20*brightness_z + 0.10*zcr_z
        + 0.04*mfcc_high_z + 0.01*mfcc_mid_z
    )

    # positive vs negative emotion axis
    valence = (
        0.55*mode_z + 0.22*brightness_z
        + 0.06*mfcc_low_z   # warmth
        - 0.08*mfcc_mid_z   # tension
        - 0.05*mfcc_high_z  # harsh brightness
    )

    return pd.DataFrame({"valence": valence, "arousal": arousal}, index=df.index)


# pick an emotion label based on valence/arousal position
def map_to_emotion(valence: float, arousal: float) -> str:
    v, a = valence, arousal

    # clear zones (easy to tell)
    if a > 0.9 and v > 0.4:   return "euphoric"
    if a > 0.9 and v < -0.5:  return "aggressive"
    if a >= 0.3 and v >= 0.35:   return "uplifting"
    if a >= 0.3 and v <= -0.25:  return "tense"
    if a <= -0.35 and v <= -0.35: return "melancholic"
    if a <= -0.35 and v >= 0.2:   return "warm"

    # middle zones (soft colors)
    if -0.35 < a < 0.35 and v <= -0.5:  return "dark"
    if -0.35 < a < 0.25 and -0.2 <= v <= 0.5:  return "dreamy"

    # fallback: find closest mood center
    centers = {
        "euphoric":     (0.70,  1.05),
        "aggressive":   (-0.70, 1.05),
        "uplifting":    (0.55,  0.50),
        "tense":        (-0.45, 0.55),
        "warm":         (0.45, -0.60),
        "melancholic":  (-0.65, -0.70),
        "dark":         (-0.65,  0.00),
        "dreamy":       (0.20, -0.10),
    }
    best = min(
        centers.items(),
        key=lambda kv: (v - kv[1][0])**2 + (a - kv[1][1])**2
    )
    return best[0]


# main function: add valence, arousal and emotion columns to your DataFrame
def label_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    va = compute_valence_arousal(df)
    df = df.copy()
    df["valence"] = va["valence"]
    df["arousal"] = va["arousal"]
    df["emotion"] = [map_to_emotion(v, a) for v, a in zip(df["valence"], df["arousal"])]
    return df
