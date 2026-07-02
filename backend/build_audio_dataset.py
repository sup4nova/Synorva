# backend/build_audio_dataset.py

# Scans data/raw_audio/ recursively, extracts acoustic features from every
# audio file, infers the instrument type from the subfolder name, and writes
# the result to audio_features.csv. Then runs emotion labeling in-place.
#
# Usage:
#   python -m backend.build_audio_dataset
#   (or via pipeline.py which calls this automatically)

from pathlib import Path
import pandas as pd
import time
import os
from dotenv import load_dotenv
from backend.audio_analysis import extract_audio_features
from backend.label_audio_emotions import label_dataframe

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def _as_path(val: str | None, default_rel: str) -> Path:
    p = Path(val) if val else Path(default_rel)
    return p if p.is_absolute() else (ROOT / p)

AUDIO_DIR    = _as_path(os.getenv("AUDIO_DIR"),    "data/raw_audio")
CSV_FEATURES = _as_path(os.getenv("CSV_FEATURES"), "data/audio_features.csv")
CSV_LABELED  = _as_path(os.getenv("CSV_LABELED"),  "data/audio_features_labeled.csv")
BATCH_SIZE   = int(os.getenv("BATCH_SIZE", 10))

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff"}


def main():
    # Load already-processed files to skip them on re-runs
    if CSV_FEATURES.exists():
        df = pd.read_csv(CSV_FEATURES)
        done = set(df["file"])
    else:
        df = pd.DataFrame()
        done = set()

    # Scan all subfolders - relative path is used as unique key to avoid
    # collisions between files with the same name in different folders
    files = [
        f for f in AUDIO_DIR.rglob("*")
        if f.is_file()
        and f.suffix.lower() in AUDIO_EXTS
        and str(f.relative_to(AUDIO_DIR)) not in done
    ]

    if not files:
        print("No new files to process.")
    else:
        print(f"Found {len(files)} new file(s) in {AUDIO_DIR}")

        while files:
            batch = files[:BATCH_SIZE]
            files = files[BATCH_SIZE:]
            rows = []

            for path in batch:
                rel = str(path.relative_to(AUDIO_DIR))
                print(f"\nAnalyzing: {rel}")
                try:
                    features = extract_audio_features(path)
                    features["file"] = rel          # relative path - unique dedup key
                    features["path"] = str(path)    # absolute path - used by auto_arranger to load the file
                    # Instrument type inferred from subfolder name (e.g. kick/, bass/, melody/)
                    # Falls back to "unknown" if the file sits directly in AUDIO_DIR
                    features["type"] = path.parent.name if path.parent != AUDIO_DIR else "unknown"
                    rows.append(features)
                except Exception as e:
                    print(f"Error on {rel}: {e}")

            if rows:
                df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
                df.to_csv(CSV_FEATURES, index=False)
                print(f"Added {len(rows)} files -> {CSV_FEATURES}")

            if files:
                print(f"\nPausing 10s before next {min(BATCH_SIZE, len(files))} files...")
                for i in range(10, 0, -1):
                    print(f"Resuming in {i}s...", end="\r")
                    time.sleep(1)
                print()

    # Label valence/arousal/emotion and write the labeled CSV
    if df.empty:
        print("No data to label.")
        return

    print("\nLabeling emotions...")
    labeled = label_dataframe(df)
    labeled.to_csv(CSV_LABELED, index=False)
    print(f"Labeled CSV written -> {CSV_LABELED}")
    print(labeled[["file", "type", "valence", "arousal", "emotion"]].head(8).to_string(index=False))


if __name__ == "__main__":
    main()