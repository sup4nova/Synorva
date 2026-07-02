# backend/main.py
# FastAPI application - HTTP server for the Synorva frontend.
# Also runnable as a CLI to rebuild datasets:
#   python -m backend.main --mode audio   -> extract + label audio features
#   python -m backend.main --mode image   -> extract + label image features
#   python -m backend.main --mode both    -> both pipelines

from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env before any os.getenv() calls below
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

import pandas as pd
import numpy as np
import cv2
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.build_audio_dataset import main as build_audio_features_csv
from backend.build_picture_dataset import main as build_image_features_csv
from backend.label_picture_emotions import label_image_dataframe
from backend.image_analysis import predict_valaro_from_bgr
from backend.auto_arranger import render_track


# --- App ---

app = FastAPI()

# Serve generated audio mixes at /static/renders/mix.wav etc.
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)

# Allow the Vite dev server to call the API without CORS errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Path helpers ---

def _as_path(val, default_rel):
    """Resolve an env var value (or fallback) to an absolute Path."""
    p = Path(val) if val else Path(default_rel)
    return p if p.is_absolute() else (ROOT / p)

CSV_PICT_FEATS   = _as_path(os.getenv("CSV_PICTURE_FEATURES"),         "data/picture_features.csv")
CSV_PICT_LABELED = _as_path(os.getenv("CSV_PICTURE_FEATURES_LABELED"), "data/picture_features_labeled.csv")
UPLOADS_DIR      = ROOT / "uploads"


# --- Dataset helpers ---

def label_image_features_csv():
    """Load picture_features.csv, add valence/arousal/emotion, write labeled CSV."""
    if not CSV_PICT_FEATS.exists():
        print("No picture features CSV to label yet. Run image feature build first.")
        return
    df = pd.read_csv(CSV_PICT_FEATS)
    if df.empty:
        print("Picture features CSV is empty.")
        return
    labeled = label_image_dataframe(df)
    labeled.to_csv(CSV_PICT_LABELED, index=False)
    print(f"Labeled images -> {CSV_PICT_LABELED}")
    print(labeled[["file", "valence", "arousal", "emotion"]].head(8).to_string(index=False))


# --- API endpoints ---

@app.get("/")
def root():
    """Basic connectivity check."""
    return {"message": "FastAPI is connected."}


@app.get("/health")
def health():
    """Lightweight liveness probe polled by the frontend."""
    return {"ok": True}


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    Save an uploaded image to uploads/ and return its path.
    Used for manual inspection / debugging - not part of the main emotion flow.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File is not an image.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name   # strip any directory traversal components
    dest = UPLOADS_DIR / f"{uuid4().hex}_{safe_name}"

    data = await file.read()
    dest.write_bytes(data)

    return {"message": "ok", "saved_as": str(dest), "size": len(data)}


@app.post("/api/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    """
    Predict valence and arousal from an uploaded image.
    Returns: {valence, arousal, features_used}
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image.")

    data = await file.read()
    img  = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not decode image.")

    return predict_valaro_from_bgr(img)


@app.post("/api/build-track")
async def build_track(file: UploadFile = File(...)):
    """
    Full pipeline: uploaded image -> valence/arousal -> rendered audio mix.

    Steps:
      1. Decode image from upload bytes
      2. predict_valaro_from_bgr -> {valence, arousal}
      3. render_track -> selects and mixes samples, writes mix.wav to static/renders/
      4. Return public URL for the mix + the selected sample list
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Image expected.")

    data = await file.read()
    img  = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not decode image.")

    pred = predict_valaro_from_bgr(img, file.filename)
    info = render_track(target_val=pred["valence"], target_aro=pred["arousal"])

    out_path   = Path(info["output"])
    static_dir = Path(__file__).parent / "static"
    mix_url    = "/static/" + out_path.relative_to(static_dir).as_posix()

    return {
        "valence": pred["valence"],
        "arousal": pred["arousal"],
        "mix_url": mix_url,
        "picks":   info["picks"],
    }


# --- CLI entry point ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Rebuild Synorva feature datasets")
    parser.add_argument(
        "--mode",
        choices=["audio", "image", "both"],
        default="both",
        help="Which pipeline to run (default: both)",
    )
    args = parser.parse_args()

    if args.mode in ("audio", "both"):
        print("AUDIO: extracting features and labeling emotions...")
        build_audio_features_csv()

    if args.mode in ("image", "both"):
        print("\nIMAGE step 1/2: features...")
        build_image_features_csv()
        print("IMAGE step 2/2: labeling...")
        label_image_features_csv()

    print("\nDone.")
