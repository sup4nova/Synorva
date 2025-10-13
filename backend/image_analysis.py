# backend/image_analysis.py
from pathlib import Path
import numpy as np
from PIL import Image, ImageStat
import cv2

def _pil_to_bgr(img):
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

def _colorfulness(img_bgr):
    (B, G, R) = cv2.split(img_bgr.astype("float"))
    rg = np.abs(R - G)
    yb = np.abs(0.5 * (R + G) - B)
    return float(np.sqrt(np.std(rg)**2 + np.std(yb)**2) +
                 0.3 * np.sqrt(np.mean(rg)**2 + np.mean(yb)**2))

def _warmth_hue(img_bgr):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    hue = hsv[..., 0] * 2.0
    sat = hsv[..., 1] / 255.0
    val = hsv[..., 2] / 255.0
    mask = (sat > 0.15) & (val > 0.15)
    if not np.any(mask):
        return 0.0
    h = hue[mask]
    warm = ((h <= 60) | (h >= 300)).mean()
    cold = ((h >= 180) & (h <= 260)).mean()
    return float(warm - cold)

def _edge_density(img_gray):
    edges = cv2.Canny(img_gray, 100, 200)
    return float(edges.mean())

def _sharpness_var_laplacian(img_gray):
    return float(cv2.Laplacian(img_gray, cv2.CV_64F).var())

def _faces_ratio(img_bgr):
    try:
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(32, 32))
        if len(faces) == 0:
            return 0.0
        areas = [w * h for (_, _, w, h) in faces]
        return float(sum(areas) / (gray.shape[0] * gray.shape[1]))
    except Exception:
        return 0.0

def extract_image_features(path: str | Path):
    """Analyse purement visuelle d'une image, sans texte ni métadonnées."""
    p = Path(path)
    img = Image.open(p).convert("RGB")

    # Redimensionner pour accélérer
    max_side = 1024
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)

    stat = ImageStat.Stat(img)
    mean_rgb = np.array(stat.mean) / 255.0
    std_rgb = np.array(stat.stddev) / 255.0

    img_bgr = _pil_to_bgr(img)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    sat = float(hsv[..., 1].mean() / 255.0)
    val = float(hsv[..., 2].mean() / 255.0)

    return {
        "file": p.name,
        "width": img.width,
        "height": img.height,
        "aspect_ratio": img.width / img.height,
        "brightness_mean": val,
        "saturation_mean": sat,
        "contrast_std": float(np.sqrt((std_rgb**2).mean())),
        "colorfulness": _colorfulness(img_bgr),
        "warmth": _warmth_hue(img_bgr),
        "edge_density": _edge_density(img_gray),
        "sharpness": _sharpness_var_laplacian(img_gray),
        "faces_ratio": _faces_ratio(img_bgr),
    }
