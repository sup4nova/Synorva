# backend/tests/test_label_picture_emotions.py
# Unit tests for the deterministic valence/arousal heuristic and emotion mapping.
# No model or dataset required - pure function tests.

import pandas as pd
import pytest

from backend.label_picture_emotions import _z, compute_valence_arousal_images, map_to_emotion


def test_z_score_normalises_to_zero_mean_unit_std():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    z = _z(s)
    assert z.mean() == pytest.approx(0.0, abs=1e-9)
    assert z.std(ddof=0) == pytest.approx(1.0, abs=1e-9)


def test_z_score_constant_column_returns_zeros():
    s = pd.Series([5.0, 5.0, 5.0])
    z = _z(s)
    assert (z == 0).all()


def _base_df(n=4, **overrides):
    """Minimal feature DataFrame with all columns compute_valence_arousal_images needs."""
    data = {
        "brightness_mean": [0.5] * n,
        "saturation_mean": [0.5] * n,
        "contrast_std":    [0.5] * n,
        "colorfulness":    [50.0] * n,
        "warmth":          [0.0] * n,
        "sharpness":       [1000.0] * n,
        "edge_density":    [50.0] * n,
        "faces_ratio":     [0.0] * n,
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_brighter_image_has_higher_valence():
    df = _base_df(brightness_mean=[0.1, 0.3, 0.7, 0.9])
    va = compute_valence_arousal_images(df)
    # brightness is monotonically increasing across rows -> valence should follow
    assert va["valence"].is_monotonic_increasing


def test_higher_contrast_has_higher_arousal():
    df = _base_df(contrast_std=[0.1, 0.3, 0.7, 0.9])
    va = compute_valence_arousal_images(df)
    assert va["arousal"].is_monotonic_increasing


@pytest.mark.parametrize("v,a,expected", [
    (0.7, 1.05, "euphoric"),
    (-0.7, 1.05, "aggressive"),
    (0.45, -0.6, "warm"),
    (-0.65, -0.7, "melancholic"),
])
def test_map_to_emotion_known_regions(v, a, expected):
    assert map_to_emotion(v, a) == expected


def test_map_to_emotion_always_returns_valid_label():
    from backend.label_picture_emotions import EMOTIONS
    for v in (-1.5, -0.5, 0.0, 0.5, 1.5):
        for a in (-1.5, -0.5, 0.0, 0.5, 1.5):
            assert map_to_emotion(v, a) in EMOTIONS


def test_label_image_dataframe_does_not_mutate_input():
    from backend.label_picture_emotions import label_image_dataframe
    df = _base_df()
    original_cols = list(df.columns)
    labeled = label_image_dataframe(df)
    assert list(df.columns) == original_cols  # input untouched
    assert {"valence", "arousal", "emotion"}.issubset(labeled.columns)
