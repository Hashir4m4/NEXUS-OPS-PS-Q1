"""
Unit Tests for Quantum Feature Scaling and Leakage Prevention
=============================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 3)

Validates:
1. Strict training-only parameter fitting.
2. Safe transformation to [0, pi] domain.
3. Handling of constant (zero-variance) features.
4. Safe clipping of out-of-distribution points.
5. Integrity of data/processed/features_train.csv and features_test.csv.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_scaling import QuantumFeatureScaler
from src.feature_extraction import FEATURE_NAMES


def test_quantum_feature_scaler_basic():
    """Tests standard fitting on training matrix and scaling to [0, pi]."""
    X_train = np.array([
        [10.0, 100.0],
        [20.0, 200.0],
        [30.0, 300.0]
    ])
    scaler = QuantumFeatureScaler()
    scaler.fit(X_train)

    X_train_scaled = scaler.transform(X_train)

    # Minimums must map to 0.0, maximums must map to pi
    np.testing.assert_allclose(X_train_scaled[0], [0.0, 0.0], atol=1e-6)
    np.testing.assert_allclose(X_train_scaled[2], [np.pi, np.pi], atol=1e-6)
    np.testing.assert_allclose(X_train_scaled[1], [np.pi / 2.0, np.pi / 2.0], atol=1e-6)


def test_quantum_feature_scaler_constant_feature():
    """Tests that constant features (range = 0) do not cause division by zero."""
    X_constant = np.array([
        [5.0, 1.0],
        [5.0, 2.0],
        [5.0, 3.0]
    ])
    scaler = QuantumFeatureScaler()
    scaler.fit(X_constant)

    scaled = scaler.transform(X_constant)
    # Column 0 is constant -> should produce finite numbers (0.0), no NaNs
    assert not np.isnan(scaled).any()
    assert not np.isinf(scaled).any()
    np.testing.assert_allclose(scaled[:, 0], 0.0)


def test_quantum_feature_scaler_clipping():
    """Tests clipping behavior when test points fall outside training range."""
    X_train = np.array([[0.0], [10.0]])
    X_test = np.array([[-5.0], [15.0]])  # Below min and above max

    scaler = QuantumFeatureScaler(clip=True)
    scaler.fit(X_train)
    scaled_test = scaler.transform(X_test)

    # Must be clipped to [0, pi]
    assert pytest.approx(scaled_test[0, 0]) == 0.0
    assert pytest.approx(scaled_test[1, 0]) == np.pi


def test_unfitted_scaler_raises():
    """Tests that transforming before fitting raises RuntimeError."""
    scaler = QuantumFeatureScaler()
    with pytest.raises(RuntimeError):
        scaler.transform(np.array([[1.0, 2.0]]))


def test_processed_feature_files():
    """Validates the actual exported feature CSV files on disk."""
    data_dir = PROJECT_ROOT / "data" / "processed"
    train_path = data_dir / "features_train.csv"
    test_path = data_dir / "features_test.csv"

    assert train_path.exists(), f"Missing {train_path}"
    assert test_path.exists(), f"Missing {test_path}"

    df_train = pd.read_csv(train_path)
    df_test = pd.read_csv(test_path)

    # 1. Row counts
    assert len(df_train) == 200
    assert len(df_test) == 100

    # 2. Patient / record isolation
    assert set(df_train["record_id"].astype(str)) == {"106", "119"}
    assert set(df_test["record_id"].astype(str)) == {"200", "208"}

    # 3. Exactly 6 unscaled features and 6 scaled features
    scaled_feature_cols = [f"{fn}_scaled" for fn in FEATURE_NAMES]
    for col in FEATURE_NAMES + scaled_feature_cols:
        assert col in df_train.columns
        assert col in df_test.columns

    # 4. No NaNs or Infs
    assert not df_train[FEATURE_NAMES + scaled_feature_cols].isna().any().any()
    assert not df_test[FEATURE_NAMES + scaled_feature_cols].isna().any().any()

    # 5. Scaled columns strictly in [0, pi]
    train_scaled_vals = df_train[scaled_feature_cols].to_numpy()
    test_scaled_vals = df_test[scaled_feature_cols].to_numpy()

    assert np.all(train_scaled_vals >= 0.0)
    assert np.all(train_scaled_vals <= np.pi)
    assert np.all(test_scaled_vals >= 0.0)
    assert np.all(test_scaled_vals <= np.pi)
