# backend/test_pipeline.py
# End-to-end reliability test for the Synorva pipeline.
# Generates synthetic images and runs them through each processing stage.
# No real photos or audio samples required.
#
# Usage:
#   python -m backend.test_pipeline       (from repo root)
#   python test_pipeline.py               (from backend/ directory)
#
# Stages:
#   1. Visual feature extraction + emotion labeling  (always runs)
#   2. ML valence/arousal prediction                 (skipped if model .pkl missing)
#   3. Audio track rendering                         (skipped if samples_index.csv missing)
#
# Exit code: 0 if score >= 70%, 1 otherwise (CI-friendly)

import sys
import numpy as np
import cv2
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.image_analysis import extract_image_features
from backend.label_picture_emotions import label_image_dataframe
import pandas as pd


# --- Synthetic image generators ---

def solid_bgr(b, g, r, w=256, h=256) -> np.ndarray:
    """Create a flat solid-color image in BGR format."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (b, g, r)
    return img

def noisy_bgr(base_bgr, noise_std=60, w=256, h=256) -> np.ndarray:
    """Create a noisy image from a base color - simulates texture and edge complexity."""
    img = solid_bgr(*base_bgr, w=w, h=h).astype(np.int16)
    noise = np.random.default_rng(42).integers(-noise_std, noise_std, (h, w, 3), dtype=np.int16)
    return np.clip(img + noise, 0, 255).astype(np.uint8)

def gradient_bgr(from_bgr, to_bgr, w=256, h=256) -> np.ndarray:
    """Create a horizontal gradient between two BGR colors."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        t = x / (w - 1)
        img[:, x] = [int(from_bgr[c] * (1 - t) + to_bgr[c] * t) for c in range(3)]
    return img


# --- Test cases ---
# Each case defines the expected direction of valence and arousal:
#   "high"  → score should be positive
#   "low"   → score should be negative
#   "any"   → no directional assertion (still checks feature ranges)

TEST_CASES = [
    {
        "name":    "Bright yellow (joyful, energetic)",
        "img":     solid_bgr(0, 220, 255),          # pure yellow in BGR
        "valence": "high",   # warm + bright → positive valence
        "arousal": "any",
        "notes":   "Warm saturated color"
    },
    {
        "name":    "Dark blue (gloomy, calm)",
        "img":     solid_bgr(80, 30, 10),            # dark blue in BGR
        "valence": "low",    # cold + dark → negative valence
        "arousal": "low",    # flat uniform image → low arousal
        "notes":   "Cold dark color"
    },
    {
        "name":    "Very bright (serene)",
        "img":     solid_bgr(240, 240, 240),         # near-white
        "valence": "high",   # high brightness → high valence
        "arousal": "low",    # uniform → low arousal
        "notes":   "Very bright uniform image"
    },
    {
        "name":    "Black (melancholic)",
        "img":     solid_bgr(5, 5, 5),               # near-black
        "valence": "low",
        "arousal": "low",
        "notes":   "Very dark uniform image"
    },
    {
        "name":    "Noisy texture (tense)",
        "img":     noisy_bgr((100, 80, 80), noise_std=80),
        "valence": "any",
        "arousal": "high",   # strong noise → high edges, contrast, sharpness → high arousal
        "notes":   "High noise → high edge density / contrast / sharpness"
    },
    {
        "name":    "Saturated red (aggressive)",
        "img":     solid_bgr(0, 0, 200),             # bright red in BGR
        "valence": "any",
        "arousal": "any",
        "notes":   "Pure red, max saturation"
    },
    {
        "name":    "Warm-to-cool gradient",
        "img":     gradient_bgr((0, 180, 255), (130, 20, 0)),  # yellow → blue
        "valence": "any",
        "arousal": "any",
        "notes":   "Sanity check: all feature values should be in valid ranges"
    },
]


# --- Feature range sanity checks ---
# These bounds are physical limits - if a feature lands outside, something is broken.

FEATURE_RANGES = {
    "brightness_mean":  (0.0, 1.0),
    "saturation_mean":  (0.0, 1.0),
    "contrast_std":     (0.0, 1.0),
    "colorfulness":     (0.0, 200.0),
    "warmth":          (-1.0, 1.0),
    "edge_density":    (0.0, 255.0),
    "sharpness":       (0.0, 1e8),
    "faces_ratio":     (0.0, 1.0),
    "aspect_ratio":    (0.01, 100.0),
}


def check_feature_ranges(feats: dict) -> list[str]:
    """Return a list of error strings for any feature outside its expected range."""
    errors = []
    for k, (lo, hi) in FEATURE_RANGES.items():
        v = feats.get(k)
        if v is None:
            errors.append(f"  x Missing feature: {k}")
        elif not (lo <= float(v) <= hi):
            errors.append(f"  x {k} = {v:.4f} out of range [{lo}, {hi}]")
    return errors


def check_direction(feats: dict, direction: str, key: str) -> str | None:
    """
    Assert that valence or arousal goes in the expected direction.
    Returns an error string if the assertion fails, None if it passes.
    """
    if direction == "any":
        return None
    v = feats.get(key)
    if v is None:
        return f"  x Key '{key}' missing from result"
    if direction == "high" and float(v) < 0:
        return f"  x {key} = {v:.3f} expected positive"
    if direction == "low" and float(v) > 0:
        return f"  x {key} = {v:.3f} expected negative"
    return None


# --- Main test runner ---

def run_tests():
    passed   = 0
    failed   = 0
    warnings = []

    print("=" * 60)
    print("  SYNORVA - End-to-end reliability test")
    print("=" * 60)

    # Stage 1: Feature extraction + emotion labeling
    print("\n[1/3] Visual feature extraction & labeling\n")

    # Extract features from all test images into a single DataFrame
    rows = []
    for tc in TEST_CASES:
        feats = extract_image_features(tc["img"], file_name=tc["name"])
        feats["file"] = tc["name"]
        rows.append(feats)

    df        = pd.DataFrame(rows)
    df_labeled = label_image_dataframe(df)   # adds valence, arousal, emotion columns

    for tc in TEST_CASES:
        name = tc["name"]
        row  = df_labeled[df_labeled["file"] == name].iloc[0].to_dict()

        # Check feature values are physically plausible
        errors = check_feature_ranges(row)

        # Check valence and arousal go in the expected direction
        for axis in ("valence", "arousal"):
            err = check_direction(row, tc[axis], axis)
            if err:
                errors.append(err)

        icon = "OK" if not errors else "FAIL"
        print(f"[{icon}] {name}")
        print(f"   valence={row['valence']:.3f}  arousal={row['arousal']:.3f}"
              f"  emotion={row['emotion']}  ({tc['notes']})")
        if errors:
            for e in errors:
                print(e)
            failed += 1
        else:
            passed += 1
        print()

    # Stage 2: ML prediction (skipped if model not yet trained)
    print("\n[2/3] ML prediction (picture_valaro.pkl)\n")
    model_path = ROOT / "backend" / "models" / "picture_valaro.pkl"

    if not model_path.exists():
        print("  [SKIP] Model not found - skipping ML stage.")
        print("         Run first: python -m backend.train_picture_reg")
        warnings.append("picture_valaro.pkl missing - ML prediction not tested.")
    else:
        from backend.image_analysis import predict_valaro_from_bgr
        model_errors = []
        for tc in TEST_CASES:
            pred = predict_valaro_from_bgr(tc["img"])
            v, a = pred["valence"], pred["arousal"]
            # Predictions should land in a reasonable range around [-1.5, 1.5]
            if not (-1.5 < v < 1.5 and -1.5 < a < 1.5):
                model_errors.append(
                    f"  x {tc['name']} → valence={v:.3f} arousal={a:.3f} out of range"
                )
            else:
                print(f"  [OK] {tc['name']} → valence={v:.3f}  arousal={a:.3f}")

        if model_errors:
            for e in model_errors:
                print(e)
            failed += len(model_errors)
        else:
            passed += 1

    # Stage 3: Audio rendering (skipped if samples_index.csv missing)
    print("\n[3/3] Audio rendering (auto_arranger)\n")
    samples_csv = ROOT / "backend" / "data" / "samples_index.csv"

    if not samples_csv.exists():
        print("  [SKIP] samples_index.csv not found - skipping audio stage.")
        print("         Run first: python -m backend.pipeline")
        warnings.append("samples_index.csv missing - audio rendering not tested.")
    else:
        try:
            from backend.auto_arranger import render_track
            import tempfile, os

            # Write to a temp file so we don't overwrite the real mix
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            result  = render_track(target_val=0.5, target_aro=0.5, out_path=tmp_path)
            wav_size = Path(tmp_path).stat().st_size
            os.unlink(tmp_path)

            if wav_size < 1000:
                print(f"  [FAIL] WAV too small ({wav_size} bytes) - likely empty render")
                failed += 1
            else:
                print(f"  [OK] WAV generated ({wav_size // 1024} KB)"
                      f" - picks: {list(result['picks'].keys())}")
                passed += 1

            # Check that selected samples aren't emotionally far from the target
            target_v, target_a = 0.5, 0.5
            for typ, pick in result["picks"].items():
                dist = ((pick["valence"] - target_v)**2 + (pick["arousal"] - target_a)**2) ** 0.5
                if dist > 0.8:
                    msg = f"{typ}: emotional distance = {dist:.2f} (target={target_v},{target_a})"
                    print(f"  [WARN] {msg}")
                    warnings.append(msg)
            else:
                print("  [OK] Emotional consistency of selected samples OK")

        except Exception as e:
            print(f"  [FAIL] Render error: {e}")
            failed += 1

    # Final report
    total = passed + failed
    score = int(passed / total * 100) if total else 0

    print("\n" + "=" * 60)
    print(f"  RESULT: {passed}/{total} tests passed - Score: {score}%")

    if warnings:
        print(f"\n  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    * {w}")

    if score == 100:
        print("\n  Pipeline reliable. Good coding session!")
    elif score >= 70:
        print("\n  Pipeline partially functional. Check errors above.")
    else:
        print("\n  Pipeline unreliable. Inspect core modules.")

    print("=" * 60)
    return score


if __name__ == "__main__":
    score = run_tests()
    sys.exit(0 if score >= 70 else 1)