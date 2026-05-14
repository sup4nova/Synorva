# backend/collect_images.py
"""
Collecte d'images d'entraînement via l'API Unsplash.

Stratégie : rechercher des mots-clés liés aux 8 émotions du projet
pour obtenir une diversité visuelle couvrant tout l'espace valence/arousal.

Usage :
    python -m backend.collect_images
    python -m backend.collect_images --per-query 30 --out data/raw_picture

Clé requise dans .env :
    UNSPLASH_ACCESS_KEY=your_key_here
    (inscription gratuite sur https://unsplash.com/developers)
"""

import os
import sys
import time
import argparse
import hashlib
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

UNSPLASH_API = "https://api.unsplash.com"

# Mots-clés par émotion cible — diversité maximale dans l'espace V/A
QUERIES: dict[str, list[str]] = {
    "euphoric":    ["festival lights", "fireworks celebration", "party joy", "colorful carnival"],
    "uplifting":   ["sunny nature", "spring flowers", "happy child", "golden hour landscape"],
    "warm":        ["cozy fireplace", "autumn leaves", "warm sunset", "coffee morning"],
    "dreamy":      ["foggy forest", "pastel sky", "soft light bokeh", "misty lake"],
    "melancholic": ["rainy window", "abandoned place", "grey sky city", "lone tree winter"],
    "dark":        ["dark alley", "storm clouds", "night forest", "shadow figure"],
    "tense":       ["lightning storm", "crowded street", "close up eye", "industrial smoke"],
    "aggressive":  ["volcanic eruption", "crashing waves", "protest crowd", "fire explosion"],
}

def _access_key() -> str:
    key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not key:
        sys.exit(
            "[ERREUR] UNSPLASH_ACCESS_KEY manquante dans .env\n"
            "  → Crée un compte sur https://unsplash.com/developers\n"
            "  → Copie ta clé dans .env : UNSPLASH_ACCESS_KEY=xxxxxxx"
        )
    return key


def _already_downloaded(out_dir: Path) -> set[str]:
    return {f.stem for f in out_dir.glob("*.jpg")}


def fetch_photos(query: str, per_page: int, page: int, key: str) -> list[dict]:
    resp = requests.get(
        f"{UNSPLASH_API}/search/photos",
        headers={"Authorization": f"Client-ID {key}"},
        params={
            "query": query,
            "per_page": min(per_page, 30),  # max autorisé par l'API
            "page": page,
            "orientation": "squarish",
            "content_filter": "low",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=20, stream=True)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"  ✗ Échec téléchargement {dest.name} : {e}")
        return False


def collect(out_dir: Path, per_query: int, pause: float = 1.0):
    out_dir.mkdir(parents=True, exist_ok=True)
    key = _access_key()
    done = _already_downloaded(out_dir)

    total_dl = 0
    total_skip = 0

    for emotion, queries in QUERIES.items():
        emotion_dir = out_dir / emotion
        emotion_dir.mkdir(exist_ok=True)
        done_emotion = {f.stem for f in emotion_dir.glob("*.jpg")}

        print(f"\n── {emotion.upper()} ──")
        remaining = per_query

        for query in queries:
            if remaining <= 0:
                break
            page = 1
            fetched_this_query = 0

            while fetched_this_query < remaining:
                batch_size = min(30, remaining - fetched_this_query)
                try:
                    photos = fetch_photos(query, batch_size, page, key)
                except requests.HTTPError as e:
                    print(f"  ✗ API error ({query}): {e}")
                    break
                if not photos:
                    break

                for photo in photos:
                    uid = photo["id"]
                    if uid in done_emotion:
                        total_skip += 1
                        continue
                    url = photo["urls"]["regular"]  # ~1080px
                    dest = emotion_dir / f"{uid}.jpg"
                    ok = download_image(url, dest)
                    if ok:
                        done_emotion.add(uid)
                        total_dl += 1
                        fetched_this_query += 1
                        print(f"  ✓ [{emotion}] {uid}.jpg  ({query})")
                    time.sleep(pause)

                page += 1
                if len(photos) < batch_size:
                    break  # plus de résultats

            remaining -= fetched_this_query

    print(f"\n{'='*50}")
    print(f"  Téléchargés : {total_dl}  |  Ignorés (déjà présents) : {total_skip}")
    print(f"  Dossier : {out_dir}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(description="Collecte d'images via Unsplash")
    parser.add_argument("--per-query", type=int, default=20,
                        help="Images à collecter par émotion (défaut: 20)")
    parser.add_argument("--out", type=str, default="data/raw_picture",
                        help="Dossier de sortie (relatif à la racine du projet)")
    parser.add_argument("--pause", type=float, default=0.5,
                        help="Pause entre téléchargements en secondes (défaut: 0.5)")
    args = parser.parse_args()

    out_dir = ROOT / args.out
    print(f"Collecte Unsplash → {out_dir}")
    print(f"  {args.per_query} images par émotion × {len(QUERIES)} émotions = ~{args.per_query * len(QUERIES)} images")
    collect(out_dir, per_query=args.per_query, pause=args.pause)


if __name__ == "__main__":
    main()
