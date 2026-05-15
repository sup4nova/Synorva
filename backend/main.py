# backend/main.py
from pathlib import Path
import time
import pandas as pd
import os
from backend.audio_analysis import extract_audio_features
from backend.label_audio_emotions import label_dataframe
from backend.build_picture_dataset import main as build_image_features_csv
from backend.label_picture_emotions import label_image_dataframe
from backend.image_analysis import predict_valaro_from_bgr
from backend.auto_arranger import render_track
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
from typing import Dict
from dotenv import load_dotenv
import numpy as np, cv2

app = FastAPI()
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def _as_path(val: str | None, default_rel: str) -> Path:
    p = Path(val) if val else Path(default_rel)
    return p if p.is_absolute() else (ROOT / p)

AUDIO_DIR    = _as_path(os.getenv("AUDIO_DIR"), "data/raw_audio")
CSV_FEATURES = _as_path(os.getenv("CSV_FEATURES"), "data/audio_features.csv")
CSV_LABELED  = _as_path(os.getenv("CSV_LABELED"), "data/audio_features_labeled.csv")
BATCH_SIZE   = int(os.getenv("BATCH_SIZE", 10))
PICTURE_DIR      = _as_path(os.getenv("PICTURE_DIR"), "data/raw_picture")
CSV_PICT_FEATS   = _as_path(os.getenv("CSV_PICTURE_FEATURES"), "data/picture_features.csv")
CSV_PICT_LABELED = _as_path(os.getenv("CSV_PICTURE_FEATURES_LABELED"), "data/picture_features_labeled.csv")

def build_features_csv():
    """scan wav files, extract audio features in batches and update audio_features.csv"""
    # load existing csv if it already exists (to skip processed files)
    if CSV_FEATURES.exists():
        df = pd.read_csv(CSV_FEATURES)
        done = set(df["file"])
    else:
        df = pd.DataFrame()
        done = set()

    # find all wav files not yet processed
    files = [f for f in AUDIO_DIR.glob("*.wav") if f.name not in done]
    if not files:
        print("no new files to process.")
        return df

    # process files batch by batch
    while files:
        batch = files[:BATCH_SIZE]
        files = files[BATCH_SIZE:]
        rows = []

        for path in batch:
            print(f"\nanalyzing: {path.name}")
            try:
                features = extract_audio_features(path)
                rows.append(features)
            except Exception as e:
                print(f"error on {path.name}: {e}")

        # merge new data and save to csv
        if rows:
            df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
            df.to_csv(CSV_FEATURES, index=False)
            print(f"added {len(rows)} files → {CSV_FEATURES}")

        # small pause before next batch
        if files:
            print(f"\npausing 10s before processing the next {min(BATCH_SIZE, len(files))} files...")
            for i in range(10, 0, -1):
                print(f"resuming in {i} s...", end="\r")
                time.sleep(1)
            print()

    return df


def label_features_csv():
    """load the features csv, add valence/arousal/emotion columns, and save a labeled csv"""
    if not CSV_FEATURES.exists():
        print("no features csv to label yet. run feature build first.")
        return                                                                              

    df = pd.read_csv(CSV_FEATURES)
    if df.empty:
        print("features csv is empty. nothing to label.")
        return

    labeled = label_dataframe(df)
    labeled.to_csv(CSV_LABELED, index=False)
    print(f"labeled csv written → {CSV_LABELED}")
    print(labeled[["file", "valence", "arousal", "emotion"]].head(8).to_string(index=False))


def label_image_features_csv():
    if not CSV_PICT_FEATS.exists():
        print("no picture features csv to label yet. run image feature build first.")
        return
    df = pd.read_csv(CSV_PICT_FEATS)
    if df.empty:
        print("picture features csv is empty.")
        return
    labeled = label_image_dataframe(df)
    labeled.to_csv(CSV_PICT_LABELED, index=False)
    print(f"labeled images → {CSV_PICT_LABELED}")
    print(labeled[["file","valence","arousal","emotion"]].head(8).to_string(index=False))

@app.get("/")
def root():
    return {"message": "FastAPI est connecté et prêt."}

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Le fichier n'est pas une image.")
    os.makedirs("uploads", exist_ok=True)
    safe_name = Path(file.filename).name  # strips any directory components
    path = os.path.join("uploads", f"{uuid4().hex}_{safe_name}")
    data = await file.read()
    with open(path, "wb") as f: f.write(data)
    return {"message": "ok", "saved_as": path, "size": len(data)}

@app.get("/health")
def health():
    print("→ /health hit")
    return {"ok": True}

@app.post("/api/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Le fichier doit être une image.")
    data = await file.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Image illisible.")
    out = predict_valaro_from_bgr(img)
    return out

@app.post("/api/build-track")
async def build_track(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Image attendue.")
    data = await file.read()
    img  = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Image illisible.")
    pred = predict_valaro_from_bgr(img, file.filename)  # -> {valence, arousal}
    info = render_track(target_val=pred["valence"], target_aro=pred["arousal"])
    # URL publique vers le mix wav
    rel = info["output"].replace("backend", "").replace("\\", "/").lstrip("/")
    return {
        "valence": pred["valence"],
        "arousal": pred["arousal"],
        "mix_url": f"/{rel}",   # ex: /static/renders/mix.wav
        "picks": info["picks"],
    }