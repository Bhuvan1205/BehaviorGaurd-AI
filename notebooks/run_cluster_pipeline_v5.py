"""
BehaviorGuard-AI — V5 Peer Clustering Pipeline
================================================
Re-runs the full peer clustering pipeline as designed in V3/V5 notebooks.

Steps:
  1. Load the enriched feature dataset + HR (users) data
  2. Apply V5 role_group mapping
  3. Segment into Day / Evening / Night shifts
  4. Build one user-level behavioral profile per user per shift
  5. Apply StandardScaler + KMeans(n_clusters=4) per (shift, role_group)
  6. Export user_cluster_assignments.csv
  7. Train per-cluster IsolationForest models
  8. Export cluster_thresholds.json
  9. Print verification summary
"""

import os
import json
import pickle
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR     = os.path.dirname(BASE_DIR)          # BehaviorGaurd-AI root

FEATURE_CSV     = os.path.join(PROJECT_DIR, "data", "processed", "behavior_dataset_v5_features.csv")
USERS_CSV       = os.path.join(PROJECT_DIR, "data", "raw", "users.csv")
MODELS_DIR      = os.path.join(BASE_DIR, "models")
CLUSTER_DIR     = os.path.join(MODELS_DIR, "cluster_models")
ARTIFACTS_DIR   = os.path.join(BASE_DIR, "artifacts")

ASSIGNMENT_CSV  = os.path.join(PROJECT_DIR, "notebooks", "models", "cluster_models", "user_cluster_assignments.csv")
THRESHOLD_JSON  = os.path.join(CLUSTER_DIR, "cluster_thresholds.json")

os.makedirs(CLUSTER_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# V5 Role group mapping (all 46 roles → 11 groups)
ROLE_GROUP_MAP = {
    # SOFTWARE ENGINEERING
    "softwareengineer":          "software_engineering",
    "softwaredeveloper":         "software_engineering",
    "webdeveloper":              "software_engineering",
    "softwarequalityengineer":   "software_engineering",
    "testengineer":              "software_engineering",
    "computerprogrammer":        "software_engineering",
    "computerscientist":         "software_engineering",

    # INDUSTRIAL / HARDWARE ENGINEERING
    "electricalengineer":        "engineering",
    "mechanicalengineer":        "engineering",
    "materialsengineer":         "engineering",
    "industrialengineer":        "engineering",
    "fieldserviceengineer":      "engineering",
    "systemsengineer":           "engineering",
    "chiefengineer":             "engineering",
    "engineer":                  "engineering",
    "hardwareengineer":          "engineering",
    "healthsafetyengineer":      "engineering",

    # SCIENTIFIC / ANALYTICAL → research
    "scientist":                 "research",
    "physicist":                 "research",
    "statistician":              "research",
    "mathematician":             "research",
    "economist":                 "research",

    # OPERATIONS
    "productionlineworker":      "operations",
    "technician":                "operations",
    "labmanager":                "operations",
    "supervisor":                "operations",

    # SALES
    "salesman":                  "sales",

    # IT / ADMIN
    "itadmin":                   "it_admin",
    "securityguard":             "it_admin",

    # LOGISTICS
    "stockroomclerk":            "logistics",
    "purchasingclerk":           "logistics",

    # MANAGEMENT
    "manager":                   "management",
    "projectmanager":            "management",
    "director":                  "management",
    "vicepresident":             "management",
    "president":                 "management",

    # ADMIN STAFF (includes small merged groups)
    "administrativeassistant":   "admin_staff",
    "administrativestaff":       "admin_staff",
    "humanresourcespecialist":   "admin_staff",
    "instructionalcoordinator":  "admin_staff",
    "technicalwriter":           "admin_staff",
    "accountant":                "finance",
    "financialanalyst":          "finance",
    "attorney":                  "admin_staff",
    "nurse":                     "healthcare",
    "nursepractitioner":         "healthcare",
}

# Profile features (one row per user per shift)
PROFILE_FEATURES = [
    "mean_logon_count",
    "std_logon_count",
    "total_logon_volume",      # log-transformed
    "mean_unique_pcs",
    "std_unique_pcs",
    "mean_activity_hour",
    "activity_hour_std",
]

# IsolationForest input features (exactly 10, in spec order)
IF_FEATURES = [
    "z_logon",
    "z_pcs",
    "logon_deviation",
    "device_deviation",
    "device_ratio",
    "burst_score",
    "hour_deviation",
    "session_gap",
    "logon_logoff_ratio",
    "night_activity_flag",
]

# Shift hour ranges
SHIFT_MASKS = {
    "Day":     lambda h: (h >= 9) & (h <= 16),
    "Evening": lambda h: (h >= 17) & (h <= 21),
    "Night":   lambda h: (h >= 22) | (h <= 8),
}

N_CLUSTERS      = 4
RANDOM_STATE    = 42
IF_ESTIMATORS   = 200
IF_CONTAMINATION = 0.06
THRESHOLD_PCTILE = 1   # 1st percentile

# ─────────────────────────────────────────────────────────────────────────────
# STEP 0 — LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 0 — Loading datasets")
print("="*70)

print(f"  → Reading feature CSV: {FEATURE_CSV}")
df = pd.read_csv(FEATURE_CSV, low_memory=False)
print(f"     Shape: {df.shape}")

print(f"  → Reading users CSV: {USERS_CSV}")
users_df = pd.read_csv(USERS_CSV)
print(f"     Shape: {users_df.shape}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — NORMALISE / APPLY ROLE GROUP MAPPING
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 1 — Applying V5 role_group mapping")
print("="*70)

# The feature CSV already has a role_group column from V5 processing.
# We re-apply the mapping from the raw 'role' column to stay consistent
# with the V5 design spec.
if "role" in df.columns:
    role_clean = df["role"].str.lower().str.replace(" ", "")
    df["role_group"] = role_clean.map(ROLE_GROUP_MAP).fillna("other")
    print(f"  → role_group distribution:\n{df['role_group'].value_counts().to_string()}")
else:
    # Fall back to whatever role_group already exists in the dataset
    print("  → 'role' column not found; using existing 'role_group' column")
    if "role_group" not in df.columns:
        raise ValueError("Neither 'role' nor 'role_group' column found in feature CSV.")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — SHIFT SEGMENTATION
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 2 — Shift segmentation (Day 09–16, Evening 17–21, Night 22–08)")
print("="*70)

# 'hour' column already exists in the feature CSV
df["Shift"] = "Unknown"
for shift_name, mask_fn in SHIFT_MASKS.items():
    mask = mask_fn(df["hour"])
    df.loc[mask, "Shift"] = shift_name

print(f"  → Shift distribution:\n{df['Shift'].value_counts().to_string()}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — BUILD USER-LEVEL PROFILES (one row per user per shift)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 3 — Building user-level behavioral profiles")
print("="*70)

def build_user_profiles(df_shift):
    """Aggregate hourly rows → one row per user."""
    grp = df_shift.groupby("user")
    profiles = pd.DataFrame({
        "mean_logon_count":  grp["logon_count"].mean(),
        "std_logon_count":   grp["logon_count"].std().fillna(0),
        "total_logon_volume": np.log1p(grp["logon_count"].sum()),  # log-transformed
        "mean_unique_pcs":   grp["unique_pcs"].mean(),
        "std_unique_pcs":    grp["unique_pcs"].std().fillna(0),
        "mean_activity_hour": grp["hour"].mean(),
        "activity_hour_std": grp["hour"].std().fillna(0),
    })
    # Also carry role_group (take the mode per user)
    profiles["role_group"] = grp["role_group"].agg(lambda x: x.mode().iloc[0])
    return profiles.reset_index()  # user becomes a column

# Build profiles for each shift
shift_profiles = {}
for shift_name in ["Day", "Evening", "Night"]:
    df_shift = df[df["Shift"] == shift_name].copy()
    prof = build_user_profiles(df_shift)
    shift_profiles[shift_name] = prof
    print(f"  → {shift_name}: {len(prof)} unique users")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — KMEANS CLUSTERING (per shift × role_group)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 4 — Running KMeans(n_clusters=4) per shift × role_group")
print("="*70)

all_assignments = []   # will become user_cluster_assignments.csv
assigned_at = datetime.now(timezone.utc).isoformat()

# Also keep per-shift clustered dfs for IF training
clustered_hourly = {}   # {shift: {role_group: df_hourly_with_cluster}}

for shift_name, profiles_df in shift_profiles.items():
    clustered_hourly[shift_name] = {}
    role_groups = profiles_df["role_group"].unique()

    for rg in role_groups:
        rg_prof = profiles_df[profiles_df["role_group"] == rg].copy()

        # Skip tiny groups that can't form 4 clusters
        if len(rg_prof) < N_CLUSTERS * 2:
            print(f"  [SKIP] {shift_name} | {rg}: only {len(rg_prof)} users (< {N_CLUSTERS*2})")
            continue

        X = rg_prof[PROFILE_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0).values

        # Scale
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # KMeans
        kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        rg_prof = rg_prof.copy()
        rg_prof["cluster_id"] = labels

        print(f"  ✓ {shift_name} | {rg}: {len(rg_prof)} users → clusters {sorted(rg_prof['cluster_id'].unique())}")

        # Collect assignments
        for _, row in rg_prof.iterrows():
            all_assignments.append({
                "user_id":    row["user"],
                "shift":      shift_name,
                "role_group": rg,
                "cluster_id": int(row["cluster_id"]),
                "assigned_at": assigned_at,
            })

        # ------------------------------------------------------------------
        # Map cluster labels back to hourly records for IF training
        # ------------------------------------------------------------------
        df_shift_hourly = df[(df["Shift"] == shift_name) & (df["role_group"] == rg)].copy()
        user_cluster_map = rg_prof.set_index("user")["cluster_id"].to_dict()
        df_shift_hourly["cluster_id"] = df_shift_hourly["user"].map(user_cluster_map)
        df_shift_hourly = df_shift_hourly.dropna(subset=["cluster_id"])
        df_shift_hourly["cluster_id"] = df_shift_hourly["cluster_id"].astype(int)

        clustered_hourly[shift_name][rg] = df_shift_hourly

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — EXPORT user_cluster_assignments.csv
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 5 — Exporting user_cluster_assignments.csv")
print("="*70)

assignments_df = pd.DataFrame(all_assignments, columns=[
    "user_id", "shift", "role_group", "cluster_id", "assigned_at"
])

os.makedirs(os.path.dirname(ASSIGNMENT_CSV), exist_ok=True)
assignments_df.to_csv(ASSIGNMENT_CSV, index=False)
print(f"  → Saved: {ASSIGNMENT_CSV}")
print(f"  → Total rows: {len(assignments_df)}")
print(f"  → Unique user_ids: {assignments_df['user_id'].nunique()}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — TRAIN PER-CLUSTER ISOLATION FOREST MODELS
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 6 — Training IsolationForest per (shift, role_group, cluster_id)")
print("="*70)

cluster_thresholds = {}
model_count = 0

for shift_name in ["Day", "Evening", "Night"]:
    for rg, df_hourly in clustered_hourly.get(shift_name, {}).items():
        for cluster_id in sorted(df_hourly["cluster_id"].unique()):
            df_cluster = df_hourly[df_hourly["cluster_id"] == cluster_id].copy()

            if len(df_cluster) < 10:
                print(f"  [SKIP] {shift_name} | {rg} | cluster {cluster_id}: only {len(df_cluster)} rows")
                continue

            # Prepare feature matrix (exactly 10 features in spec order)
            X_if = df_cluster[IF_FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)

            # Convert boolean flags to int
            X_if = X_if.copy()
            for col in X_if.columns:
                if X_if[col].dtype == bool:
                    X_if[col] = X_if[col].astype(int)

            X_if = X_if.values.astype(float)

            # Train IsolationForest
            iforest = IsolationForest(
                n_estimators=IF_ESTIMATORS,
                contamination=IF_CONTAMINATION,
                random_state=RANDOM_STATE,
            )
            iforest.fit(X_if)

            # Calibrated threshold = 1st percentile of decision_function scores
            scores = iforest.decision_function(X_if)
            threshold = float(np.percentile(scores, THRESHOLD_PCTILE))

            # Build safe filename
            safe_rg    = rg.lower().replace(" ", "_")
            safe_shift = shift_name.lower()
            model_key  = f"{shift_name}_{safe_rg}_{cluster_id}"
            model_file = os.path.join(CLUSTER_DIR, f"{safe_shift}_{safe_rg}_{cluster_id}_if.pkl")

            with open(model_file, "wb") as f:
                pickle.dump(iforest, f)

            cluster_thresholds[model_key] = threshold
            model_count += 1

            print(f"  ✓ {model_key}: {len(df_cluster)} rows | threshold={threshold:.4f} | saved → {os.path.basename(model_file)}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — EXPORT cluster_thresholds.json
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 7 — Exporting cluster_thresholds.json")
print("="*70)

with open(THRESHOLD_JSON, "w") as f:
    json.dump(cluster_thresholds, f, indent=2)

print(f"  → Saved: {THRESHOLD_JSON}")
print(f"  → Total threshold keys: {len(cluster_thresholds)}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — VERIFICATION SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("STEP 8 — Verification Summary")
print("="*70)

total_unique_users = assignments_df["user_id"].nunique()
nan_check = assignments_df.isnull().any().any()

print(f"  ✅ Total unique users in CSV          : {total_unique_users}")
print(f"  ✅ Total rows in CSV                   : {len(assignments_df)}")
print(f"  ✅ Model files saved                   : {model_count}")
print(f"  ✅ Threshold keys in JSON              : {len(cluster_thresholds)}")
print(f"  ✅ NaN values in assignment CSV        : {nan_check}")
print(f"  ✅ global isolation_forest_model.pkl   : NOT modified (preserved)")

# Sanity checks
print("\n  — Shift distribution in assignments:")
print(assignments_df["Shift"].value_counts().to_string() if "Shift" in assignments_df.columns else assignments_df["shift"].value_counts().to_string())

print("\n  — Cluster ID distribution:")
print(assignments_df["cluster_id"].value_counts().sort_index().to_string())

print("\n  — Role group distribution:")
print(assignments_df["role_group"].value_counts().to_string())

print("\n" + "="*70)
print("Pipeline complete.")
print("="*70)
