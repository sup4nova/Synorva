# backend/build_image_dataset.py

# Scans data/raw_picture/ recursively, extracts visual features from every
# image, and writes the result to picture_features.csv. Then runs emotion
# labeling (valence/arousal) in-place and writes picture_features_labeled.csv.
#
# Usage:
#   python -m backend.build_image_dataset
#   (or via pipeline.py --images)

from pathlib import Path
import pandas as pd
import time
import os
from dotenv import load_dotenv

import cv2
from backend.image_analysis import extract_image_features
from backend.label_picture_emotions import label_image_dataframe

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def _as_path(val: str | None, default_rel: str) -> Path:
    p = Path(val) if val else Path(default_rel)
    return p if p.is_absolute() else (ROOT / p)

PICTURE_DIR    = _as_path(os.getenv("PICTURE_DIR"),           "data/raw_picture")
CSV_FEATURES   = _as_path(os.getenv("CSV_PICTURE_FEATURES"),  "data/picture_features.csv")
CSV_LABELED    = _as_path(os.getenv("CSV_PICTURE_LABELED"),   "data/picture_features_labeled.csv")
BATCH_SIZE_IMG = int(os.getenv("BATCH_SIZE_IMG", 24))
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def main():
    # Load already-processed files to skip them on re-runs
    if CSV_FEATURES.exists():
        df = pd.read_csv(CSV_FEATURES)
        done = set(df["file"])
    else:
        df = pd.DataFrame()
        done = set()

    # Scan all subfolders - relative path used as unique key to avoid
    # collisions between files with the same name in different folders
    files = [
        f for f in PICTURE_DIR.rglob("*")
        if f.is_file()
        and f.suffix.lower() in IMG_EXTS
        and str(f.relative_to(PICTURE_DIR)) not in done
    ]

    if not files:
        print("No new images to process.")
        return

    print(f"Found {len(files)} new image(s) in {PICTURE_DIR}")

    while files:
        batch = files[:BATCH_SIZE_IMG]
        files = files[BATCH_SIZE_IMG:]
        rows = []

        for path in batch:
            rel = str(path.relative_to(PICTURE_DIR))
            print(f"\nAnalyzing image: {rel}")
            try:
                img = cv2.imread(str(path))
                if img is None:
                    print(f"  Could not load: {path.name} - skipping.")
                    continue
                # Pass relative path as file_name so the CSV key matches the
                # dedup check above (avoids collisions across subfolders)
                feats = extract_image_features(img, file_name=rel)
                rows.append(feats)
            except Exception as e:
                print(f"Error on {path.name}: {e}")

        if rows:
            df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
            df.to_csv(CSV_FEATURES, index=False)
            print(f"Added {len(rows)} images -> {CSV_FEATURES}")

        if files:
            nxt = min(BATCH_SIZE_IMG, len(files))
            print(f"\nPausing 5s before next {nxt} images...")
            for i in range(5, 0, -1):
                print(f"Resuming in {i}s", end="\r")
                time.sleep(1)
            print()

    # Label valence/arousal/emotion and write the labeled CSV
    if df.empty:
        print("No data to label.")
        return

    print("\nLabeling emotions...")
    labeled = label_image_dataframe(df)
    labeled.to_csv(CSV_LABELED, index=False)
    print(f"Labeled CSV written -> {CSV_LABELED}")
    print(labeled[["file", "valence", "arousal", "emotion"]].head(8).to_string(index=False))


if __name__ == "__main__":
    main()