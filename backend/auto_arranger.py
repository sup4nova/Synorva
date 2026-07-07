# backend/auto_arranger.py

# Audio rendering engine.
# Takes two numbers (valence, arousal) and produces a 32-bar WAV file.
# Called by main.py /api/build-track when the user clicks "Generate track".

from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd
import librosa
import soundfile as sf
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def _as_path(val, default_rel):
    p = Path(val) if val else Path(default_rel)
    return p if p.is_absolute() else (ROOT / p)

# ============ RENDER CONFIG ============
SR = 44100                 # output sample rate (CD quality for the final mix)
TEMPO = 124.0              # target BPM - all samples are time-stretched to match
KEY_TARGET = "Am"          # target key - all samples are pitch-shifted to match
BARS_TOTAL = 32            # total track length in bars (~62s at 124 BPM)
SIG_BEATS = 4              # time signature: 4 beats per bar

# Arrangement map - defines when each instrument plays and how.
# bars: (start_bar, end_bar) - 1-indexed, end is exclusive
# pattern:
#   "1/1" = one shot every beat
#   "1/2" = one shot every 2 beats
#   "loop" = sample loops continuously
#   "hold" = sample is stretched to fill the entire slot
# Add more instrument types here as long as they exist in your CSV (e.g. "snare", "hihat")
ARRANGE = {
    "kick":   {"bars": (1, 33), "pattern": "1/1"},
    "bass":   {"bars": (5, 33), "pattern": "1/2"},
    "melody": {"bars": (9, 25), "pattern": "loop"},
    "riser":  {"bars": (29, 33), "pattern": "hold"},
}

OUT_WAV = str(ROOT / "backend" / "static" / "renders" / "mix.wav")

def _resolve_samples_csv() -> str:
    configured = os.getenv("CSV_LABELED")
    if configured:
        return str(_as_path(configured, ""))
    main_csv = ROOT / "data" / "audio_features_labeled.csv"
    demo_csv = ROOT / "data" / "demo_audio_features_labeled.csv"
    if main_csv.exists():
        return str(main_csv)
    if demo_csv.exists():
        return str(demo_csv)
    raise FileNotFoundError(
        "No samples CSV found. Run: python scripts/build_demo_dataset.py"
    )


# ============ TEMPO UTILS ============

def beats_to_samples(beats: float, sr=SR, tempo=TEMPO) -> int:
    # Convert a number of beats to audio samples at the current tempo
    seconds = (60.0 / tempo) * beats
    return int(seconds * sr)

def bars_to_samples(bars: float, sr=SR, tempo=TEMPO, sig_beats=SIG_BEATS) -> int:
    # Convert a number of bars to audio samples
    return beats_to_samples(bars * sig_beats, sr=sr, tempo=tempo)


# ============ PITCH / TEMPO HELPERS ============

def _semi_tone_shift(src_key: Optional[str], tgt_key: Optional[str]) -> int:
    # Returns how many semitones to shift src_key to reach tgt_key.
    # Only uses the root note (e.g. "Am" -> "A", "C#" -> "C#").
    if not src_key or not tgt_key:
        return 0
    order = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    def root(k: str) -> str:
        k = k.replace("min","m").replace("maj","").upper()
        return k.replace("M","")[:2].replace("H","")
    try:
        return order.index(root(tgt_key)) - order.index(root(src_key))
    except Exception:
        return 0

def _loudness_normalize(y: np.ndarray, target_db=-18.0) -> np.ndarray:
    # Normalize the RMS level of an audio signal to target_db.
    # Ensures all samples sit at the same perceived loudness before mixing.
    rms = np.sqrt(np.mean(y**2) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    gain = 10 ** ((target_db - db)/20)
    return y * gain


# ============ DATA ============

def load_samples_index(path: str | None = None) -> pd.DataFrame:
    path = path or _resolve_samples_csv()
    # Load the labeled audio CSV and normalize column names for the arranger.
    # Renames tempo_bpm -> bpm and adds an empty key column if missing.
    df = pd.read_csv(path)
    if "tempo_bpm" in df.columns and "bpm" not in df.columns:
        df = df.rename(columns={"tempo_bpm": "bpm"})
    if "key" not in df.columns:
        df["key"] = None
    needed = {"path", "type", "bpm", "valence", "arousal"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    return df


# ============ SELECTION ============

def select_best_by_emotion(df: pd.DataFrame, typ: str, target_val: float, target_aro: float) -> Optional[pd.Series]:
    # Find the sample of a given type whose valence/arousal is closest to the target.
    # Tiebreak: prefer the sample whose BPM is closest to the target tempo.
    sub = df[df["type"] == typ].copy()
    if sub.empty:
        return None
    sub["dist"] = np.sqrt((sub["valence"]-target_val)**2 + (sub["arousal"]-target_aro)**2)
    sub["tempo_diff"] = (sub["bpm"] - TEMPO).abs().fillna(0)
    sub = sub.sort_values(["dist","tempo_diff"])
    return sub.iloc[0]


# ============ RENDER ============

def _load_prepare(path: str, bpm: Optional[float], key: Optional[str]) -> np.ndarray:
    # Load a sample and prepare it for mixing:
    # 1. Time-stretch to match target TEMPO (clamped to 0.5x–2.0x to avoid artifacts)
    # 2. Pitch-shift to match KEY_TARGET
    # 3. Normalize loudness to -18 dB RMS
    y, sr = librosa.load(path, sr=SR, mono=True)
    if bpm and bpm > 0:
        rate = float(np.clip(TEMPO / float(bpm), 0.5, 2.0))
        y = librosa.effects.time_stretch(y, rate=rate)
    st = _semi_tone_shift(key, KEY_TARGET)
    if st != 0:
        y = librosa.effects.pitch_shift(y, sr=SR, n_steps=st)
    y = _loudness_normalize(y, target_db=-18.0)
    return y.astype(np.float32)

def _pattern_step(pattern: str) -> int:
    # Returns the spacing in beats for a "1/x" pattern (e.g. "1/2" -> 2 beats between hits).
    # "loop" and "hold" are handled separately in render_track.
    if pattern in ("loop", "hold"):
        return 0
    num, den = pattern.split("/")
    return int(den)

def render_track(target_val: float, target_aro: float,
                 out_path: str = OUT_WAV) -> Dict:
    # Main function - builds and exports the full mix as a WAV file.
    #
    # Steps:
    #   1. Select the emotionally closest sample for each instrument type
    #   2. Prepare each sample (time-stretch, pitch-shift, normalize)
    #   3. Place samples on their lane according to ARRANGE patterns
    #   4. Sum all lanes, soft-clip to prevent clipping, write WAV
    #   5. Return output path + metadata about the chosen samples

    df = load_samples_index()

    # Pick best sample per instrument type
    picks: Dict[str, pd.Series] = {}
    for typ in ARRANGE:
        best = select_best_by_emotion(df, typ, target_val, target_aro)
        if best is not None:
            picks[typ] = best

    total = bars_to_samples(BARS_TOTAL)
    mix = np.zeros(total, dtype=np.float32)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    for typ, row in picks.items():
        y = _load_prepare(row["path"], row.get("bpm"), row.get("key"))
        if len(y) == 0:
            continue

        start = bars_to_samples(ARRANGE[typ]["bars"][0] - 1)
        end   = min(bars_to_samples(ARRANGE[typ]["bars"][1] - 1), total)
        pattern = ARRANGE[typ]["pattern"]
        lane = np.zeros(total, dtype=np.float32)

        if pattern == "hold":
            # Stretch or tile the sample to fill the entire slot
            need = end - start
            if need <= 0:
                continue
            y_use = np.tile(y, int(np.ceil(need / len(y))))[:need] if len(y) < need else y[:need]
            lane[start:start+len(y_use)] += y_use

        elif pattern == "loop":
            # Repeat the sample end-to-end until the slot is filled
            pos = start
            while pos < end:
                seg = y[:max(0, end - pos)] if pos + len(y) > end else y
                if len(seg) > 0:
                    lane[pos:pos+len(seg)] += seg
                pos += len(seg)

        else:
            # "1/x" - fire a one-shot every x beats across the slot
            step = beats_to_samples(_pattern_step(pattern))
            if step <= 0:
                continue
            one_shot = y[:beats_to_samples(1)] if typ == "kick" else y
            pos = start
            while pos < end:
                seg = one_shot[:max(0, end - pos)] if pos + len(one_shot) > end else one_shot
                if len(seg) > 0:
                    lane[pos:pos+len(seg)] += seg
                pos += step

        lane = np.clip(lane, -1.0, 1.0)
        mix += lane

    # Soft-clip: if the summed mix exceeds 1.0, scale it down to 0.98
    peak = float(np.max(np.abs(mix)) + 1e-9)
    if peak > 1.0:
        mix = mix / peak * 0.98

    sf.write(out_path, mix, SR, subtype="PCM_16")

    picks_out = {
        typ: {
            "path":    str(row["path"]),
            "bpm":     float(row["bpm"]) if pd.notna(row["bpm"]) else None,
            "key":     row["key"] if pd.notna(row["key"]) else None,
            "valence": float(row["valence"]),
            "arousal": float(row["arousal"]),
        }
        for typ, row in picks.items()
    }

    return {"output": out_path, "tempo": TEMPO, "key": KEY_TARGET, "picks": picks_out}


if __name__ == "__main__":
    info = render_track(target_val=0.65, target_aro=0.55, out_path=OUT_WAV)
    print("mix:", info["output"])
    print("picks:", info["picks"])
