# backend/image_analysis.py
# Extracts visual features from an image and predicts valence/arousal.
# Called by:
#   - build_picture_dataset.py  -> bulk feature extraction for training
#   - main.py (/api/analyze-image, /api/build-track) -> per-upload prediction

from pathlib import Path
import numpy as np
from PIL import Image, ImageStat
import cv2
import joblib
import json

# Lazy-loaded at first call - avoids loading the model at import time
_MODEL = None
_META  = None

# Canonical list of feature columns (same order used during training)
FEATURE_COLS = [
    "width", "height", "aspect_ratio",
    "brightness_mean", "saturation_mean", "contrast_std",
    "colorfulness", "warmth", "edge_density", "sharpness", "faces_ratio",
]


# --- Model loading ---

def _load_regressor():
    """Load the trained valence/arousal regressor + its metadata (once)."""
    global _MODEL, _META
    if _MODEL is None:
        _MODEL = joblib.load("backend/models/picture_valaro.pkl")
        # Meta stores the exact feature column order used during training
        _META  = json.loads(Path("backend/models/picture_valaro.meta.json").read_text(encoding="utf-8"))
    return _MODEL, _META


# --- Public prediction entry point ---

def predict_valaro_from_bgr(img_bgr, file_name=None):
    """
    Predict valence and arousal from a BGR image (OpenCV format).
    Returns: {"valence": float, "arousal": float, "features_used": [...]}
    """
    model, meta = _load_regressor()
    feats = extract_image_features(img_bgr, file_name=file_name)

    # Use the column order saved at training time - order matters for sklearn
    cols = meta["feature_cols"]
    X = np.array([[float(feats[c]) for c in cols]], dtype=float)

    pred = model.predict(X)[0]  # returns [valence, arousal]
    return {"valence": float(pred[0]), "arousal": float(pred[1]), "features_used": cols}


# --- Format helpers ---

def _pil_to_bgr(img):
    """Convert a PIL RGB image to a BGR numpy array (OpenCV format)."""
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


# --- Individual feature extractors ---

def _colorfulness(img_bgr):
    """
    Hasler & Süsstrunk colorfulness metric.
    Combines the spread (std) and shift (mean) of opponent color channels:
      rg = |R - G|       (red-green axis)
      yb = |0.5(R+G) - B| (yellow-blue axis)
    High value -> vivid / saturated palette. Low -> muted / monochrome.
    """
    (B, G, R) = cv2.split(img_bgr.astype("float"))
    rg = np.abs(R - G)
    yb = np.abs(0.5 * (R + G) - B)
    return float(
        np.sqrt(np.std(rg)**2 + np.std(yb)**2) +
        0.3 * np.sqrt(np.mean(rg)**2 + np.mean(yb)**2)
    )


def _warmth_hue(img_bgr):
    """
    Warm/cool hue balance, restricted to non-grey pixels (sat > 0.15, val > 0.15).
    Warm hues: reds/oranges/yellows (0–60°) and pinks/magentas (300–360°).
    Cool hues: blues/cyans (180–260°).
    Returns warm_fraction - cool_fraction: positive = warm, negative = cool.
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    hue = hsv[..., 0] * 2.0        # OpenCV hue is 0–180; scale to 0–360
    sat = hsv[..., 1] / 255.0
    val = hsv[..., 2] / 255.0

    # Ignore grey / near-black pixels (unreliable hue)
    mask = (sat > 0.15) & (val > 0.15)
    if not np.any(mask):
        return 0.0

    h = hue[mask]
    warm = ((h <= 60) | (h >= 300)).mean()
    cold = ((h >= 180) & (h <= 260)).mean()
    return float(warm - cold)


def _edge_density(img_gray):
    """
    Fraction of pixels flagged as edges by Canny (thresholds 100/200).
    High -> busy, complex, energetic image. Low -> calm, open, minimal.
    """
    edges = cv2.Canny(img_gray, 100, 200)
    return float(edges.mean())   # mean of 0/255 map ≈ fraction of edge pixels


def _sharpness_var_laplacian(img_gray):
    """
    Variance of the Laplacian - standard blur/sharpness detector.
    High -> sharp, in-focus. Low -> blurry, soft, dreamy.
    """
    return float(cv2.Laplacian(img_gray, cv2.CV_64F).var())


def _faces_ratio(img_bgr):
    """
    Fraction of image area covered by detected frontal faces (Haar cascade).
    0.0 if no face or if detection fails.
    Useful signal for portrait vs landscape/abstract images.
    """
    try:
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(32, 32))
        if len(faces) == 0:
            return 0.0
        areas = [w * h for (_, _, w, h) in faces]
        return float(sum(areas) / (gray.shape[0] * gray.shape[1]))
    except Exception:
        return 0.0


# --- Main extractor ---

def extract_image_features(img_bgr, file_name: str | None = None):
    """
    Compute all 11 visual features from a BGR image array.
    If file_name is given, it is prepended as the "file" key
    (used by build_picture_dataset.py when writing the CSV).

    Processing steps:
      1. Convert BGR -> RGB -> PIL for PIL-based stats
      2. Resize to max 1024px on the longest side (avoids memory spikes on huge images)
      3. Re-derive BGR/gray/HSV after resize for consistent pixel counts
      4. Compute each feature and return a flat dict
    """
    # Convert from OpenCV BGR to PIL RGB for ImageStat
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(img_rgb).convert("RGB")

    # Cap resolution - prevents runaway memory on large uploads
    max_side = 1024
    if max(pil.size) > max_side:
        pil.thumbnail((max_side, max_side), Image.LANCZOS)

    # Per-channel std deviation - used for contrast
    stat    = ImageStat.Stat(pil)
    std_rgb = np.array(stat.stddev) / 255.0   # normalised to [0, 1]

    # Rebuild BGR/gray/HSV from the (possibly resized) PIL image
    img_bgr  = _pil_to_bgr(pil)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv      = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    sat = float(hsv[..., 1].mean() / 255.0)   # average saturation [0, 1]
    val = float(hsv[..., 2].mean() / 255.0)   # average brightness [0, 1]

    feats = {
        "width":           pil.width,
        "height":          pil.height,
        "aspect_ratio":    pil.width / max(pil.height, 1),   # guard vs 0-height edge case
        "brightness_mean": val,
        "saturation_mean": sat,
        "contrast_std":    float(np.sqrt((std_rgb**2).mean())),  # RMS of per-channel std
        "colorfulness":    _colorfulness(img_bgr),
        "warmth":          _warmth_hue(img_bgr),
        "edge_density":    _edge_density(img_gray),
        "sharpness":       _sharpness_var_laplacian(img_gray),
        "faces_ratio":     _faces_ratio(img_bgr),
    }

    # Prepend "file" key only when called from the dataset builder
    if file_name is not None:
        feats = {"file": file_name, **feats}

    return feats