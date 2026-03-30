import os
from math import exp

import joblib
import numpy as np
import pandas as pd

from app.core.model_loader import get_feature_list


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
model = joblib.load(os.path.join(BASE_DIR, "notebooks", "models", "isolation_forest_model.pkl"))
scaler = joblib.load(os.path.join(BASE_DIR, "notebooks", "models", "feature_scaler.pkl"))


def predict(features: dict):
    feature_names = get_feature_list()
    raw_vector = np.array(
        [[float(features.get(name, 0)) for name in feature_names]],
        dtype=float,
    )
    feature_vector = pd.DataFrame(raw_vector, columns=feature_names)

    scaled = scaler.transform(raw_vector)
    scaled_frame = pd.DataFrame(scaled, columns=feature_names)

    score = model.decision_function(scaled_frame)[0]
    flag = int(model.predict(scaled_frame)[0] == -1)

    return flag, float(score)


def anomaly_score_to_risk(score: float) -> float:
    """
    Convert the Isolation Forest decision score into a smooth 0..1 risk value.

    IsolationForest does not expose a calibrated probability by default, so we
    derive a monotonic risk percentage from the decision score itself:
    lower scores => higher risk, higher scores => lower risk.
    """
    bounded = 1.0 / (1.0 + exp(float(score) * 6.0))
    return max(0.0, min(float(bounded), 1.0))
