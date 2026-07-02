# backend/train_picture_reg.py
# Trains a Random Forest regressor to predict valence and arousal from image features.
# Run this once after building data/picture_features_labeled.csv.
#
# Input:  data/picture_features_labeled.csv   (built by build_picture_dataset.py)
# Output: backend/models/picture_valaro.pkl        (model, loaded at runtime)
#         backend/models/picture_valaro.meta.json  (feature order + metrics)
#
# Usage:
#   python -m backend.train_picture_reg

import pandas as pd
import joblib
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor

from backend.image_analysis import FEATURE_COLS   # canonical list of 11 feature names

ROOT    = Path(__file__).resolve().parents[1]
CSV_IN  = ROOT / "data"            / "picture_features_labeled.csv"
MODEL_P = ROOT / "backend/models" / "picture_valaro.pkl"
META_P  = ROOT / "backend/models" / "picture_valaro.meta.json"
SEED    = 42


def main():
    # - Load dataset
    if not CSV_IN.exists():
        print(f"[ERROR] Labeled CSV not found: {CSV_IN}")
        print("        Run first: python -m backend.pipeline --images")
        return

    df = pd.read_csv(CSV_IN)
    print(f"Loaded {len(df)} samples from {CSV_IN}")

    # - Feature matrix and targets
    X = df[FEATURE_COLS].copy()          # 11 visual features
    Y = df[["valence", "arousal"]].copy()  # two regression targets

    # Fill any missing values with column medians (safety net for bad extractions)
    X = X.fillna(X.median(numeric_only=True))
    Y = Y.fillna(Y.median(numeric_only=True))

    # - Train / test split
    # 80% training, 20% held out for evaluation - same seed for reproducibility
    Xtr, Xte, Ytr, Yte = train_test_split(X, Y, test_size=0.2, random_state=SEED)

    # - Model
    # MultiOutputRegressor trains one RandomForest per target (valence, arousal).
    # 400 trees gives stable predictions; n_jobs=-1 uses all CPU cores.
    base  = RandomForestRegressor(n_estimators=400, random_state=SEED, n_jobs=-1)
    model = MultiOutputRegressor(base)

    print("Training...")
    model.fit(Xtr, Ytr)
    print("Done.")

    # - Evaluation
    pred    = model.predict(Xte)
    mae_val = mean_absolute_error(Yte["valence"], pred[:, 0])
    mae_aro = mean_absolute_error(Yte["arousal"], pred[:, 1])
    r2_val  = r2_score(Yte["valence"],  pred[:, 0])
    r2_aro  = r2_score(Yte["arousal"],  pred[:, 1])
    print(f"MAE  valence={mae_val:.3f}  arousal={mae_aro:.3f}")
    print(f"R²   valence={r2_val:.3f}   arousal={r2_aro:.3f}")
    # R² > 0.5 is reasonable; > 0.7 is good for this kind of heuristic-labeled data

    # - Save model
    MODEL_P.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_P)

    # Save metadata alongside the model so predict_valaro_from_bgr can
    # reconstruct the input vector in exactly the same column order as training
    meta = {
        "feature_cols": FEATURE_COLS,
        "targets":      ["valence", "arousal"],
        "metrics": {
            "MAE": {"valence": float(mae_val), "arousal": float(mae_aro)},
            "R2":  {"valence": float(r2_val),  "arousal": float(r2_aro)},
        },
    }
    META_P.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Model saved  → {MODEL_P}")
    print(f"Metadata     → {META_P}")


if __name__ == "__main__":
    main()