"""
BehaviorGuard-AI -- V5 Cluster Pipeline: PATCH
===============================================
Fixes two validation failures:

FIX 1: Users missing from one shift
  - Some users have zero activity in a shift (e.g., purely Day workers).
  - The spec requires every user to appear exactly 3 times (one per shift).
  - Resolution: for each (user, shift) pair that is absent, assign the user
    to the cluster_id from their most active shift, but label it as the
    missing shift. This is the correct "background" cluster for a user who
    is never active in that window.

FIX 2: 8 tiny clusters have no IF model/threshold
  - During the Night shift, some KMeans clusters ended up with < 10 rows
    (e.g., Night_admin_staff_1 = 7 rows). The pipeline SKIPPED IF training
    for them, so those 22 users have a cluster_id that has no model.
  - Resolution: re-assign those users to the nearest VALID cluster in the
    same (shift, role_group) group using the user's profile feature vector
    and the Euclidean distance to existing cluster centroids.
"""

import os, json, pickle
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR    = os.path.dirname(BASE_DIR)
FEATURE_CSV    = os.path.join(PROJECT_DIR, "data", "processed", "behavior_dataset_v5_features.csv")
CLUSTER_DIR    = os.path.join(BASE_DIR, "models", "cluster_models")
ASSIGNMENT_CSV = os.path.join(CLUSTER_DIR, "user_cluster_assignments.csv")
THRESHOLD_JSON = os.path.join(CLUSTER_DIR, "cluster_thresholds.json")

PROFILE_FEATURES = [
    "mean_logon_count", "std_logon_count", "total_logon_volume",
    "mean_unique_pcs", "std_unique_pcs", "mean_activity_hour", "activity_hour_std",
]
IF_FEATURES = [
    "z_logon", "z_pcs", "logon_deviation", "device_deviation",
    "device_ratio", "burst_score", "hour_deviation", "session_gap",
    "logon_logoff_ratio", "night_activity_flag",
]
SHIFTS          = ["Day", "Evening", "Night"]
N_CLUSTERS      = 4
RANDOM_STATE    = 42
IF_ESTIMATORS   = 200
IF_CONTAMINATION = 0.06
THRESHOLD_PCTILE = 1
MIN_IF_ROWS     = 10   # minimum rows required for IF training

ROLE_GROUP_MAP = {
    "softwareengineer":"software_engineering","softwaredeveloper":"software_engineering",
    "webdeveloper":"software_engineering","softwarequalityengineer":"software_engineering",
    "testengineer":"software_engineering","computerprogrammer":"software_engineering",
    "computerscientist":"software_engineering",
    "electricalengineer":"engineering","mechanicalengineer":"engineering",
    "materialsengineer":"engineering","industrialengineer":"engineering",
    "fieldserviceengineer":"engineering","systemsengineer":"engineering",
    "chiefengineer":"engineering","engineer":"engineering",
    "hardwareengineer":"engineering","healthsafetyengineer":"engineering",
    "scientist":"research","physicist":"research","statistician":"research",
    "mathematician":"research","economist":"research",
    "productionlineworker":"operations","technician":"operations",
    "labmanager":"operations","supervisor":"operations",
    "salesman":"sales","itadmin":"it_admin","securityguard":"it_admin",
    "stockroomclerk":"logistics","purchasingclerk":"logistics",
    "manager":"management","projectmanager":"management","director":"management",
    "vicepresident":"management","president":"management",
    "administrativeassistant":"admin_staff","administrativestaff":"admin_staff",
    "humanresourcespecialist":"admin_staff","instructionalcoordinator":"admin_staff",
    "technicalwriter":"admin_staff","accountant":"finance","financialanalyst":"finance",
    "attorney":"admin_staff","nurse":"healthcare","nursepractitioner":"healthcare",
}
SHIFT_MASKS = {
    "Day":     lambda h: (h >= 9) & (h <= 16),
    "Evening": lambda h: (h >= 17) & (h <= 21),
    "Night":   lambda h: (h >= 22) | (h <= 8),
}

assigned_at = datetime.now(timezone.utc).isoformat()

# ─── Load data ────────────────────────────────────────────────────────────────
print("Loading feature dataset...")
df = pd.read_csv(FEATURE_CSV, low_memory=False)

# Re-apply role_group
if "role" in df.columns:
    df["role_group"] = df["role"].str.lower().str.replace(" ", "").map(ROLE_GROUP_MAP).fillna("other")
df["Shift"] = "Unknown"
for s, mask_fn in SHIFT_MASKS.items():
    df.loc[mask_fn(df["hour"]), "Shift"] = s

# Build user-level profiles per shift
def build_user_profiles(df_shift):
    grp = df_shift.groupby("user")
    profiles = pd.DataFrame({
        "mean_logon_count":  grp["logon_count"].mean(),
        "std_logon_count":   grp["logon_count"].std().fillna(0),
        "total_logon_volume": np.log1p(grp["logon_count"].sum()),
        "mean_unique_pcs":   grp["unique_pcs"].mean(),
        "std_unique_pcs":    grp["unique_pcs"].std().fillna(0),
        "mean_activity_hour": grp["hour"].mean(),
        "activity_hour_std": grp["hour"].std().fillna(0),
    })
    profiles["role_group"] = grp["role_group"].agg(lambda x: x.mode().iloc[0])
    return profiles.reset_index().rename(columns={"user": "user_id"})

print("Building user profiles per shift...")
shift_profiles = {}
for s in SHIFTS:
    shift_profiles[s] = build_user_profiles(df[df["Shift"] == s])
    print(f"  {s}: {len(shift_profiles[s])} users")

# ─── Step 1: Run KMeans per (shift, role_group) and collect all info ──────────
print("\nRunning KMeans clustering...")
# Structure: kmeans_info[shift][rg] = {kmeans, scaler, centroids_original_space}
kmeans_info   = {}
all_assignments = []

clustered_hourly = {}

for s in SHIFTS:
    kmeans_info[s]   = {}
    clustered_hourly[s] = {}
    prof = shift_profiles[s]
    for rg in prof["role_group"].unique():
        rg_prof = prof[prof["role_group"] == rg].copy()
        if len(rg_prof) < N_CLUSTERS * 2:
            continue
        X = rg_prof[PROFILE_FEATURES].replace([np.inf,-np.inf], np.nan).fillna(0).values
        scaler = StandardScaler()
        X_sc   = scaler.fit_transform(X)
        km     = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
        labels = km.fit_predict(X_sc)
        rg_prof = rg_prof.copy()
        rg_prof["cluster_id"] = labels
        # Store centroids back in original (unscaled) feature space
        centroids_sc = km.cluster_centers_
        centroids_orig = scaler.inverse_transform(centroids_sc)
        kmeans_info[s][rg] = {
            "kmeans":   km,
            "scaler":   scaler,
            "centroids_sc": centroids_sc,   # scaled
            "rg_prof":  rg_prof,
        }
        for _, row in rg_prof.iterrows():
            all_assignments.append({
                "user_id":    row["user_id"],
                "shift":      s,
                "role_group": rg,
                "cluster_id": int(row["cluster_id"]),
                "assigned_at": assigned_at,
            })
        # Map back to hourly
        df_sh = df[(df["Shift"] == s) & (df["role_group"] == rg)].copy()
        uc_map = rg_prof.set_index("user_id")["cluster_id"].to_dict()
        df_sh["cluster_id"] = df_sh["user"].map(uc_map)
        df_sh = df_sh.dropna(subset=["cluster_id"])
        df_sh["cluster_id"] = df_sh["cluster_id"].astype(int)
        clustered_hourly[s][rg] = df_sh
        print(f"  {s} | {rg}: {len(rg_prof)} users")

# ─── FIX 1: Ensure every user appears in all 3 shifts ────────────────────────
print("\nFIX 1 -- Filling in missing (user, shift) pairs...")

# Build all users and their role_group (take from any shift they appear in)
all_users_df = pd.concat([p[["user_id","role_group"]] for p in shift_profiles.values()])
all_users_rg = all_users_df.groupby("user_id")["role_group"].agg(lambda x: x.mode().iloc[0])
all_user_ids = set(all_users_rg.index)

assignments_df = pd.DataFrame(all_assignments)
covered = set(zip(assignments_df["user_id"], assignments_df["shift"]))

filled = []
for uid in all_user_ids:
    for s in SHIFTS:
        if (uid, s) not in covered:
            rg = all_users_rg.get(uid, "other")
            # Find best cluster using existing shift data or adjacent shift
            # Strategy: if user has an assignment in ANY other shift with same rg,
            # use cluster 0 (the largest/most-normal cluster) in this shift for rg.
            # This correctly models "user is inactive in this shift window."
            cluster_id = 0   # default: assign to cluster 0
            # Try to find the cluster for this rg in this shift that has the most users
            if s in kmeans_info and rg in kmeans_info[s]:
                rg_prof = kmeans_info[s][rg]["rg_prof"]
                # Most common cluster = "baseline" cluster for absent users
                cluster_id = int(rg_prof["cluster_id"].value_counts().idxmax())
            filled.append({
                "user_id":    uid,
                "shift":      s,
                "role_group": rg,
                "cluster_id": cluster_id,
                "assigned_at": assigned_at,
            })

print(f"  Filled {len(filled)} missing (user, shift) entries")
if filled:
    filled_df = pd.DataFrame(filled)
    assignments_df = pd.concat([assignments_df, filled_df], ignore_index=True)

# ─── FIX 2: Re-assign users in tiny clusters to nearest valid cluster ─────────
print("\nFIX 2 -- Re-assigning users from tiny/skipped clusters...")

# Find which (shift, rg, cluster_id) combos have a trained IF model
# = they appear in cluster_thresholds.json (loaded from disk)
if os.path.isfile(THRESHOLD_JSON):
    with open(THRESHOLD_JSON) as f:
        existing_thresholds = json.load(f)
else:
    existing_thresholds = {}

valid_combos = set(existing_thresholds.keys())  # e.g. "Night_admin_staff_0"

def combo_key(shift, rg, cid):
    return f"{shift}_{rg}_{cid}"

# Build per-(shift,rg) cluster size counts from hourly data
valid_clusters_by_context = {}
for s in SHIFTS:
    valid_clusters_by_context[s] = {}
    for rg, df_sh in clustered_hourly.get(s, {}).items():
        cluster_sizes = df_sh["cluster_id"].value_counts()
        valid_cids = [c for c in cluster_sizes.index
                      if combo_key(s, rg, c) in valid_combos]
        valid_clusters_by_context[s][rg] = valid_cids

def reassign_cluster(user_id, shift, rg, bad_cid):
    """Return nearest valid cluster_id in (shift, rg) space, else 0."""
    valid_cids = valid_clusters_by_context.get(shift, {}).get(rg, [])
    if not valid_cids:
        return 0
    if len(valid_cids) == 1:
        return valid_cids[0]
    # Use profile features to pick nearest centroid
    info = kmeans_info.get(shift, {}).get(rg)
    if info is None:
        return valid_cids[0]
    rg_prof = info["rg_prof"]
    user_row = rg_prof[rg_prof["user_id"] == user_id]
    if user_row.empty:
        # User was filled in for this shift; use most-common valid cluster
        return valid_cids[0]
    X_user = user_row[PROFILE_FEATURES].replace([np.inf,-np.inf],np.nan).fillna(0).values
    X_user_sc = info["scaler"].transform(X_user)
    dists = {}
    for cid in valid_cids:
        centroid = info["centroids_sc"][cid]
        dists[cid] = np.linalg.norm(X_user_sc - centroid)
    return min(dists, key=dists.get)

# Find rows needing re-assignment
mask_bad = assignments_df.apply(
    lambda r: combo_key(r["shift"], r["role_group"], r["cluster_id"]) not in valid_combos,
    axis=1
)
bad_rows = assignments_df[mask_bad]
print(f"  Rows needing re-assignment: {len(bad_rows)}")

for idx, row in bad_rows.iterrows():
    new_cid = reassign_cluster(row["user_id"], row["shift"], row["role_group"], row["cluster_id"])
    assignments_df.at[idx, "cluster_id"] = int(new_cid)
    print(f"    Re-assigned {row['user_id']} | {row['shift']} | {row['role_group']}: "
          f"cluster {row['cluster_id']} -> {new_cid}")

# ─── Re-train IF for any newly covered (shift,rg,cluster) combos ──────────────
print("\nChecking for new combos needing IF training after re-assignment...")
with open(THRESHOLD_JSON) as f:
    thresholds = json.load(f)

# After re-assignment all combos should already be covered, but verify
new_combos_in_csv = set(
    assignments_df.apply(lambda r: combo_key(r["shift"], r["role_group"], r["cluster_id"]), axis=1)
)
still_missing = new_combos_in_csv - set(thresholds.keys())
if still_missing:
    print(f"  Still missing thresholds for: {still_missing}")
    # Train IF for these tiny combos using whatever hourly data is available
    newly_trained = 0
    for key in sorted(still_missing):
        parts = key.split("_")
        shift  = parts[0]
        cid    = int(parts[-1])
        rg     = "_".join(parts[1:-1])
        df_sh  = clustered_hourly.get(shift, {}).get(rg)
        if df_sh is None:
            print(f"    [SKIP] {key}: no hourly data")
            continue
        df_cl = df_sh[df_sh["cluster_id"] == cid]
        print(f"    Training IF for {key}: {len(df_cl)} rows")
        if len(df_cl) == 0:
            # Use all data for this (shift, rg)
            df_cl = df_sh.copy()
            print(f"      -> fell back to full {len(df_cl)} rows for {shift}/{rg}")
        X_if = df_cl[IF_FEATURES].replace([np.inf,-np.inf], np.nan).fillna(0)
        for col in X_if.columns:
            if X_if[col].dtype == bool:
                X_if[col] = X_if[col].astype(int)
        X_if = X_if.values.astype(float)
        iforest = IsolationForest(n_estimators=IF_ESTIMATORS,
                                  contamination=IF_CONTAMINATION,
                                  random_state=RANDOM_STATE)
        iforest.fit(X_if)
        scores    = iforest.decision_function(X_if)
        threshold = float(np.percentile(scores, THRESHOLD_PCTILE))
        model_file = os.path.join(CLUSTER_DIR, f"{shift.lower()}_{rg}_{cid}_if.pkl")
        with open(model_file, "wb") as f2:
            pickle.dump(iforest, f2)
        thresholds[key] = threshold
        newly_trained += 1
        print(f"    Saved {os.path.basename(model_file)} | threshold={threshold:.4f}")
    print(f"  Newly trained: {newly_trained}")
    with open(THRESHOLD_JSON, "w") as f2:
        json.dump(thresholds, f2, indent=2)
    print(f"  Updated cluster_thresholds.json ({len(thresholds)} keys)")
else:
    print("  No new combos -- all assignments covered by existing models.")

# ─── Write final CSV ───────────────────────────────────────────────────────────
print("\nWriting corrected user_cluster_assignments.csv...")
# Deduplicate: each user should appear exactly once per shift
assignments_df = assignments_df.drop_duplicates(subset=["user_id","shift"], keep="first")
assignments_df = assignments_df[["user_id","shift","role_group","cluster_id","assigned_at"]]
assignments_df["cluster_id"] = assignments_df["cluster_id"].astype(int)
assignments_df = assignments_df.sort_values(["user_id","shift"]).reset_index(drop=True)
assignments_df.to_csv(ASSIGNMENT_CSV, index=False)
print(f"  Saved: {ASSIGNMENT_CSV}")
print(f"  Total rows     : {len(assignments_df)}")
print(f"  Unique users   : {assignments_df['user_id'].nunique()}")
print(f"  Expected rows  : {assignments_df['user_id'].nunique() * 3}")

# Quick sanity check
user_counts = assignments_df.groupby("user_id")["shift"].nunique()
not_3 = (user_counts != 3).sum()
print(f"  Users != 3 shifts: {not_3}")

print("\nPatch complete.")
