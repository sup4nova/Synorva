"""
Build demo_audio_features_labeled.csv from data/demo_samples/.

Run once after cloning (with the venv active):
    python scripts/build_demo_dataset.py

Produces data/demo_audio_features_labeled.csv, which auto_arranger.py
picks up automatically when the full dataset is not present.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("AUDIO_DIR",    str(ROOT / "data" / "demo_samples"))
os.environ.setdefault("CSV_FEATURES", str(ROOT / "data" / "demo_audio_features.csv"))
os.environ.setdefault("CSV_LABELED",  str(ROOT / "data" / "demo_audio_features_labeled.csv"))

from backend.build_audio_dataset import main  # noqa: E402

if __name__ == "__main__":
    demo_dir = ROOT / "data" / "demo_samples"
    if not demo_dir.exists():
        print(f"[error] {demo_dir} not found.")
        sys.exit(1)
    count = sum(1 for _ in demo_dir.rglob("*") if _.is_file())
    print(f"[demo] Processing {count} files from {demo_dir}")
    main()
    print(f"[demo] Done → {os.environ['CSV_LABELED']}")
