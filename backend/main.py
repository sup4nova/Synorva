# backend/main.py
from pathlib import Path
import time
import pandas as pd
import os
from backend.audio_analysis import extract_audio_features
from backend.label_audio_emotions import label_dataframe
from backend.build_picture_dataset import main as build_image_features_csv
from backend.label_picture_emotions import label_image_dataframe
from dotenv import load_dotenv
 
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


def main():
    print("step 1/2: building or updating features csv...")
    build_features_csv()
    print("\nstep 2/2: labeling emotions...")
    label_features_csv()
    print("\ndone")


if __name__ == "__main__":
    main()

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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["audio","image","both"], default="both",
                        help="pipeline à exécuter")
    args = parser.parse_args()

    if args.mode in ("audio","both"):
        print("AUDIO  step 1/2: features…")
        build_features_csv()
        print("AUDIO  step 2/2: labeling…")
        label_features_csv()

    if args.mode in ("image","both"):
        print("\nIMAGE step 1/2: features…")
        build_image_features_csv()
        print("IMAGE step 2/2: labeling…")
        label_image_features_csv()

    print("\ndone")