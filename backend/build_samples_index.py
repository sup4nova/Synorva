# backend/build_samples_index.py
"""
Construit backend/data/samples_index.csv à partir de data/audio_features_labeled.csv.

Ce script fait le pont entre le pipeline d'extraction/labeling audio
et l'auto_arranger qui lit samples_index.csv.

Il infère le type d'instrument depuis le nom du sous-dossier :
    data/raw_audio/kick/kick_01.wav  →  type = "kick"

Usage :
    python -m backend.build_samples_index
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def _as_path(val, default_rel):
    p = Path(val) if val else Path(default_rel)
    return p if p.is_absolute() else (ROOT / p)

AUDIO_DIR        = _as_path(os.getenv("AUDIO_DIR"), "data/raw_audio")
CSV_LABELED      = _as_path(os.getenv("CSV_LABELED"), "data/audio_features_labeled.csv")
SAMPLES_INDEX    = ROOT / "backend" / "data" / "samples_index.csv"

# Types reconnus — doivent correspondre aux clés de ARRANGE dans auto_arranger.py
KNOWN_TYPES = {"kick", "snare", "hihat", "bass", "melody", "riser", "pad", "vocal"}


def infer_type(rel_path: str) -> str | None:
    """Infère le type depuis les composantes du chemin relatif."""
    parts = Path(rel_path).parts
    for part in parts:
        name = part.lower()
        for t in KNOWN_TYPES:
            if t in name:
                return t
    return None


def normalize_to_unit(series: pd.Series) -> pd.Series:
    """Ramène les z-scores audio dans [-1, 1] via tanh pour matcher l'échelle image."""
    return np.tanh(series * 0.6)


def build(csv_labeled: Path, audio_dir: Path, out_path: Path):
    if not csv_labeled.exists():
        print(f"[ERREUR] CSV labeled introuvable : {csv_labeled}")
        print("  Lance d'abord : python -m backend.build_audio_dataset")
        print("                  python -m backend.main --mode audio")
        return

    df = pd.read_csv(csv_labeled)
    if df.empty:
        print("[ERREUR] CSV labeled vide.")
        return

    print(f"Chargé : {len(df)} samples depuis {csv_labeled}")

    # normalise valence/arousal (z-scores → [-1,1]) pour matcher l'échelle image
    df["valence"] = normalize_to_unit(df["valence"])
    df["arousal"]  = normalize_to_unit(df["arousal"])

    rows = []
    skipped = 0

    for _, row in df.iterrows():
        rel = row["file"]  # chemin relatif depuis AUDIO_DIR (ex: kick/kick_01.wav)
        abs_path = audio_dir / rel

        if not abs_path.exists():
            print(f"  ✗ Fichier manquant : {abs_path}")
            skipped += 1
            continue

        typ = infer_type(rel)
        if typ is None:
            print(f"  ⚠ Type inconnu pour : {rel}  (dossier parent non reconnu)")
            skipped += 1
            continue

        bpm = row.get("tempo_bpm", "")
        rows.append({
            "path":    str(abs_path),
            "type":    typ,
            "bpm":     round(float(bpm), 2) if pd.notna(bpm) and bpm != "" else "",
            "key":     "",   # non extrait pour l'instant
            "valence": round(float(row["valence"]), 4),
            "arousal": round(float(row["arousal"]), 4),
        })

    if not rows:
        print("[ERREUR] Aucun sample valide trouvé.")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_path, index=False)

    print(f"\n{'='*55}")
    print(f"  samples_index.csv créé → {out_path}")
    print(f"  {len(rows)} samples indexés  |  {skipped} ignorés")
    print(f"\n  Répartition par type :")
    for t, g in out_df.groupby("type"):
        v_range = f"{g['valence'].min():.2f} → {g['valence'].max():.2f}"
        a_range = f"{g['arousal'].min():.2f} → {g['arousal'].max():.2f}"
        print(f"    {t:<10} {len(g):>3} samples  |  V: {v_range}  A: {a_range}")
    print(f"{'='*55}")


def main():
    build(CSV_LABELED, AUDIO_DIR, SAMPLES_INDEX)


if __name__ == "__main__":
    main()
