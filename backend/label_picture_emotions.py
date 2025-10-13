# backend/label_picture_emotions.py
import numpy as np
import pandas as pd

# Étiquettes finales (mêmes catégories que pour l'audio, pour cohérence multimodale)
EMOTIONS = ["aggressive", "tense", "euphoric", "uplifting", 
            "melancholic", "warm", "dark", "dreamy"]

def _z(series: pd.Series) -> pd.Series:
    mu = series.mean()
    sd = series.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mu) / sd

def compute_valence_arousal_images(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les deux axes émotionnels pour des images selon des caractéristiques visuelles.
    - Valence : agréable ↔ désagréable
    - Arousal : calme ↔ énergique
    """
    # Normalisation (z-score)
    bright_z   = _z(df["brightness_mean"])
    sat_z      = _z(df["saturation_mean"])
    contrast_z = _z(df["contrast_std"])
    color_z    = _z(df["colorfulness"])
    warm_z     = _z(df["warmth"])
    sharp_z    = _z(df["sharpness"])
    edge_z     = _z(df["edge_density"])
    faces_z    = _z(df["faces_ratio"])

    # 🔹 AROUSAL = intensité visuelle / énergie de la scène
    arousal = (
        0.28 * contrast_z +
        0.22 * edge_z +
        0.18 * sharp_z +
        0.18 * color_z +
        0.10 * sat_z +
        0.04 * bright_z
    )

    # 🔹 VALENCE = chaleur et positivité perçue
    valence = (
        0.40 * bright_z +
        0.25 * warm_z +
        0.15 * sat_z +
        0.10 * faces_z +
        0.10 * color_z -
        0.05 * edge_z  # trop de lignes/détail peut évoquer tension
    )

    return pd.DataFrame({"valence": valence, "arousal": arousal}, index=df.index)

def map_to_emotion(v: float, a: float) -> str:
    """Mappe la position (valence, arousal) sur une émotion discrète."""
    if a > 0.9 and v > 0.4:   return "euphoric"
    if a > 0.9 and v < -0.5:  return "aggressive"
    if a >= 0.3 and v >= 0.35: return "uplifting"
    if a >= 0.3 and v <= -0.25: return "tense"
    if a <= -0.35 and v <= -0.35: return "melancholic"
    if a <= -0.35 and v >= 0.2:   return "warm"
    if -0.35 < a < 0.35 and v <= -0.5: return "dark"
    if -0.35 < a < 0.25 and -0.2 <= v <= 0.5: return "dreamy"

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
    best = min(centers.items(), key=lambda kv: (v - kv[1][0])**2 + (a - kv[1][1])**2)
    return best[0]

def label_image_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute valence/arousal/emotion au DataFrame d’images."""
    va = compute_valence_arousal_images(df)
    labeled = df.copy()
    labeled["valence"] = va["valence"]
    labeled["arousal"] = va["arousal"]
    labeled["emotion"] = [
        map_to_emotion(v, a) for v, a in zip(labeled["valence"], labeled["arousal"])
    ]
    return labeled