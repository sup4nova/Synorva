# backend/build_image_dataset.py
from pathlib import Path
import pandas as pd
import time
import os
from dotenv import load_dotenv

from backend.image_analysis import extract_image_features

# charge .env depuis la racine du projet
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def _as_path(val: str | None, default_rel: str) -> Path:
    p = Path(val) if val else Path(default_rel)
    return p if p.is_absolute() else (ROOT / p)

PICTURE_DIR    = _as_path(os.getenv("PICTURE_DIR"), "data/raw_picture")
CSV_FEATURES   = _as_path(os.getenv("CSV_PICTURE_FEATURES"), "data/picture_features.csv")
BATCH_SIZE_IMG = int(os.getenv("BATCH_SIZE_IMG", 24))
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

def main():
    # lire l'existant pour skipper ce qui est déjà fait
    if CSV_FEATURES.exists():
        df = pd.read_csv(CSV_FEATURES)
        done = set(df["file"])
    else:
        df = pd.DataFrame()
        done = set()

    # on scanne récursivement le dossier d’images
    files = [f for f in PICTURE_DIR.rglob("*")
             if f.suffix.lower() in IMG_EXTS and f.name not in done]

    if not files:
        print("No new images to process.")
        return

    while files:
        batch = files[:BATCH_SIZE_IMG]
        files = files[BATCH_SIZE_IMG:]
        rows = []

        for path in batch:
            rel = path.relative_to(ROOT) if path.is_absolute() or path.is_relative_to(ROOT) else path
            print(f"\nAnalyzing image: {rel}")
            try:
                feats = extract_image_features(path)
                rows.append(feats)
            except Exception as e:
                print(f"Error on {path.name}: {e}")

        if rows:
            df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
            df.to_csv(CSV_FEATURES, index=False)
            print(f"Added {len(rows)} images → {CSV_FEATURES}")

        if files:
            nxt = min(BATCH_SIZE_IMG, len(files))
            print(f"\nPausing 5s before processing the next {nxt} images…")
            for i in range(5, 0, -1):
                print(f"Resuming in {i}s", end="\r")
                time.sleep(1)
            print()

if __name__ == "__main__":
    main()
