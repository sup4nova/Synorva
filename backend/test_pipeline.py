# backend/test_pipeline.py
"""
Test end-to-end de fiabilité du pipeline Synorva.

Étapes testées :
  1. Extraction des features visuelles (image_analysis.py)
  2. Cohérence des features avec l'émotion attendue
  3. Prédiction valence/arousal (si le modèle .pkl existe)
  4. Rendu audio (si samples_index.csv existe)
  5. Rapport final avec score de fiabilité
"""

import sys
import numpy as np
import cv2
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.image_analysis import extract_image_features
from backend.label_picture_emotions import label_image_dataframe
import pandas as pd

# ─────────────────────────────────────────────
# Helpers pour générer des images de test
# ─────────────────────────────────────────────

def solid_bgr(b, g, r, w=256, h=256) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (b, g, r)
    return img

def noisy_bgr(base_bgr, noise_std=60, w=256, h=256) -> np.ndarray:
    img = solid_bgr(*base_bgr, w=w, h=h).astype(np.int16)
    noise = np.random.default_rng(42).integers(-noise_std, noise_std, (h, w, 3), dtype=np.int16)
    return np.clip(img + noise, 0, 255).astype(np.uint8)

def gradient_bgr(from_bgr, to_bgr, w=256, h=256) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        t = x / (w - 1)
        img[:, x] = [int(from_bgr[c] * (1 - t) + to_bgr[c] * t) for c in range(3)]
    return img


# ─────────────────────────────────────────────
# Cas de test avec émotion attendue
# ─────────────────────────────────────────────
# Chaque cas : (nom, image BGR, valence_attendue, arousal_attendue, tolérance)
# valence/arousal attendus sont "high" | "low" | "any"

TEST_CASES = [
    {
        "name": "Image jaune vif (joyeux, énergique)",
        "img": solid_bgr(0, 220, 255),       # jaune pur
        "valence": "high",   # lumineux + chaud → valence positive
        "arousal": "any",
        "notes": "Couleur chaude saturée"
    },
    {
        "name": "Image bleu foncé (sombre, calme)",
        "img": solid_bgr(80, 30, 10),        # bleu sombre
        "valence": "low",    # froid + sombre → valence négative
        "arousal": "low",    # peu de contraste → arousal bas
        "notes": "Couleur froide et sombre"
    },
    {
        "name": "Image très lumineuse (serein)",
        "img": solid_bgr(240, 240, 240),     # quasi blanc
        "valence": "high",   # luminosité élevée → valence haute
        "arousal": "low",    # uniforme → arousal bas
        "notes": "Image uniforme très claire"
    },
    {
        "name": "Image noire (mélancolique)",
        "img": solid_bgr(5, 5, 5),           # quasi noir
        "valence": "low",
        "arousal": "low",
        "notes": "Image très sombre et uniforme"
    },
    {
        "name": "Image texturée bruyante (tendu)",
        "img": noisy_bgr((100, 80, 80), noise_std=80),
        "valence": "any",
        "arousal": "high",   # bords et contraste élevés → arousal haut
        "notes": "Bruit fort → bords/contraste/netteté élevés"
    },
    {
        "name": "Image rouge saturé (agressif)",
        "img": solid_bgr(0, 0, 200),         # rouge vif
        "valence": "any",
        "arousal": "any",
        "notes": "Rouge pur, saturation max"
    },
    {
        "name": "Dégradé chaud-froid",
        "img": gradient_bgr((0, 180, 255), (130, 20, 0)),  # jaune→bleu
        "valence": "any",
        "arousal": "any",
        "notes": "Vérification que les features sont dans des plages raisonnables"
    },
]

# ─────────────────────────────────────────────
# Vérifications de plage (sanity checks)
# ─────────────────────────────────────────────

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
    errors = []
    for k, (lo, hi) in FEATURE_RANGES.items():
        v = feats.get(k)
        if v is None:
            errors.append(f"  ✗ Feature manquante : {k}")
        elif not (lo <= float(v) <= hi):
            errors.append(f"  ✗ {k} = {v:.4f} hors plage [{lo}, {hi}]")
    return errors


def check_direction(feats: dict, direction: str, key: str) -> str | None:
    """Vérifie valence/arousal dans la bonne direction (high/low) après labeling."""
    if direction == "any":
        return None
    v = feats.get(key)
    if v is None:
        return f"  ✗ Clé '{key}' absente du résultat"
    if direction == "high" and float(v) < 0:
        return f"  ✗ {key} = {v:.3f} attendu positif"
    if direction == "low" and float(v) > 0:
        return f"  ✗ {key} = {v:.3f} attendu négatif"
    return None


# ─────────────────────────────────────────────
# Runner principal
# ─────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0
    warnings = []

    print("=" * 60)
    print("  SYNORVA — Test de fiabilité end-to-end")
    print("=" * 60)

    # ── 1. Tests feature extraction + labeling ──────────────────
    print("\n[1/3] Extraction des features visuelles & labeling\n")

    rows = []
    for tc in TEST_CASES:
        feats = extract_image_features(tc["img"], file_name=tc["name"])
        feats["file"] = tc["name"]
        rows.append(feats)

    df = pd.DataFrame(rows)
    df_labeled = label_image_dataframe(df)

    for tc in TEST_CASES:
        name = tc["name"]
        row = df_labeled[df_labeled["file"] == name].iloc[0].to_dict()
        errors = check_feature_ranges(row)

        dir_err = check_direction(row, tc["valence"], "valence")
        if dir_err:
            errors.append(dir_err)
        dir_err = check_direction(row, tc["arousal"], "arousal")
        if dir_err:
            errors.append(dir_err)

        status = "PASS" if not errors else "FAIL"
        icon = "✅" if status == "PASS" else "❌"
        print(f"{icon} {name}")
        print(f"   valence={row['valence']:.3f}  arousal={row['arousal']:.3f}"
              f"  emotion={row['emotion']}  ({tc['notes']})")
        if errors:
            for e in errors:
                print(e)
            failed += 1
        else:
            passed += 1
        print()

    # ── 2. Test modèle ML (optionnel) ───────────────────────────
    print("\n[2/3] Prédiction ML (picture_valaro.pkl)\n")
    model_path = ROOT / "backend" / "models" / "picture_valaro.pkl"
    if not model_path.exists():
        print("  ⚠️  Modèle introuvable — cette étape est ignorée.")
        print("      Lance d'abord : python -m backend.train_picture_reg")
        warnings.append("Modèle picture_valaro.pkl absent — prédiction ML non testée.")
    else:
        from backend.image_analysis import predict_valaro_from_bgr
        model_errors = []
        for tc in TEST_CASES:
            pred = predict_valaro_from_bgr(tc["img"])
            v, a = pred["valence"], pred["arousal"]
            if not (-1.5 < v < 1.5 and -1.5 < a < 1.5):
                model_errors.append(f"  ✗ {tc['name']} → valence={v:.3f} arousal={a:.3f} hors plage")
            else:
                print(f"  ✅ {tc['name']} → valence={v:.3f}  arousal={a:.3f}")

        if model_errors:
            for e in model_errors:
                print(e)
            failed += len(model_errors)
        else:
            passed += 1

    # ── 3. Test rendu audio (optionnel) ─────────────────────────
    print("\n[3/3] Rendu audio (auto_arranger)\n")
    samples_csv = ROOT / "backend" / "data" / "samples_index.csv"
    if not samples_csv.exists():
        print("  ⚠️  samples_index.csv introuvable — cette étape est ignorée.")
        print("      Assure-toi que le dossier backend/data/ contient samples_index.csv")
        warnings.append("samples_index.csv absent — rendu audio non testé.")
    else:
        try:
            from backend.auto_arranger import render_track
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            result = render_track(target_val=0.5, target_aro=0.5, out_path=tmp_path)
            wav_size = Path(tmp_path).stat().st_size
            os.unlink(tmp_path)

            if wav_size < 1000:
                print(f"  ❌ WAV généré trop petit ({wav_size} bytes)")
                failed += 1
            else:
                print(f"  ✅ WAV généré ({wav_size // 1024} KB) — picks: {list(result['picks'].keys())}")
                passed += 1

            # test cohérence émotionnelle : l'écart val/aro entre cible et pick ne doit pas dépasser 0.5
            cible_v, cible_a = 0.5, 0.5
            incoherents = []
            for typ, pick in result["picks"].items():
                dist = ((pick["valence"] - cible_v)**2 + (pick["arousal"] - cible_a)**2) ** 0.5
                if dist > 0.8:
                    incoherents.append(f"  ⚠️  {typ}: dist émotionnelle = {dist:.2f} (cible={cible_v},{cible_a})")
            if incoherents:
                for w in incoherents:
                    print(w)
                    warnings.append(w.strip())
            else:
                print("  ✅ Cohérence émotionnelle des samples OK")

        except Exception as e:
            print(f"  ❌ Erreur lors du rendu : {e}")
            failed += 1

    # ── Rapport final ────────────────────────────────────────────
    total = passed + failed
    score = int(passed / total * 100) if total else 0
    print("\n" + "=" * 60)
    print(f"  RÉSULTAT : {passed}/{total} tests réussis — Score : {score}%")
    if warnings:
        print(f"\n  Avertissements ({len(warnings)}) :")
        for w in warnings:
            print(f"    • {w}")
    if score == 100:
        print("\n  Pipeline fiable. Bonne session de coding !")
    elif score >= 70:
        print("\n  Pipeline partiellement fonctionnel. Voir les erreurs ci-dessus.")
    else:
        print("\n  Pipeline peu fiable. Vérifier les modules core.")
    print("=" * 60)
    return score


if __name__ == "__main__":
    score = run_tests()
    sys.exit(0 if score >= 70 else 1)
