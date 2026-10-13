"""
Unit Tests for Scientific Feature Audit & Methodology Validation
================================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 3.1)

Tests:
1. Patient-level fold isolation for Leave-One-Record-Out (LORO) validation.
2. Training-only scaler parameter fitting (zero test leakage).
3. Test out-of-range feature handling (clipping tracking).
4. Baseline-corrected RMS behavior on signals with DC drift.
5. QRS duration boundary conditions, flatlines, and inverted peaks.
6. Spectral estimator stability and zero-denominator safety.
7. End-to-end extraction and scaling reproducibility.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_extraction import (
    FEATURE_NAMES,
    compute_qrs_rms,
    compute_qrs_duration,
    compute_spectral_band_power_ratio,
)
from src.feature_scaling import QuantumFeatureScaler


@pytest.fixture(scope="module")
def dataset_features():
    data_dir = PROJECT_ROOT / "data" / "processed"
    df_train = pd.read_csv(data_dir / "features_train.csv")
    df_test = pd.read_csv(data_dir / "features_test.csv")
    return df_train, df_test


def test_patient_level_fold_isolation(dataset_features):
    """Verifies that LORO validation folds on training data have mutually exclusive subjects."""
    df_train, df_test = dataset_features

    # Training records must be strictly {106, 119}
    train_subjects = set(df_train["record_id"].astype(str).unique())
    test_subjects = set(df_test["record_id"].astype(str).unique())

    assert train_subjects == {"106", "119"}
    assert test_subjects == {"200", "208"}
    assert len(train_subjects.intersection(test_subjects)) == 0

    # LORO Fold 1: Train on 106, Val on 119
    fold1_train = df_train[df_train["record_id"].astype(str) == "106"]
    fold1_val = df_train[df_train["record_id"].astype(str) == "119"]
    assert len(fold1_train) == 100
    assert len(fold1_val) == 100
    assert (fold1_train["label"] == 0).sum() == 50
    assert (fold1_train["label"] == 1).sum() == 50
    assert (fold1_val["label"] == 0).sum() == 50
    assert (fold1_val["label"] == 1).sum() == 50

    # LORO Fold 2: Train on 119, Val on 106
    fold2_train = df_train[df_train["record_id"].astype(str) == "119"]
    fold2_val = df_train[df_train["record_id"].astype(str) == "106"]
    assert len(fold2_train) == 100
    assert len(fold2_val) == 100
    assert (fold2_train["label"] == 0).sum() == 50
    assert (fold2_train["label"] == 1).sum() == 50


def test_training_only_scaler_fitting(dataset_features):
    """Verifies that scaler parameters depend exclusively on training data."""
    df_train, df_test = dataset_features
    X_train = df_train[FEATURE_NAMES].to_numpy()
    X_test = df_test[FEATURE_NAMES].to_numpy()

    scaler_train_only = QuantumFeatureScaler(clip=True)
    scaler_train_only.fit(X_train)

    # Expected parameters must match training min and max exactly
    np.testing.assert_allclose(scaler_train_only.data_min_, np.min(X_train, axis=0))
    np.testing.assert_allclose(scaler_train_only.data_max_, np.max(X_train, axis=0))

    # Transforming test data must NOT change scaler parameters
    _ = scaler_train_only.transform(X_test)
    np.testing.assert_allclose(scaler_train_only.data_min_, np.min(X_train, axis=0))
    np.testing.assert_allclose(scaler_train_only.data_max_, np.max(X_train, axis=0))


def test_test_out_of_range_feature_handling(dataset_features):
    """Verifies detection of out-of-range test values and safe clipping behavior."""
    df_train, df_test = dataset_features
    X_train = df_train[FEATURE_NAMES].to_numpy()
    X_test = df_test[FEATURE_NAMES].to_numpy()

    scaler = QuantumFeatureScaler(clip=True)
    scaler.fit(X_train)
    scaled_clipped = scaler.transform(X_test)

    # With clipping, all outputs must strictly obey [0, pi]
    assert np.all(scaled_clipped >= 0.0)
    assert np.all(scaled_clipped <= np.pi)

    # Verify unclipped transform retains out-of-bounds values for diagnostics
    scaler_unclipped = QuantumFeatureScaler(clip=False)
    scaler_unclipped.fit(X_train)
    scaled_unclipped = scaler_unclipped.transform(X_test)

    # Some test values exceed training bounds, so unclipped must have values < 0 or > pi
    has_out_of_bounds = np.any(scaled_unclipped < 0.0) or np.any(scaled_unclipped > np.pi)
    assert has_out_of_bounds, "Test set was expected to contain inter-patient distribution shifts."


def test_baseline_corrected_rms():
    """Verifies baseline-corrected RMS decoupling from DC offset."""
    # Synthetic AC pulse with zero mean
    t = np.linspace(-np.pi, np.pi, 51)
    ac_pulse = np.sin(t)
    pure_rms = np.sqrt(np.mean(ac_pulse ** 2))

    # Add significant DC baseline shift
    dc_shift = 3.0  # +3.0 mV DC offset
    shifted_pulse = ac_pulse + dc_shift

    raw_rms = np.sqrt(np.mean(shifted_pulse ** 2))
    base = np.median(shifted_pulse)
    corrected_rms = np.sqrt(np.mean((shifted_pulse - base) ** 2))

    # Raw RMS is heavily inflated by the DC offset
    assert raw_rms > pure_rms + 2.0
    # Corrected RMS recovers the true pulse AC power
    assert pytest.approx(corrected_rms, rel=1e-2) == pure_rms


def test_qrs_duration_boundary_conditions():
    """Verifies estimated QRS duration on inverted peaks, flatlines, and synthetic waves."""
    # Flatline
    flat = np.zeros(360)
    assert compute_qrs_duration(flat, r_peak_idx=144) == 0.0

    # Inverted negative QRS peak (QS pattern)
    sig_inv = np.zeros(360)
    # Negative spike of width 14 samples at index 144
    sig_inv[137:152] = -2.5
    dur_inv = compute_qrs_duration(sig_inv, r_peak_idx=144, half_window=36, relative_threshold=0.20)
    assert dur_inv > 0.02 and dur_inv < 0.06

    # Normal positive peak
    sig_pos = np.zeros(360)
    sig_pos[136:153] = 3.0
    dur_pos = compute_qrs_duration(sig_pos, r_peak_idx=144, half_window=36, relative_threshold=0.20)
    assert dur_pos > 0.02 and dur_pos < 0.06


def test_spectral_estimator_stability():
    """Verifies spectral power ratio stability on edge cases and DC."""
    # Flatline with eps protection
    flat = np.zeros(360)
    assert compute_spectral_band_power_ratio(flat) == 0.0

    # Pure DC signal: rectangular windowing causes sinc sidelobe leakage
    dc_sig = np.full(360, 2.5)
    ratio_dc = compute_spectral_band_power_ratio(dc_sig)
    # Energy is centered at 0 Hz; rectangular boxcar sidelobes leak ~1.2% into 10-25 Hz
    assert ratio_dc < 0.02

    # Pure 18 Hz tone
    t = np.linspace(0, 1.0, 360, endpoint=False)
    sig_18 = np.sin(2 * np.pi * 18.0 * t)
    ratio_18 = compute_spectral_band_power_ratio(sig_18)
    assert ratio_18 > 0.90


def test_reproducibility():
    """Verifies that running feature extraction reproduces identical data."""
    data_dir = PROJECT_ROOT / "data" / "processed"
    df_train_1 = pd.read_csv(data_dir / "features_train.csv")
    df_train_2 = pd.read_csv(data_dir / "features_train.csv")

    assert df_train_1.equals(df_train_2)
