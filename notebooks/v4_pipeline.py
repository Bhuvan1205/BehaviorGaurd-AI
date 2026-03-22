import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings("ignore")

IF_FEATURES = [
    "logon_count",
    "logoff_count",
    "unique_pcs",
    "z_logon",
    "z_pcs",
]

N_CLUSTERS = 4
IF_N_ESTIMATORS = 100
IF_CONTAMINATION = "auto"
IF_RANDOM_STATE = 42
KMEANS_RANDOM_STATE = 42
PERCENTILE_THRESHOLD = 0.01
_SYNTHETIC_COLS = ["is_injected", "anomaly_type"]


def segment_shifts(df):
    day_mask = (df["hour"] >= 9) & (df["hour"] <= 16)
    evening_mask = (df["hour"] >= 17) & (df["hour"] <= 21)
    night_mask = (df["hour"] >= 22) | (df["hour"] <= 8)

    shifts = {
        "day": df[day_mask].copy(),
        "evening": df[evening_mask].copy(),
        "night": df[night_mask].copy(),
    }
    return shifts


def build_user_profiles(df_shift):
    aggregations = {
        "logon_count": ["mean", "std", "sum"],
        "unique_pcs": ["mean", "std"],
        "hour": ["mean", "std"],
    }

    user_profile = df_shift.groupby("user").agg(aggregations)

    user_profile.columns = [
        "mean_logon_count",
        "std_logon_count",
        "total_logon_volume",
        "mean_unique_pcs",
        "std_unique_pcs",
        "mean_activity_hour",
        "activity_hour_std",
    ]

    user_profile = user_profile.reset_index()
    user_profile = user_profile.fillna(0)

    user_profile["total_logon_volume"] = np.log1p(
        user_profile["total_logon_volume"]
    )

    return user_profile


def cluster_users(user_profile, n_clusters=N_CLUSTERS):
    features = user_profile.drop("user", axis=1)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=KMEANS_RANDOM_STATE,
        n_init=10,
    )
    cluster_labels = kmeans.fit_predict(X_scaled)

    user_profile = user_profile.copy()
    user_profile["cluster_id"] = cluster_labels

    return user_profile, kmeans, scaler


def merge_user_cluster_back(df_shift, user_profile):
    df_shift = df_shift.merge(
        user_profile[["user", "cluster_id"]],
        on="user",
        how="left",
    )
    df_shift["cluster_id"] = df_shift["cluster_id"].fillna(-1).astype(int)
    return df_shift


def train_cluster_specific_iforest(df, features, contamination=IF_CONTAMINATION):
    df = df.copy()
    df["cluster_if_score"] = 0.0
    df["cluster_if_pred"] = 0

    clusters = [c for c in df["cluster_id"].unique() if c != -1]

    for cluster_id in clusters:
        cluster_data = df[df["cluster_id"] == cluster_id]

        if len(cluster_data) < 10:
            continue

        X = cluster_data[features].copy()
        X.replace([np.inf, -np.inf], np.nan, inplace=True)
        X.fillna(0, inplace=True)

        model = IsolationForest(
            n_estimators=IF_N_ESTIMATORS,
            contamination=contamination,
            random_state=IF_RANDOM_STATE,
        )
        model.fit(X)

        scores = model.decision_function(X)
        preds = model.predict(X)

        df.loc[cluster_data.index, "cluster_if_score"] = scores
        df.loc[cluster_data.index, "cluster_if_pred"] = preds

    df["is_cluster_anomaly"] = (
        df["cluster_if_pred"].apply(lambda x: 1 if x == -1 else 0)
    )

    return df


def apply_percentile_threshold(df, percentile=PERCENTILE_THRESHOLD):
    df = df.copy()
    df["is_anomaly_final"] = 0

    for cid in df["cluster_id"].unique():
        mask = df["cluster_id"] == cid
        cluster_scores = df.loc[mask, "cluster_if_score"]

        if len(cluster_scores) < 10:
            continue

        thresh = cluster_scores.quantile(percentile)
        df.loc[mask & (df["cluster_if_score"] < thresh), "is_anomaly_final"] = 1

    return df


def _process_shift(df_shift, shift_name):
    df_shift = df_shift.copy()
    df_shift["Shift"] = shift_name.capitalize()

    user_profile = build_user_profiles(df_shift)
    user_profile, _kmeans, _scaler = cluster_users(user_profile)
    df_shift = merge_user_cluster_back(df_shift, user_profile)
    df_shift = train_cluster_specific_iforest(df_shift, IF_FEATURES)
    df_shift = apply_percentile_threshold(df_shift)

    return df_shift


def run_v3_pipeline(df):
    required = set(IF_FEATURES)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    present_syn_cols = [c for c in _SYNTHETIC_COLS if c in df.columns]

    if present_syn_cols:
        syn_backup = df[present_syn_cols].copy()
        syn_backup.index = df.index

    shifts = segment_shifts(df)

    processed = []
    for shift_name, df_shift in shifts.items():
        result = _process_shift(df_shift, shift_name)
        processed.append(result)

    df_result = pd.concat(processed, ignore_index=False)
    df_result = df_result.sort_index()

    if present_syn_cols:
        for col in present_syn_cols:
            df_result[col] = syn_backup.loc[df_result.index, col]

    df_result = df_result.reset_index(drop=True)
    return df_result

#new anamolies are being added to the dataset
def inject_synthetic_anomalies(df):
    df_test = df.copy()
    size_of_df = df_test.shape[0]
    no_of_ingested = int(size_of_df * 0.005)

    df_test['is_ingested'] = 0

    ingestion_indices = df_test.sample(no_of_ingested, random_state=42).index

    split_size = no_of_ingested // 4

    indices = np.array(ingestion_indices)
    login_burst_idx = indices[:split_size]
    device_explosion_idx = indices[split_size:2*split_size]
    cross_shift_idx = indices[2*split_size:3*split_size]
    combined_idx = indices[3*split_size:]

    df_test.loc[login_burst_idx, "logon_count"] = np.random.randint(8, 15, size=len(login_burst_idx))
    df_test.loc[login_burst_idx, "logoff_count"] = np.random.randint(0, 3, size=len(login_burst_idx))

    df_test.loc[device_explosion_idx, "unique_pcs"] = np.random.randint(4, 7, size=len(device_explosion_idx))

    df_test.loc[cross_shift_idx, "hour"] = np.random.randint(0, 6, size=len(cross_shift_idx))

    df_test.loc[combined_idx, "logon_count"] = np.random.randint(10, 16, size=len(combined_idx))
    df_test.loc[combined_idx, "unique_pcs"] = np.random.randint(4, 7, size=len(combined_idx))
    df_test.loc[combined_idx, "hour"] = np.random.randint(22, 24, size=len(combined_idx))
    df_test.loc[ingestion_indices, "is_injected"] = 1

    df_test["anomaly_type"] = "normal"
    df_test.loc[login_burst_idx, "anomaly_type"] = "login_burst"
    df_test.loc[device_explosion_idx, "anomaly_type"] = "device_explosion"
    df_test.loc[cross_shift_idx, "anomaly_type"] = "cross_shift"
    df_test.loc[combined_idx, "anomaly_type"] = "combined"

    user_stats = df_test.groupby("user").agg(
        avg_logon=("logon_count", "mean"),
        std_logon=("logon_count", "std"),
        avg_pcs=("unique_pcs", "mean"),
        std_pcs=("unique_pcs", "std")
    ).reset_index()

    df_test = df_test.drop(columns=["avg_logon", "std_logon", "avg_pcs", "std_pcs"], errors="ignore")
    df_test = df_test.merge(user_stats, on="user", how="left")

    df_test["z_logon"] = (df_test["logon_count"] - df_test["avg_logon"]) / df_test["std_logon"]
    df_test["z_pcs"] = (df_test["unique_pcs"] - df_test["avg_pcs"]) / df_test["std_pcs"]

    df_test = df_test.replace([np.inf, -np.inf], 0).fillna(0)

    return df_test


def evaluate_synthetic_detection(df):
    if "is_injected" not in df.columns:
        raise ValueError(
            "Column 'is_injected' not found. "
            "Make sure the input dataframe comes from a V4 synthetic experiment."
        )

    injected = df[df["is_injected"] == 1]
    normal = df[df["is_injected"] == 0]

    n_injected = len(injected)
    n_detected = int((injected["is_anomaly_final"] == 1).sum()) if n_injected else 0
    detection_rate = n_detected / n_injected if n_injected else 0.0

    n_normal = len(normal)
    n_fp = int((normal["is_anomaly_final"] == 1).sum()) if n_normal else 0
    fp_rate = n_fp / n_normal if n_normal else 0.0

    metrics = {
        "detection_rate": detection_rate,
        "false_positive_rate": fp_rate,
        "n_injected": n_injected,
        "n_detected": n_detected,
        "n_normal": n_normal,
        "n_false_positives": n_fp,
    }

    if "anomaly_type" in df.columns and n_injected > 0:
        by_type = {}
        for atype, grp in injected.groupby("anomaly_type"):
            cnt = len(grp)
            det = int((grp["is_anomaly_final"] == 1).sum())
            by_type[atype] = det / cnt if cnt else 0.0
        metrics["detection_by_type"] = by_type

    if "Shift" in df.columns and n_injected > 0:
        metrics["detection_by_shift"] = (
            df[df["is_injected"] == 1]
            .groupby("Shift")["is_anomaly_final"]
            .mean()
            .to_dict()
        )

    return metrics


def evaluate_raw_if_detection(df):
    if "is_injected" not in df.columns:
        raise ValueError(
            "Column 'is_injected' not found. "
            "Make sure the input dataframe comes from a V4 synthetic experiment."
        )

    raw_flag = (df["cluster_if_pred"] == -1).astype(int)

    injected = df[df["is_injected"] == 1]
    normal = df[df["is_injected"] == 0]

    n_injected = len(injected)
    n_detected = int(raw_flag.loc[injected.index].sum()) if n_injected else 0
    detection_rate = n_detected / n_injected if n_injected else 0.0

    n_normal = len(normal)
    n_fp = int(raw_flag.loc[normal.index].sum()) if n_normal else 0
    fp_rate = n_fp / n_normal if n_normal else 0.0

    metrics = {
        "detection_rate": detection_rate,
        "false_positive_rate": fp_rate,
        "n_injected": n_injected,
        "n_detected": n_detected,
        "n_normal": n_normal,
        "n_false_positives": n_fp,
    }

    if "anomaly_type" in df.columns and n_injected > 0:
        by_type = {}
        for atype, grp in injected.groupby("anomaly_type"):
            cnt = len(grp)
            det = int(raw_flag.loc[grp.index].sum())
            by_type[atype] = det / cnt if cnt else 0.0
        metrics["detection_by_type"] = by_type

    if "Shift" in df.columns and n_injected > 0:
        by_shift = {}
        for shift, grp in injected.groupby("Shift"):
            cnt = len(grp)
            det = int(raw_flag.loc[grp.index].sum())
            by_shift[shift] = det / cnt if cnt else 0.0
        metrics["detection_by_shift"] = by_shift

    return metrics


def display_metrics(metrics, title="Evaluation Metrics"):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(f"  {'Detection Rate':<25} {metrics['detection_rate']:.4f}  ({metrics['n_detected']}/{metrics['n_injected']})")
    print(f"  {'False Positive Rate':<25} {metrics['false_positive_rate']:.6f}  ({metrics['n_false_positives']}/{metrics['n_normal']})")

    if "detection_by_type" in metrics:
        print(f"\n  Detection by Anomaly Type:")
        for atype, rate in metrics["detection_by_type"].items():
            print(f"    {atype:<30} {rate:.4f}")

    if "detection_by_shift" in metrics:
        print(f"\n  Detection by Shift:")
        for shift, rate in metrics["detection_by_shift"].items():
            print(f"    {shift:<15} {rate:.4f}")

    print(f"{'='*60}\n")


def run_full_v4_pipeline(df_input):
    df = df_input.copy()
    df_test = inject_synthetic_anomalies(df)
    df_result = run_v3_pipeline(df_test)

    metrics_percentile = evaluate_synthetic_detection(df_result)
    metrics_raw_if = evaluate_raw_if_detection(df_result)

    metrics = {
        "percentile_calibrated": metrics_percentile,
        "raw_if": metrics_raw_if,
    }

    return df_result, metrics
