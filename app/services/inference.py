import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

# Use sklearn's HDBSCAN (available in scikit-learn >= 1.3)
from sklearn.cluster import HDBSCAN as _HDBSCAN

from app.core.model_loader import get_model, get_scaler

logger = logging.getLogger(__name__)

IF_FEATURES = [
    "z_logon", "z_pcs", "logon_deviation", "device_deviation",
    "device_ratio", "burst_score", "hour_deviation", "session_gap",
    "logon_logoff_ratio", "night_activity_flag",
]

def _determine_shift(hour: int) -> str:
    if 9 <= hour <= 16:
        return "Day"
    if 17 <= hour <= 21:
        return "Evening"
    return "Night"


def _resolve_risk_level(risk_score: float) -> str:
    if risk_score >= 0.80:
        return "HIGH"
    if risk_score >= 0.68:
        return "ELEVATED"
    if risk_score >= 0.50:
        return "GUARDED"
    return "LOW"


def run_inference(df: pd.DataFrame, cur) -> pd.DataFrame:
    """
    Executes V6 clustering and anomaly scoring:
      1. Contextual Segmentation (Shift × Role Group).
      2. HDBSCAN fit-predict per context to compute labels and probabilities.
      3. Risk scoring & anomaly flags based on HDBSCAN output.
      4. Global Isolation Forest continuous scoring & anomaly check.
    """
    logger.info("Starting ML Inference (V6 Pipeline)...")
    df = df.copy()

    # ── 1. Shift & Role Group Segmentation ────────────────────────────────────
    df["shift"] = df["hour"].apply(_determine_shift)

    # Fetch role groups from the database for the batch users
    user_ids = df["user_id"].unique().tolist()
    role_map = {}
    if user_ids:
        placeholders = ",".join(["%s"] * len(user_ids))
        cur.execute(
            f"""
            SELECT u.user_id::text, r.role_name
            FROM core.users u
            LEFT JOIN core.roles r ON r.role_id = u.role_id
            WHERE u.user_id = ANY(ARRAY[{placeholders}]::uuid[])
            """,
            user_ids,
        )
        for row in cur.fetchall():
            # Map role names to lowercase clean role groups
            role_name = (row["role_name"] or "general").lower().strip()
            role_map[str(row["user_id"])] = role_name

    df["role_group"] = df["user_id"].apply(lambda uid: role_map.get(str(uid), "general"))

    # ── 2. HDBSCAN Clustering ─────────────────────────────────────────────────
    df["hdbscan_label"] = 0
    df["cluster_probability"] = 1.0
    df["is_noise"] = False

    groups = df.groupby(["shift", "role_group"])
    for (shift, rg), subset in groups:
        idx = subset.index

        # V6 Notebook requires group size >= 100 for clustering
        if len(subset) < 100:
            df.loc[idx, "hdbscan_label"] = 0
            df.loc[idx, "cluster_probability"] = 1.0
            df.loc[idx, "is_noise"] = False
            continue

        # Extract features and handle inf/nan values
        X = (
            subset[IF_FEATURES]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )
        # Convert bool to int/float for scikit-learn compatibility
        if "night_activity_flag" in X.columns:
            X = X.copy()
            X["night_activity_flag"] = X["night_activity_flag"].astype(int)

        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(X.values)

        # Compute dynamic parameters for small weekly batches (V6 notebook parameters for large groups)
        min_cluster_size = min(50, max(5, int(len(subset) * 0.05)))
        min_samples = max(2, int(min_cluster_size * 0.2))

        # Fit HDBSCAN (V6 notebook exact parameters)
        clusterer = _HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric="euclidean",
            cluster_selection_method="eom"
        )
        labels = clusterer.fit_predict(X_scaled)
        probabilities = clusterer.probabilities_

        df.loc[idx, "hdbscan_label"] = labels
        df.loc[idx, "cluster_probability"] = probabilities
        df.loc[idx, "is_noise"] = (labels == -1)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise    = (labels == -1).sum()
        logger.info(
            "  HDBSCAN  %s | %-25s  %d records  →  %d clusters  %d noise (min_sz=%d, min_samp=%d)",
            shift, rg, len(subset), n_clusters, n_noise, min_cluster_size, min_samples
        )

    # ── 3. V6 Risk Score Calculation ──────────────────────────────────────────
    # Formula: risk_score = (is_noise)*0.6 + (1 - prob)*0.4
    df["risk_score"] = (
        (df["hdbscan_label"] == -1).astype(int) * 0.6
        +
        (1.0 - df["cluster_probability"]) * 0.4
    )
    df["risk_score"] = df["risk_score"].clip(0.0, 1.0)
    df["anomaly_flag"] = df["risk_score"] > 0.6
    df["risk_level"] = df["risk_score"].apply(_resolve_risk_level)

    # ── 4. Global Isolation Forest Scoring ────────────────────────────────────
    logger.info("Executing Global Isolation Forest Scoring...")
    iso = get_model()
    global_scaler = get_scaler()

    # Extract all features for the entire batch
    X_global = (
        df[IF_FEATURES]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )
    if "night_activity_flag" in X_global.columns:
        X_global = X_global.copy()
        X_global["night_activity_flag"] = X_global["night_activity_flag"].astype(int)

    X_global_scaled = global_scaler.transform(X_global.values)
    X_global_scaled_df = pd.DataFrame(X_global_scaled, columns=IF_FEATURES)
    df["if_score"] = iso.decision_function(X_global_scaled_df)
    df["if_anomaly"] = iso.predict(X_global_scaled_df) == -1

    anomaly_count = df["anomaly_flag"].sum()
    logger.info(
        "Scoring complete | %d anomalies detected by HDBSCAN | %d by Isolation Forest",
        anomaly_count, df["if_anomaly"].sum(),
    )
    return df
