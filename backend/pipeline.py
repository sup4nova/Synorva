# backend/pipeline.py
"""
Pipeline complet Synorva — une seule commande pour tout mettre à jour.

Usage :
    python -m backend.pipeline            # audio + samples_index
    python -m backend.pipeline --images   # + dataset images
    python -m backend.pipeline --help
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def step(title: str):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")


def run_audio_pipeline():
    from backend.build_audio_dataset import main as build_audio
    from backend.main import build_features_csv, label_features_csv
    from backend.build_samples_index import main as build_index

    step("1/3  Extraction des features audio")
    build_features_csv()

    step("2/3  Labeling valence/arousal audio")
    label_features_csv()

    step("3/3  Génération du samples_index.csv")
    build_index()


def run_image_pipeline():
    from backend.build_picture_dataset import main as build_pictures
    from backend.main import label_image_features_csv

    step("1/2  Extraction des features image")
    build_pictures()

    step("2/2  Labeling valence/arousal image")
    label_image_features_csv()


def main():
    parser = argparse.ArgumentParser(
        description="Met à jour tous les datasets et le samples_index Synorva"
    )
    parser.add_argument(
        "--images", action="store_true",
        help="Inclure aussi le pipeline image (build_picture_dataset + labeling)"
    )
    parser.add_argument(
        "--audio-only", action="store_true",
        help="Forcer uniquement le pipeline audio (défaut si --images absent)"
    )
    args = parser.parse_args()

    print("=" * 55)
    print("  SYNORVA — Pipeline de mise à jour")
    print("=" * 55)

    try:
        run_audio_pipeline()
    except Exception as e:
        print(f"\n[ERREUR] Pipeline audio : {e}")
        sys.exit(1)

    if args.images:
        try:
            run_image_pipeline()
        except Exception as e:
            print(f"\n[ERREUR] Pipeline image : {e}")
            sys.exit(1)

    print(f"\n{'='*55}")
    print("  Terminé. Relance uvicorn si le backend tournait déjà.")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
