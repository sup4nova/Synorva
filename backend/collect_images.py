# backend/collect_images.py

# Downloads training images from the Unsplash API, organized by emotion category.
# Each emotion gets its own subfolder under data/raw_picture/.
# Quota is distributed evenly across all keywords to maximize visual diversity.
#
# Usage:
#   python -m backend.collect_images
#   python -m backend.collect_images --per-query 20 --out data/raw_picture
#
# Requires in .env:
#   UNSPLASH_ACCESS_KEY=your_key (free at https://unsplash.com/developers)
#   Rate limit: 50 requests/hour on the free tier.

import os
import sys
import time
import argparse
import math
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

UNSPLASH_API = "https://api.unsplash.com"

# Search queries per emotion - edit these to change dataset diversity.
# The quota (--per-query) is split evenly across all keywords in each emotion.
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
            "[ERROR] UNSPLASH_ACCESS_KEY missing from .env\n"
            "  -> Sign up at https://unsplash.com/developers\n"
            "  -> Add to .env: UNSPLASH_ACCESS_KEY=xxxxxxx"
        )
    return key


def _already_downloaded(emotion_dir: Path) -> set[str]:
    # Returns Unsplash photo IDs already on disk - used to skip re-downloads.
    return {f.stem for f in emotion_dir.glob("*.jpg")}


def fetch_photos(query: str, per_page: int, page: int, key: str) -> list[dict]:
    resp = requests.get(
        f"{UNSPLASH_API}/search/photos",
        headers={"Authorization": f"Client-ID {key}"},
        params={
            "query": query,
            "per_page": min(per_page, 30),  # API hard limit
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
        print(f"  ✗ Download failed {dest.name}: {e}")
        return False


def collect(out_dir: Path, per_query: int, pause: float = 1.0):
    out_dir.mkdir(parents=True, exist_ok=True)
    key = _access_key()

    total_dl = 0
    total_skip = 0

    for emotion, queries in QUERIES.items():
        emotion_dir = out_dir / emotion
        emotion_dir.mkdir(exist_ok=True)
        done_emotion = _already_downloaded(emotion_dir)

        print(f"\n-- {emotion.upper()} --")

        # Distribute quota evenly across all keywords so every one contributes.
        # e.g. per_query=20, 4 keywords -> 5 images per keyword
        per_keyword = max(1, math.ceil(per_query / len(queries)))

        for query in queries:
            fetched = 0
            page = 1

            print(f"  [{query}] - target: {per_keyword} images")

            while fetched < per_keyword:
                batch_size = min(30, per_keyword - fetched)
                try:
                    photos = fetch_photos(query, batch_size, page, key)
                except requests.HTTPError as e:
                    print(f"  ✗ API error ({query}): {e}")
                    break
                if not photos:
                    break  # query exhausted

                for photo in photos:
                    if fetched >= per_keyword:
                        break
                    uid = photo["id"]
                    if uid in done_emotion:
                        total_skip += 1
                        continue
                    dest = emotion_dir / f"{uid}.jpg"
                    if download_image(photo["urls"]["regular"], dest):
                        done_emotion.add(uid)
                        total_dl += 1
                        fetched += 1
                        print(f"  ✓ [{emotion}/{query}] {uid}.jpg")
                    time.sleep(pause)

                page += 1
                if len(photos) < batch_size:
                    break  # no more results for this keyword

    print(f"\n{'='*50}")
    print(f"  Downloaded: {total_dl}  |  Skipped (already present): {total_skip}")
    print(f"  Output folder: {out_dir}")
    print(f"{'='*50}")


def main():
    parser = argparse.ArgumentParser(description="Download training images from Unsplash")
    parser.add_argument("--per-query", type=int, default=20,
                        help="Total images per emotion, split evenly across keywords (default: 20)")
    parser.add_argument("--out", type=str, default="data/raw_picture",
                        help="Output folder relative to project root")
    parser.add_argument("--pause", type=float, default=0.5,
                        help="Pause between downloads in seconds (default: 0.5)")
    args = parser.parse_args()

    out_dir = ROOT / args.out
    n_keywords = max(len(v) for v in QUERIES.values())
    per_kw = max(1, math.ceil(args.per_query / n_keywords))
    print(f"Unsplash collect -> {out_dir}")
    print(f"  {args.per_query} images/emotion ÷ {n_keywords} keywords = ~{per_kw} per keyword")
    print(f"  {args.per_query} × {len(QUERIES)} emotions = ~{args.per_query * len(QUERIES)} images total")
    collect(out_dir, per_query=args.per_query, pause=args.pause)


if __name__ == "__main__":
    main()