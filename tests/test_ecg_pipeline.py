"""
Unit Tests for ECG Data Pipeline (Synthetic Fixtures Only)
==========================================================
CRITICAL: ALL TESTS USE SYNTHETICALLY GENERATED FIXTURES.
NO REAL CLINICAL OR BIOMEDICAL DATASETS ARE DOWNLOADED OR PROCESSED HERE.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import (
    validate_sampling_frequency,
    validate_signal_integrity,
    validate_annotation_alignment,
)
from src.signal_preprocessing import (
    check_segment_boundaries,
    segment_ecg_signal,
    scale_features_to_quantum_range,
    ECGSegment,
)


# ==========================================
# SYNTHETIC FIXTURES (CLEARLY MARKED)
# ==========================================

def generate_synthetic_ecg_lead(
    duration_seconds: float = 10.0,
    fs: float = 360.0
) -> Tuple[np.ndarray, np.ndarray, list]:
    """
    SYNTHETIC FIXTURE GENERATOR:
    Synthesizes a simple sinusoidal signal with artificial 'R-peaks'
    at 1.0 second intervals for testing data ingestion pipelines.
    """
    n_samples = int(duration_seconds * fs)
    t = np.linspace(0, duration_seconds, n_samples, endpoint=False)
    # Synthetic baseline sine wave
    signal = 0.2 * np.sin(2 * np.pi * 1.0 * t)

    # Place artificial pulse peaks every second (e.g. at 1s, 2s, 3s, ...)
    peak_times = np.arange(0.2, duration_seconds, 1.0)
    annotation_samples = np.array([int(pt * fs) for pt in peak_times], dtype=np.int64)
    for p in annotation_samples:
        if p < n_samples:
            signal[p] += 1.5  # Artificial spike

    # Artificial symbol list (alternating synthetic 'N' and 'V' symbols for testing)
    annotation_symbols = ["N" if i % 2 == 0 else "V" for i in range(len(annotation_samples))]

    return signal, annotation_samples, annotation_symbols


# ==========================================
# DATA LOADER VALIDATION TESTS
# ==========================================

def test_validate_sampling_frequency():
    """Tests sampling rate validation tolerance."""
    assert validate_sampling_frequency(360.0, expected_fs=360.0) is True
    assert validate_sampling_frequency(360.05, expected_fs=360.0, tolerance=0.1) is True
    assert validate_sampling_frequency(250.0, expected_fs=360.0) is False
    assert validate_sampling_frequency(-360.0, expected_fs=360.0) is False
    assert validate_sampling_frequency(float("nan"), expected_fs=360.0) is False


def test_validate_signal_integrity():
    """Tests detection of NaNs, Infs, and empty arrays."""
    clean_signal = np.array([0.1, 0.2, 0.5, 0.2, 0.1])
    valid, errors = validate_signal_integrity(clean_signal)
    assert valid is True
    assert len(errors) == 0

    nan_signal = np.array([0.1, np.nan, 0.5])
    valid_nan, errors_nan = validate_signal_integrity(nan_signal)
    assert valid_nan is False
    assert any("NaN" in e for e in errors_nan)

    inf_signal = np.array([0.1, np.inf, 0.5])
    valid_inf, errors_inf = validate_signal_integrity(inf_signal)
    assert valid_inf is False
    assert any("infinite" in e for e in errors_inf)

    empty_signal = np.array([])
    valid_empty, errors_empty = validate_signal_integrity(empty_signal, min_length=10)
    assert valid_empty is False


def test_validate_annotation_alignment():
    """Tests validation of annotation indices against signal bounds."""
    sig_len = 1000
    valid_samples = np.array([100, 250, 500, 750])
    is_valid, errors = validate_annotation_alignment(valid_samples, sig_len)
    assert is_valid is True

    # Out of upper bound
    oob_samples = np.array([100, 500, 1000])  # 1000 is invalid index for length 1000
    is_valid_oob, errors_oob = validate_annotation_alignment(oob_samples, sig_len)
    assert is_valid_oob is False
    assert any("exceed" in e for e in errors_oob)

    # Negative index
    neg_samples = np.array([-5, 100, 200])
    is_valid_neg, errors_neg = validate_annotation_alignment(neg_samples, sig_len)
    assert is_valid_neg is False

    # Non-monotonic
    non_mono = np.array([200, 100, 300])
    is_valid_mono, errors_mono = validate_annotation_alignment(non_mono, sig_len)
    assert is_valid_mono is False


# ==========================================
# PREPROCESSING & SEGMENTATION TESTS
# ==========================================

def test_check_segment_boundaries():
    """Tests boundary condition verification for fixed-length windows."""
    sig_len = 500
    win_before = 100
    win_after = 100

    # Inside bounds
    assert check_segment_boundaries(150, sig_len, win_before, win_after) is True
    # Exactly at boundary start
    assert check_segment_boundaries(100, sig_len, win_before, win_after) is True
    # Boundary start violation
    assert check_segment_boundaries(99, sig_len, win_before, win_after) is False
    # Exactly at boundary end
    assert check_segment_boundaries(400, sig_len, win_before, win_after) is True
    # Boundary end violation
    assert check_segment_boundaries(401, sig_len, win_before, win_after) is False


def test_segment_ecg_signal_with_synthetic_data():
    """
    Tests beat segmentation on a synthetic signal fixture.
    Verifies window size, record ID preservation, and label unassigned status.
    """
    sig, ann_samples, ann_symbols = generate_synthetic_ecg_lead(duration_seconds=5.0, fs=360.0)
    record_id = "SYNTHETIC_PATIENT_001"
    win_before = 100
    win_after = 150
    expected_segment_len = win_before + win_after

    segments, dropped = segment_ecg_signal(
        signal=sig,
        annotation_samples=ann_samples,
        annotation_symbols=ann_symbols,
        record_id=record_id,
        window_before=win_before,
        window_after=win_after,
        lead_name="SYNTHETIC_LEAD"
    )

    assert len(segments) > 0
    for seg in segments:
        # 1. Verify fixed length
        assert len(seg.signal) == expected_segment_len
        # 2. Verify record ID is preserved for patient-level isolation
        assert seg.record_id == record_id
        # 3. Verify label remains unassigned per hackathon rule
        assert seg.label is None
        # 4. Verify original annotation symbol is preserved
        assert seg.annotation_symbol in ["N", "V"]


def test_scale_features_to_quantum_range():
    """Tests that features scale strictly into [0, pi]."""
    synthetic_features = np.array([
        [-10.0, 5.0, 100.0],
        [0.0, 10.0, 200.0],
        [10.0, 15.0, 300.0]
    ])
    scaled = scale_features_to_quantum_range(synthetic_features, min_val=0.0, max_val=np.pi)

    assert scaled.shape == synthetic_features.shape
    assert np.all(scaled >= 0.0)
    assert np.all(scaled <= np.pi)
    # Check that minimum is 0 and maximum is pi along columns
    np.testing.assert_allclose(np.min(scaled, axis=0), 0.0)
    np.testing.assert_allclose(np.max(scaled, axis=0), np.pi)
