"""
Centralized artifact loader for BehaviorGuard-AI production inference.

Loads the following artifacts ONCE (singleton pattern) and provides
thread-safe access methods:

  - notebooks/models/isolation_forest_model.pkl   (IsolationForest)
  - notebooks/models/feature_scaler.pkl           (RobustScaler)
  - notebooks/artifacts/feature_list.json          (ordered feature names)

Source: notebooks/V6.ipynb — execution_count 61 (serialisation cell).
"""

import json
import os
import threading

import joblib


_lock = threading.Lock()

_model = None
_scaler = None
_feature_list = None
_loaded = False


def _resolve(relative_path: str) -> str:
    """Return an absolute path relative to the project root."""
    # model_loader.py lives at  app/core/model_loader.py
    # project root is two directories up.
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(project_root, relative_path)


def _load_artifacts() -> None:
    """Load model, scaler, and feature list from disk exactly once."""
    global _model, _scaler, _feature_list, _loaded

    if _loaded:
        return

    with _lock:
        # Double-checked locking
        if _loaded:
            return

        model_path = _resolve(os.path.join("notebooks", "models", "isolation_forest_model.pkl"))
        scaler_path = _resolve(os.path.join("notebooks", "models", "feature_scaler.pkl"))
        features_path = _resolve(os.path.join("notebooks", "artifacts", "feature_list.json"))

        _model = joblib.load(model_path)
        _scaler = joblib.load(scaler_path)

        with open(features_path, "r") as fh:
            _feature_list = json.load(fh)

        _loaded = True


def get_model():
    """Return the pre-trained IsolationForest model."""
    _load_artifacts()
    return _model


def get_scaler():
    """Return the fitted RobustScaler."""
    _load_artifacts()
    return _scaler


def get_feature_list() -> list:
    """Return the ordered feature name list (length 10)."""
    _load_artifacts()
    return list(_feature_list)
