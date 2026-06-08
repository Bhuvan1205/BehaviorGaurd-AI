"""
BehaviorGuard-AI -- Cluster Pipeline Output Validation
=======================================================
Runs 4 structured checks on the outputs of run_cluster_pipeline_v5.py:
  CHECK 1 -- CSV integrity
  CHECK 2 -- Model file integrity
  CHECK 3 -- Threshold JSON integrity
  CHECK 4 -- Coverage cross-reference
Prints PASS / FAIL with per-check details.
"""

import os, re, sys, json, pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR   = os.path.dirname(BASE_DIR)
CLUSTER_DIR   = os.path.join(BASE_DIR, "models", "cluster_models")
ASSIGNMENT_CSV = os.path.join(CLUSTER_DIR, "user_cluster_assignments.csv")
THRESHOLD_JSON = os.path.join(CLUSTER_DIR, "cluster_thresholds.json")

VALID_SHIFTS   = {"Day", "Evening", "Night"}
VALID_CLUSTERS = {0, 1, 2, 3}
IF_N_FEATURES  = 10          # must match feature_list.json

PASS_MARK = "[PASS]"
FAIL_MARK = "[FAIL]"

failures = []   # accumulates failure messages

# ─────────────────────────────────────────────────────────────────────────────
def banner(title):
    print("\n" + "=" * 72)
    print(f"  {title}")
    print("=" * 72)

def ok(msg):
    print(f"  {PASS_MARK} {msg}")

def fail(msg):
    print(f"  {FAIL_MARK} {msg}")
    failures.append(msg)

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 1 -- CSV integrity
# ─────────────────────────────────────────────────────────────────────────────
banner("CHECK 1 -- CSV Integrity: user_cluster_assignments.csv")

if not os.path.isfile(ASSIGNMENT_CSV):
    fail(f"File not found: {ASSIGNMENT_CSV}")
    print("\n  Cannot continue without assignment CSV -- aborting.")
    sys.exit(1)

df = pd.read_csv(ASSIGNMENT_CSV)

# 1a: Required columns
REQUIRED_COLS = ["user_id", "shift", "role_group", "cluster_id", "assigned_at"]
missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
if missing_cols:
    fail(f"Missing columns: {missing_cols}")
else:
    ok(f"All required columns present: {REQUIRED_COLS}")

# 1b: Shift values
bad_shifts = set(df["shift"].unique()) - VALID_SHIFTS
if bad_shifts:
    fail(f"Invalid shift values found: {bad_shifts}")
else:
    ok(f"Shift values are valid: {sorted(df['shift'].unique())}")

# 1c: Cluster ID values
bad_clusters = set(df["cluster_id"].unique()) - VALID_CLUSTERS
if bad_clusters:
    fail(f"Invalid cluster_id values found: {bad_clusters}")
else:
    ok(f"cluster_id values are valid: {sorted(df['cluster_id'].unique())}")

# 1d: No null values
null_counts = df[REQUIRED_COLS].isnull().sum()
if null_counts.any():
    fail(f"Null values detected:\n{null_counts[null_counts > 0].to_string()}")
else:
    ok("No null values in any required column")

# 1e: Each user appears exactly 3 times (one per shift)
user_counts = df.groupby("user_id")["shift"].nunique()
users_not_3 = user_counts[user_counts != 3]
if len(users_not_3) > 0:
    fail(f"{len(users_not_3)} users do NOT appear in all 3 shifts. Examples:\n"
         f"{users_not_3.head(10).to_string()}")
else:
    ok("Every user appears in exactly 3 shifts")

# 1f: row count per shift sanity
shift_counts = df["shift"].value_counts()
print(f"\n  Shift distribution:\n{shift_counts.to_string()}")

total_users = df["user_id"].nunique()
print(f"\n  Total unique users : {total_users}")
print(f"  Total CSV rows     : {len(df)}")
print(f"  Expected rows      : {total_users * 3}")
if len(df) == total_users * 3:
    ok(f"Row count ({len(df)}) == users ({total_users}) x 3 shifts")
else:
    fail(f"Row count mismatch: {len(df)} rows vs {total_users * 3} expected")

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 2 -- Model file integrity
# ─────────────────────────────────────────────────────────────────────────────
banner("CHECK 2 -- Model File Integrity (.pkl files)")

if not os.path.isdir(CLUSTER_DIR):
    fail(f"cluster_models directory not found: {CLUSTER_DIR}")
    model_files = []
else:
    model_files = sorted([
        f for f in os.listdir(CLUSTER_DIR)
        if f.endswith("_if.pkl")
    ])

print(f"  Found {len(model_files)} model files ending in '_if.pkl'")

valid_model_count = 0
zero_vec = np.zeros((1, IF_N_FEATURES))

for fname in model_files:
    fpath = os.path.join(CLUSTER_DIR, fname)
    try:
        with open(fpath, "rb") as f:
            model = pickle.load(f)

        # Check type
        if not isinstance(model, IsolationForest):
            fail(f"{fname}: not an IsolationForest (got {type(model).__name__})")
            continue

        # Check fitted
        if not hasattr(model, "estimators_"):
            fail(f"{fname}: model not fitted (estimators_ missing)")
            continue

        # Check inference
        score = model.decision_function(zero_vec)
        if not (isinstance(score, np.ndarray) and len(score) == 1):
            fail(f"{fname}: decision_function returned unexpected shape {score.shape}")
            continue

        valid_model_count += 1
        print(f"  {PASS_MARK} {fname}  ->  zero-vec score = {score[0]:.4f}")

    except Exception as e:
        fail(f"{fname}: exception during validation -- {e}")

print(f"\n  Valid models : {valid_model_count} / {len(model_files)}")
if valid_model_count == len(model_files) and len(model_files) > 0:
    ok(f"All {valid_model_count} model files passed integrity check")
elif len(model_files) == 0:
    fail("No model files found in cluster_models directory")
else:
    fail(f"{len(model_files) - valid_model_count} model files FAILED integrity check")

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3 -- Threshold JSON integrity
# ─────────────────────────────────────────────────────────────────────────────
banner("CHECK 3 -- Threshold JSON Integrity: cluster_thresholds.json")

if not os.path.isfile(THRESHOLD_JSON):
    fail(f"File not found: {THRESHOLD_JSON}")
    thresholds = {}
else:
    with open(THRESHOLD_JSON) as f:
        thresholds = json.load(f)

print(f"  Total threshold keys : {len(thresholds)}")

# 3a: Key pattern {shift}_{role_group}_{cluster_id}
KEY_PATTERN = re.compile(
    r"^(Day|Evening|Night)_[a-z_]+_[0-3]$"
)
bad_keys = [k for k in thresholds if not KEY_PATTERN.match(k)]
if bad_keys:
    fail(f"Keys with invalid pattern: {bad_keys}")
else:
    ok("All keys match pattern {shift}_{role_group}_{cluster_id}")

# 3b: All values are negative floats
non_negative = {k: v for k, v in thresholds.items() if not isinstance(v, (int, float)) or v >= 0}
if non_negative:
    fail(f"Non-negative or non-float threshold values found: {non_negative}")
else:
    ok("All threshold values are negative floats (correct for IsolationForest)")

# 3c: Key count matches model file count
if len(thresholds) == valid_model_count:
    ok(f"Threshold count ({len(thresholds)}) matches valid model count ({valid_model_count})")
else:
    fail(f"Threshold count ({len(thresholds)}) != valid model count ({valid_model_count})")

# 3d: Print all keys and values
print("\n  Threshold key-value listing:")
print(f"  {'Key':<45}  {'Threshold':>12}")
print(f"  {'-'*45}  {'-'*12}")
for k in sorted(thresholds.keys()):
    print(f"  {k:<45}  {thresholds[k]:>12.6f}")

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 4 -- Coverage cross-reference
# ─────────────────────────────────────────────────────────────────────────────
banner("CHECK 4 -- Coverage Cross-Reference (CSV <-> Thresholds/Models)")

# Build set of (shift, role_group, cluster_id) from CSV
csv_combos = set(
    df[["shift", "role_group", "cluster_id"]]
    .drop_duplicates()
    .apply(lambda r: f"{r['shift']}_{r['role_group']}_{r['cluster_id']}", axis=1)
)

# Build set of keys from threshold JSON
threshold_keys = set(thresholds.keys())

# Build set of keys inferred from model file names
# File pattern: {shift}_{role_group}_{cluster_id}_if.pkl
model_keys = set()
for fname in model_files:
    # strip _if.pkl suffix
    stem = fname[:-len("_if.pkl")]
    # Capitalise shift prefix to match key format
    for s in ["day", "evening", "night"]:
        if stem.startswith(s + "_"):
            cap_stem = s.capitalize() + stem[len(s):]
            model_keys.add(cap_stem)
            break

# Missing thresholds for CSV combos
missing_thresholds = csv_combos - threshold_keys
# Missing model files for CSV combos
missing_models = csv_combos - model_keys

print(f"\n  Unique (shift, role_group, cluster_id) combos in CSV : {len(csv_combos)}")
print(f"  Keys in cluster_thresholds.json                      : {len(threshold_keys)}")
print(f"  Model files (inferred keys)                          : {len(model_keys)}")

if missing_thresholds:
    fail(f"{len(missing_thresholds)} CSV combos MISSING from threshold JSON:")
    for m in sorted(missing_thresholds):
        print(f"    - {m}")
else:
    ok("All CSV (shift, role_group, cluster_id) combos have a threshold entry")

if missing_models:
    fail(f"{len(missing_models)} CSV combos MISSING a model file:")
    for m in sorted(missing_models):
        print(f"    - {m}")
else:
    ok("All CSV (shift, role_group, cluster_id) combos have a model file")

# Extra thresholds not in CSV (informational)
extra_in_json = threshold_keys - csv_combos
if extra_in_json:
    print(f"\n  [INFO] Keys in JSON but not in CSV (may be skipped groups): {len(extra_in_json)}")
    for e in sorted(extra_in_json):
        print(f"    ~ {e}")

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
banner("FINAL VALIDATION SUMMARY")

if failures:
    print(f"  STATUS : FAIL")
    print(f"  Total failure points : {len(failures)}")
    print()
    for i, f_msg in enumerate(failures, 1):
        print(f"  [{i}] {f_msg}")
    sys.exit(1)
else:
    print(f"  STATUS : PASS")
    print(f"  All 4 checks passed with zero failures.")
    print()
    print(f"  Summary:")
    print(f"    - Unique users in CSV        : {total_users}")
    print(f"    - Valid model files          : {valid_model_count}")
    print(f"    - Threshold keys in JSON     : {len(thresholds)}")
    print(f"    - Coverage gaps (CSV vs JSON): {len(missing_thresholds)}")
    print(f"    - Coverage gaps (CSV vs PKL) : {len(missing_models)}")
