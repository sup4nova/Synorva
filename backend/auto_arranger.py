# backend/auto_arranger.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd
import librosa
import soundfile as sf

# ============ CONFIG MINIMALE ============
SR = 44100                 # sample rate du rendu
TEMPO = 124.0              # BPM cible
KEY_TARGET = "Am"          # clé cible (simplifiée)
BARS_TOTAL = 32            # longueur totale en mesures
SIG_BEATS = 4              # signature 4/4

# Arrangement très simple : où placer chaque type
# bars=(start,end) en mesures inclusives start, exclusives end
ARRANGE = {
    "kick":   {"bars": (1, 33), "pattern": "1/1"},   # chaque beat
    "bass":   {"bars": (5, 33), "pattern": "1/2"},   # un beat sur deux
    "melody": {"bars": (9, 25), "pattern": "loop"},  # boucle continue
    "riser":  {"bars": (29, 33), "pattern": "hold"}, # tenir la fin
    # ajoute d'autres types selon ton CSV: "snare", "hihat", "vocal", ...
}

SAMPLES_CSV = "backend/data/samples_index.csv"  # path,type,bpm,key,valence,arousal,bars,sample_rate
OUT_WAV     = "backend/static/renders/mix.wav"  # sortie

# ============ UTILS TEMPO ============
def beats_to_samples(beats: float, sr=SR, tempo=TEMPO) -> int:
    seconds = (60.0 / tempo) * beats
    return int(seconds * sr)

def bars_to_samples(bars: float, sr=SR, tempo=TEMPO, sig_beats=SIG_BEATS) -> int:
    return beats_to_samples(bars * sig_beats, sr=sr, tempo=tempo)

# ============ MUSIQUE (PITCH/TEMPO) ============
def _semi_tone_shift(src_key: Optional[str], tgt_key: Optional[str]) -> int:
    """Décalage approximatif en demi-tons (racine seulement, simplifié)."""
    if not src_key or not tgt_key:
        return 0
    order = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    def root(k: str) -> str:
        k = k.replace("min","m").replace("maj","").upper()
        return k.replace("M","")[:2].replace("H","")  # robustesse grossière
    try:
        return order.index(root(tgt_key)) - order.index(root(src_key))
    except Exception:
        return 0

def _loudness_normalize(y: np.ndarray, target_db=-18.0) -> np.ndarray:
    rms = np.sqrt(np.mean(y**2) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    gain = 10 ** ((target_db - db)/20)
    return y * gain

# ============ DATA ============
_df_cache: Optional[pd.DataFrame] = None

def load_samples_index(path=SAMPLES_CSV, force_reload=False) -> pd.DataFrame:
    global _df_cache
    if _df_cache is None or force_reload:
        df = pd.read_csv(path)
        needed = {"path","type","bpm","key","valence","arousal"}
        missing = needed - set(df.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes dans {path}: {missing}")
        _df_cache = df
    return _df_cache

# ============ SELECTION ============
def select_best_by_emotion(df: pd.DataFrame, typ: str, target_val: float, target_aro: float) -> Optional[pd.Series]:
    sub = df[df["type"] == typ].copy()
    if sub.empty:
        return None
    sub["dist"] = np.sqrt((sub["valence"]-target_val)**2 + (sub["arousal"]-target_aro)**2)
    sub["tempo_diff"] = (sub["bpm"] - TEMPO).abs().fillna(0)
    sub = sub.sort_values(["dist","tempo_diff"])
    return sub.iloc[0]

# ============ RENDER ============
def _load_prepare(path: str, bpm: Optional[float], key: Optional[str]) -> np.ndarray:
    y, sr = librosa.load(path, sr=SR, mono=True)
    # time-stretch vers tempo cible (si BPM fourni)
    if bpm and bpm > 0:
        rate = TEMPO / float(bpm)
        # clamp léger pour éviter artefacts extrêmes
        rate = float(np.clip(rate, 0.5, 2.0))
        y = librosa.effects.time_stretch(y, rate)
    # pitch-shift vers KEY_TARGET (simple)
    st = _semi_tone_shift(key, KEY_TARGET)
    if st != 0:
        y = librosa.effects.pitch_shift(y, sr=SR, n_steps=st)
    # normalisation simple
    y = _loudness_normalize(y, target_db=-18.0)
    return y.astype(np.float32)

def _pattern_step(pattern: str) -> int:
    """Retourne le pas en beats pour 1/1, 1/2, 1/4. 'loop' et 'hold' gérés ailleurs."""
    if pattern in ("loop","hold"):
        return 0
    num, den = pattern.split("/")
    return int(den)

def render_track(target_val: float, target_aro: float,
                 out_path: str = OUT_WAV) -> Dict:
    df = load_samples_index()
    picks: Dict[str, pd.Series] = {}
    for typ, cfg in ARRANGE.items():
        best = select_best_by_emotion(df, typ, target_val, target_aro)
        if best is not None:
            picks[typ] = best

    total = bars_to_samples(BARS_TOTAL)
    mix = np.zeros(total, dtype=np.float32)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    for typ, row in picks.items():
        y = _load_prepare(row["path"], row.get("bpm", None), row.get("key", None))
        if len(y) == 0:
            continue
        start_bar, end_bar = ARRANGE[typ]["bars"]
        start = bars_to_samples(start_bar-1)
        end   = bars_to_samples(end_bar-1)  # exclusif sur fin
        end   = min(end, total)

        pattern = ARRANGE[typ]["pattern"]
        lane = np.zeros(total, dtype=np.float32)

        if pattern == "hold":
            need = end - start
            if need <= 0: continue
            if len(y) < need:
                reps = int(np.ceil(need / len(y)))
                y_use = np.tile(y, reps)[:need]
            else:
                y_use = y[:need]
            lane[start:start+len(y_use)] += y_use

        elif pattern == "loop":
            pos = start
            while pos < end:
                seg = y
                if pos+len(seg) > end:
                    seg = seg[:max(0, end - pos)]
                if len(seg) > 0:
                    lane[pos:pos+len(seg)] += seg
                pos += len(seg)

        else:
            # "1/x" -> tous les 'x' beats, one-shot
            step_beats = _pattern_step(pattern)
            if step_beats <= 0: continue
            step = beats_to_samples(step_beats)
            one_shot = y[:beats_to_samples(1)] if typ == "kick" else y
            pos = start
            while pos < end:
                seg = one_shot
                if pos+len(seg) > end:
                    seg = seg[:max(0, end - pos)]
                if len(seg) > 0:
                    lane[pos:pos+len(seg)] += seg
                pos += step

        # mixage simple
        lane = np.clip(lane, -1.0, 1.0)
        mix += lane

    # soft clip final
    peak = float(np.max(np.abs(mix)) + 1e-9)
    if peak > 1.0:
        mix = mix / peak * 0.98

    sf.write(out_path, mix, SR, subtype="PCM_16")

    # résume les choix
    picks_out = {
        typ: {
            "path": str(row["path"]),
            "bpm": float(row["bpm"]) if pd.notna(row["bpm"]) else None,
            "key": row["key"] if pd.notna(row["key"]) else None,
            "valence": float(row["valence"]),
            "arousal": float(row["arousal"]),
        }
        for typ, row in picks.items()
    }

    return {
        "output": out_path,
        "tempo": TEMPO,
        "key": KEY_TARGET,
        "picks": picks_out,
    }

if __name__ == "__main__":
    info = render_track(target_val=0.65, target_aro=0.55, out_path=OUT_WAV)
    print("✅ mix:", info["output"])
    print("🎚 picks:", info["picks"])
