# backend/collect_samples.py
"""
Collecte de samples audio via l'API Freesound.

Télécharge des samples CC-licensed filtrés par type d'instrument
et construit le fichier samples_index.csv utilisé par auto_arranger.py.

Usage :
    python -m backend.collect_samples
    python -m backend.collect_samples --per-type 15 --out data/raw_audio

Clé requise dans .env :
    FREESOUND_API_KEY=your_key_here
    (inscription gratuite sur https://freesound.org/apiv2/apply/)
"""

import os
import sys
import csv
import time
import argparse
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

FREESOUND_API = "https://freesound.org/apiv2"

# Correspondance type → tags de recherche Freesound
# Chaque type doit correspondre à une valeur du champ "type" dans ARRANGE (auto_arranger.py)
SAMPLE_QUERIES: dict[str, list[str]] = {
    "kick":   ["kick drum one shot", "bass drum hit", "kick one shot"],
    "snare":  ["snare drum hit", "snare one shot", "snare crack"],
    "hihat":  ["hi-hat loop", "hihat closed", "hihat rhythm"],
    "bass":   ["bass loop", "bass guitar loop", "sub bass loop"],
    "melody": ["melodic loop", "synth melody", "piano melody loop"],
    "riser":  ["riser effect", "impact riser", "build up effect"],
    "pad":    ["ambient pad", "synth pad loop", "atmosphere pad"],
    "vocal":  ["vocal chop loop", "vocal sample", "voice loop"],
}

# Durée maximale des samples (secondes) — évite les morceaux complets
MAX_DURATION = 30
MIN_DURATION = 0.5

# Licences autorisées (CC0 = domaine public, CC BY = attribution)
ALLOWED_LICENSES = [
    "Creative Commons 0",
    "Attribution",
    "Attribution NonCommercial",
]


def _api_key() -> str:
    key = os.getenv("FREESOUND_API_KEY", "")
    if not key:
        sys.exit(
            "[ERREUR] FREESOUND_API_KEY manquante dans .env\n"
            "  → Crée un compte sur https://freesound.org/apiv2/apply/\n"
            "  → Copie ta clé dans .env : FREESOUND_API_KEY=xxxxxxx"
        )
    return key


def _load_existing_index(csv_path: Path) -> set[str]:
    if not csv_path.exists():
        return set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["path"] for row in reader}


def search_sounds(query: str, key: str, page: int = 1, page_size: int = 15) -> dict:
    params = {
        "query": query,
        "filter": (
            f"duration:[{MIN_DURATION} TO {MAX_DURATION}] "
            f"type:wav"
        ),
        "fields": "id,name,tags,duration,license,previews,download,ac_analysis",
        "page": page,
        "page_size": page_size,
        "token": key,
    }
    resp = requests.get(f"{FREESOUND_API}/search/text/", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_download_url(sound_id: int, key: str) -> str | None:
    resp = requests.get(
        f"{FREESOUND_API}/sounds/{sound_id}/",
        params={"token": key, "fields": "download,previews"},
        timeout=10,
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    # Utilise le preview HQ si le download nécessite OAuth
    return data.get("previews", {}).get("preview-hq-mp3") or data.get("download")


def download_file(url: str, dest: Path, key: str) -> bool:
    try:
        r = requests.get(url, params={"token": key}, timeout=30, stream=True)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"  ✗ Échec : {dest.name} — {e}")
        return False


def extract_ac_meta(sound: dict) -> tuple[float | None, str | None]:
    """Extrait BPM et tonalité depuis AudioCommons analysis si disponible."""
    ac = sound.get("ac_analysis") or {}
    bpm = ac.get("ac_tempo")
    key = ac.get("ac_tonality")  # ex: "Am", "C major"
    return (float(bpm) if bpm else None), (str(key) if key else None)


CSV_HEADER = ["path", "type", "bpm", "key", "valence", "arousal"]


def append_to_index(csv_path: Path, row: dict):
    is_new = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def collect(out_dir: Path, csv_path: Path, per_type: int, pause: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    key = _api_key()
    existing = _load_existing_index(csv_path)

    total_dl = 0
    total_skip = 0

    for sample_type, queries in SAMPLE_QUERIES.items():
        type_dir = out_dir / sample_type
        type_dir.mkdir(exist_ok=True)
        downloaded_this_type = 0

        print(f"\n── {sample_type.upper()} ──")

        for query in queries:
            if downloaded_this_type >= per_type:
                break

            page = 1
            while downloaded_this_type < per_type:
                try:
                    data = search_sounds(query, key, page=page, page_size=15)
                except requests.HTTPError as e:
                    print(f"  ✗ API error ({query}): {e}")
                    break

                sounds = data.get("results", [])
                if not sounds:
                    break

                for sound in sounds:
                    if downloaded_this_type >= per_type:
                        break

                    sid = sound["id"]
                    name = f"{sid}.mp3"
                    dest = type_dir / name

                    if str(dest) in existing:
                        total_skip += 1
                        continue

                    # Vérifie la licence
                    license_str = sound.get("license", "")
                    if not any(lic in license_str for lic in ALLOWED_LICENSES):
                        continue

                    # Récupère l'URL de preview HQ (pas besoin d'OAuth)
                    previews = sound.get("previews", {})
                    url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
                    if not url:
                        continue

                    ok = download_file(url, dest, key)
                    if not ok:
                        continue

                    bpm, tonality = extract_ac_meta(sound)

                    # valence/arousal : à 0 par défaut, seront calculés par label_audio_emotions
                    row = {
                        "path": str(dest),
                        "type": sample_type,
                        "bpm": round(bpm, 2) if bpm else "",
                        "key": tonality or "",
                        "valence": 0.0,
                        "arousal": 0.0,
                    }
                    append_to_index(csv_path, row)
                    existing.add(str(dest))
                    downloaded_this_type += 1
                    total_dl += 1
                    print(f"  ✓ [{sample_type}] {name}  bpm={bpm or '?'}  key={tonality or '?'}  ({query})")
                    time.sleep(pause)

                page += 1
                if not data.get("next"):
                    break

    print(f"\n{'='*55}")
    print(f"  Téléchargés : {total_dl}  |  Ignorés (déjà présents) : {total_skip}")
    print(f"  Index CSV   : {csv_path}")
    print(f"  Dossier     : {out_dir}")
    print(f"\n  Prochaine étape : calculer valence/arousal des samples")
    print(f"    python -m backend.build_audio_dataset")
    print(f"    python -m backend.label_audio_emotions  (ou via main.py --mode audio)")
    print(f"{'='*55}")


def main():
    parser = argparse.ArgumentParser(description="Collecte de samples via Freesound")
    parser.add_argument("--per-type", type=int, default=20,
                        help="Samples à collecter par type (défaut: 20)")
    parser.add_argument("--out", type=str, default="data/raw_audio",
                        help="Dossier de sortie (relatif à la racine du projet)")
    parser.add_argument("--csv", type=str, default="backend/data/samples_index.csv",
                        help="Chemin du CSV index des samples")
    parser.add_argument("--pause", type=float, default=0.3,
                        help="Pause entre téléchargements en secondes (défaut: 0.3)")
    args = parser.parse_args()

    out_dir = ROOT / args.out
    csv_path = ROOT / args.csv
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    n_types = len(SAMPLE_QUERIES)
    print(f"Collecte Freesound → {out_dir}")
    print(f"  {args.per_type} samples × {n_types} types = ~{args.per_type * n_types} samples")
    collect(out_dir, csv_path, per_type=args.per_type, pause=args.pause)


if __name__ == "__main__":
    main()
