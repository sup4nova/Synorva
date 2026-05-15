# backend/build_dataset.py
from pathlib import Path
import pandas as pd
import time
from backend.audio_analysis import extract_audio_features
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def _as_path(val: str | None, default_rel: str) -> Path:
    p = Path(val) if val else Path(default_rel)
    return p if p.is_absolute() else (ROOT / p)

AUDIO_DIR    = _as_path(os.getenv("AUDIO_DIR"), "data/raw_audio")
CSV_FEATURES = _as_path(os.getenv("CSV_FEATURES"), "data/audio_features.csv")
BATCH_SIZE   = int(os.getenv("BATCH_SIZE", 10))

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff"}

def main():
    if CSV_FEATURES.exists():
        df = pd.read_csv(CSV_FEATURES)
        done = set(df["file"])
    else:
        df = pd.DataFrame()
        done = set()

    # rglob pour descendre dans tous les sous-dossiers, chemin relatif comme clé unique
    files = [
        f for f in AUDIO_DIR.rglob("*")
        if f.suffix.lower() in AUDIO_EXTS
        and str(f.relative_to(AUDIO_DIR)) not in done
    ]
    if not files:
        print("No new files to process.")
        return

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
                features["file"] = rel   # chemin relatif → clé unique même en sous-dossiers
                rows.append(features)
            except Exception as e:
                print(f"Error on {rel}: {e}")

        if rows:
            df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
            df.to_csv(CSV_FEATURES, index=False)
            print(f"Added {len(rows)} files → {CSV_FEATURES}")

        if files:
            print(f"\nPausing 10s before processing the next {min(BATCH_SIZE, len(files))} files...")
            for i in range(10, 0, -1):
                print(f"Resuming in {i}s…", end="\r")
                time.sleep(1)
            print()

if __name__ == "__main__":
    main()
