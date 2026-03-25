"""
Re-train the IsolationForest model using StandardScaler-transformed features.

Uses the EXACT same hyperparameters from V6.ipynb (execution_count 30):
  - n_estimators=200
  - contamination=0.06
  - random_state=42
  - n_jobs=-1

Pipeline:
  1. Load training CSV (3.37M rows)
  2. Extract 10 features in feature_list.json order
  3. Scale with the new StandardScaler (just saved)
  4. Train IsolationForest
  5. Save to notebooks/models/isolation_forest_model.pkl
"""
import pandas as pd
import numpy as np
import json
import joblib
from sklearn.ensemble import IsolationForest

# ── 1. Load training data ──────────────────────────────────────────────
print("Loading training data...")
df = pd.read_csv("data/processed/behavior_dataset_v5_features.csv")
print(f"  Rows: {df.shape[0]:,}  Columns: {df.shape[1]}")

# ── 2. Load canonical feature order ────────────────────────────────────
with open("notebooks/artifacts/feature_list.json", "r") as f:
    features = json.load(f)
print(f"  Features: {features}")

# ── 3. Extract feature matrix ─────────────────────────────────────────
X_raw = df[features].values
print(f"  Feature matrix: {X_raw.shape}")

# ── 4. Load the new StandardScaler and transform ──────────────────────
scaler = joblib.load("notebooks/models/feature_scaler.pkl")
print(f"  Scaler type: {type(scaler).__name__}")
X_scaled = scaler.transform(X_raw)
print(f"  Scaled matrix: {X_scaled.shape}")
print(f"  Scaled mean (sample): {X_scaled.mean(axis=0)[:3]}")
print(f"  Scaled std  (sample): {X_scaled.std(axis=0)[:3]}")

# ── 5. Train IsolationForest (V6 exact params) ────────────────────────
print("\nTraining IsolationForest (this may take a few minutes)...")
iso = IsolationForest(
    n_estimators=200,
    contamination=0.06,
    random_state=42,
    n_jobs=-1
)
# Train on a named DataFrame so sklearn stores feature_names_in_
X_scaled_df = pd.DataFrame(X_scaled, columns=features)
iso.fit(X_scaled_df)
print("  Training complete!")

# ── 6. Quick sanity check ─────────────────────────────────────────────
preds = iso.predict(X_scaled[:1000])
n_anomalies = (preds == -1).sum()
print(f"\n  Sanity check (first 1000 rows): {n_anomalies} anomalies detected")

# ── 7. Save model ─────────────────────────────────────────────────────
joblib.dump(iso, "notebooks/models/isolation_forest_model.pkl")
print("\n✅ Saved new IsolationForest to notebooks/models/isolation_forest_model.pkl")
