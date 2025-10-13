# backend/build_dataset.py
from pathlib import Path
import pandas as pd
import time
from backend.audio_analysis import extract_audio_features
from dotenv import load_dotenv
import os

load_dotenv()

AUDIO_DIR = Path(os.getenv("AUDIO_DIR", "./data/raw_audio"))
CSV_FEATURES = Path(os.getenv("CSV_FEATURES", "./data/audio_features.csv"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))

def main():
    # read existing CSV if it exists
    if CSV_FEATURES.exists():
        df = pd.read_csv(CSV_FEATURES)
        done = set(df["file"])
    else:
        df = pd.DataFrame()
        done = set()

    files = [f for f in AUDIO_DIR.glob("*.wav") if f.name not in done]
    if not files:
        print("No new files to process.")
        return

    while files:
        batch = files[:BATCH_SIZE]
        files = files[BATCH_SIZE:]  
        rows = []

        for path in batch:
            print(f"\nAnalyzing: {path.name}")
            try:
                features = extract_audio_features(path)
                rows.append(features)
            except Exception as e:
                print(f"Error on {path.name}: {e}")

        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
        df.to_csv(CSV_FEATURES, index=False)
        print(f"Added {len(rows)} files → {CSV_FEATURES}")

        # if there are remaining files, pause before continuing
        if files:
            print(f"\nPausing 10s before processing the next {min(BATCH_SIZE, len(files))} files...")
            for i in range(10, 0, -1):
                print(f"Resuming in {i} s...", end="\r")
                time.sleep(1)
            print()

if __name__ == "__main__":
    main()
