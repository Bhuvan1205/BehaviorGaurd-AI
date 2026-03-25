"""
Re-fit the feature scaler using StandardScaler on the SAME 10 features
from the training dataset (behavior_dataset_v5_features.csv).

DO NOT retrain the model — only the scaler.
"""
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib
import json

# ── 1. Load training data ───────────────────────────────────────────────
df = pd.read_csv("data/processed/behavior_dataset_v5_features.csv")
print(f"Loaded training data: {df.shape[0]} rows, {df.shape[1]} columns")

# ── 2. Load the canonical feature order ─────────────────────────────────
with open("notebooks/artifacts/feature_list.json", "r") as f:
    features = json.load(f)

print(f"Feature order: {features}")

# ── 3. Extract feature matrix ──────────────────────────────────────────
X = df[features].values
print(f"Feature matrix shape: {X.shape}")
print(f"\nPre-scaling stats (sample):")
print(pd.DataFrame(X, columns=features).describe().to_string())

# ── 4. Fit StandardScaler ──────────────────────────────────────────────
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

print(f"\nPost-scaling stats (sample):")
print(pd.DataFrame(X_scaled, columns=features).describe().to_string())

# ── 5. Save scaler ────────────────────────────────────────────────────
joblib.dump(scaler, "notebooks/models/feature_scaler.pkl")
print("\n✅ Saved new StandardScaler to notebooks/models/feature_scaler.pkl")
