# backend/pipeline.py
# Single command to rebuild all Synorva datasets in the correct order.
#
# Usage:
#   python -m backend.pipeline            # audio pipeline only (default)
#   python -m backend.pipeline --images   # audio + image pipelines
#   python -m backend.pipeline --help

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# --- Helpers ---

def step(title: str):
    """Print a visible section header to track progress in the terminal."""
    print(f"\n{'-'*55}")
    print(f"  {title}")
    print(f"{'-'*55}")


# --- Sub-pipelines ---

def run_audio_pipeline():
    """
    Full audio pipeline - two steps in order:

    1. build_audio_dataset.main()
       Scans data/raw_audio/**/*.wav, extracts acoustic features (librosa),
       adds valence/arousal/emotion labels, writes:
         - data/audio_features.csv
         - data/audio_features_labeled.csv

    2. build_samples_index.main()
       Reads audio_features_labeled.csv, infers instrument type from folder names,
       normalises valence/arousal to [-1, 1] via tanh, writes:
         - backend/data/samples_index.csv   (used by auto_arranger at runtime)
    """
    from backend.build_audio_dataset import main as build_audio
    from backend.build_samples_index import main as build_index

    step("1/2  Audio feature extraction + emotion labeling")
    build_audio()

    step("2/2  Generating samples_index.csv")
    build_index()


def run_image_pipeline():
    """
    Full image pipeline - two steps in order:

    1. build_picture_dataset.main()
       Scans data/raw_picture/**/*.{jpg,png,...}, extracts visual features
       (brightness, saturation, warmth, edge density, etc.), writes:
         - data/picture_features.csv

    2. label_image_features_csv() (from main.py)
       Adds valence/arousal/emotion columns and writes:
         - data/picture_features_labeled.csv
    """
    from backend.build_picture_dataset import main as build_pictures
    from backend.main import label_image_features_csv

    step("1/2  Image feature extraction")
    build_pictures()

    step("2/2  Image emotion labeling")
    label_image_features_csv()


# --- Entry point ---

def main():
    parser = argparse.ArgumentParser(
        description="Rebuild all Synorva datasets and the samples index"
    )
    parser.add_argument(
        "--images", action="store_true",
        help="Also run the image pipeline (build_picture_dataset + labeling)",
    )
    parser.add_argument(
        "--audio-only", action="store_true",
        help="Run only the audio pipeline (default behaviour when --images is absent)",
    )
    args = parser.parse_args()

    print("=" * 55)
    print("  SYNORVA - Dataset rebuild")
    print("=" * 55)

    # Audio pipeline always runs (it's the core dependency for track generation)
    try:
        run_audio_pipeline()
    except Exception as e:
        print(f"\n[ERROR] Audio pipeline failed: {e}")
        sys.exit(1)

    # Image pipeline is optional - only runs when --images is passed
    if args.images:
        try:
            run_image_pipeline()
        except Exception as e:
            print(f"\n[ERROR] Image pipeline failed: {e}")
            sys.exit(1)

    print(f"\n{'='*55}")
    print("  Done. Restart uvicorn if the backend was already running.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()