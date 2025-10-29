# backend/train_picture_reg.py
import pandas as pd, joblib, json
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from pathlib import Path
from image_analysis import FEATURE_COLS  # 👈

CSV_IN  = "backend/data/picture_features_labeled.csv"
MODEL_P = "backend/models/picture_valaro.pkl"
META_P  = "backend/models/picture_valaro.meta.json"
SEED    = 42

df = pd.read_csv(CSV_IN)

# X = uniquement les colonnes numériques attendues
X = df[FEATURE_COLS].copy()
Y = df[["valence","arousal"]].copy()

# (sécurité) impute NaN
X = X.fillna(X.median(numeric_only=True))
Y = Y.fillna(Y.median(numeric_only=True))

Xtr, Xte, Ytr, Yte = train_test_split(X, Y, test_size=0.2, random_state=SEED)

base = RandomForestRegressor(n_estimators=400, random_state=SEED, n_jobs=-1)
model = MultiOutputRegressor(base)

print("⏳ Entraînement…")
model.fit(Xtr, Ytr)
print("✅ OK.")

pred = model.predict(Xte)
mae_val = mean_absolute_error(Yte["valence"], pred[:,0])
mae_aro = mean_absolute_error(Yte["arousal"], pred[:,1])
r2_val  = r2_score(Yte["valence"],  pred[:,0])
r2_aro  = r2_score(Yte["arousal"],  pred[:,1])
print(f"MAE val={mae_val:.3f}  aro={mae_aro:.3f} | R² val={r2_val:.3f}  aro={r2_aro:.3f}")

Path(MODEL_P).parent.mkdir(parents=True, exist_ok=True)
joblib.dump(model, MODEL_P)

meta = {
    "feature_cols": FEATURE_COLS,  # 👈 ordre canonique
    "targets": ["valence","arousal"],
    "metrics": {"MAE":{"valence":float(mae_val),"arousal":float(mae_aro)},
                "R2":{"valence":float(r2_val),"arousal":float(r2_aro)}}
}
Path(META_P).write_text(json.dumps(meta, indent=2), encoding="utf-8")
print(f"💾 {MODEL_P}\n🗂  {META_P}")
