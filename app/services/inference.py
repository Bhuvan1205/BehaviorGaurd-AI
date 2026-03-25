"""
Production inference module for BehaviorGuard-AI.

Runs single-event anomaly prediction using the pre-trained artifacts
from notebooks/V6.ipynb:

  1. Load artifacts once via model_loader (singleton).
  2. Scale the 10-element feature vector with the saved RobustScaler.
  3. Score with the saved IsolationForest.

Inference pipeline extracted from V6.ipynb:
  • execution_count 30  — iso = IsolationForest(n_estimators=200,
                                                contamination=0.06,
                                                random_state=42, n_jobs=-1)
  • execution_count 31  — iso.decision_function(X) / iso.predict(X)
  • execution_count 32  — anomaly flag: predict == -1  →  True (anomaly)
  • execution_count 62  — sanity check: scaler_loaded.transform → iso_loaded.predict
"""

import numpy as np
import pandas as pd

from app.core.model_loader import get_model, get_scaler, get_feature_list


_artifacts_ready = False


def load_model() -> None:
    """
    Eagerly load all inference artifacts into memory.

    Calls the singleton loader so that subsequent predict() calls
    never hit disk.  Safe to call multiple times.
    """
    global _artifacts_ready
    # These calls trigger _load_artifacts() at most once (singleton).
    get_model()
    get_scaler()
    get_feature_list()
    _artifacts_ready = True


def predict(features: list) -> dict:
    """
    Run anomaly inference on a single feature vector.

    Parameters
    ----------
    features : list[float]
        Ordered 10-element feature list produced by
        ``app.services.feature_engine.compute_features``.
        Order MUST match notebooks/artifacts/feature_list.json.

    Returns
    -------
    dict
        {
            "anomaly_flag": int,      # 1 = anomaly, 0 = normal
            "anomaly_score": float    # continuous decision_function score
        }

    Raises
    ------
    ValueError
        If ``features`` length does not equal the expected feature count.
    """
    model = get_model()
    scaler = get_scaler()
    feature_list = get_feature_list()

    expected_len = len(feature_list)
    if len(features) != expected_len:
        raise ValueError(
            f"Feature vector length mismatch: "
            f"expected {expected_len}, got {len(features)}"
        )

    # Build a named DataFrame so sklearn receives the feature names
    # the model was fitted with (eliminates the UserWarning).
    X = pd.DataFrame([features], columns=feature_list)

    # Replace inf / NaN with 0  (mirrors notebook cleanup logic)
    X = X.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    # Scale features using the saved RobustScaler
    # The scaler was fitted on numpy arrays (group[features].values in V6),
    # so pass .values to avoid a "fitted without feature names" warning.
    # The IsolationForest was fitted on a named DataFrame (df_v6[features]),
    # so wrap the scaled output back into a DataFrame for the model.
    X_scaled = pd.DataFrame(
        scaler.transform(X.values), columns=feature_list
    )
    print("SCALED:", X_scaled.values.tolist()[0])

    # IsolationForest prediction
    # V6 cell 31:  iso.predict(X)   →  -1 = anomaly, 1 = normal
    raw_pred = model.predict(X_scaled)[0]

    # V6 cell 31:  iso.decision_function(X)  →  continuous anomaly score
    anomaly_score = float(model.decision_function(X_scaled)[0])

    # V6 cell 32:  df_v6["if_anomaly"] = df_v6["if_anomaly"] == -1
    anomaly_flag = 1 if raw_pred == -1 else 0

    return {
        "anomaly_flag": anomaly_flag,
        "anomaly_score": anomaly_score,
    }
