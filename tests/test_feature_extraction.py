"""
Unit Tests for Feature Extraction Module
========================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 3)

Validates mathematical correctness, physical ranges, and edge-case robustness
for all six ECG feature extraction functions.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_extraction import (
    compute_rr_intervals_from_annotations,
    compute_qrs_rms,
    compute_qrs_duration,
    compute_peak_to_peak_amplitude,
    compute_spectral_band_power_ratio,
    FEATURE_NAMES,
)


def test_rr_intervals_calculation():
    """Tests Pre-RR and Post-RR calculation with beat and auxiliary annotations."""
    # Synthetic annotation sequence: [beat at 0, rhythm mark '+' at 100, beat at 360, beat at 720]
    samples = np.array([0, 100, 360, 720], dtype=np.int64)
    symbols = ["N", "+", "V", "N"]

    # Target is beat index 2 (sample 360)
    pre_rr, post_rr = compute_rr_intervals_from_annotations(
        beat_index=2,
        ann_samples=samples,
        ann_symbols=symbols,
        sampling_rate=360.0
    )

    # Pre-RR should skip the '+' at index 1 and look at index 0 (sample 0)
    # Distance = (360 - 0) / 360 = 1.0 s
    assert pytest.approx(pre_rr, rel=1e-4) == 1.0

    # Post-RR should look at index 3 (sample 720)
    # Distance = (720 - 360) / 360 = 1.0 s
    assert pytest.approx(post_rr, rel=1e-4) == 1.0


def test_qrs_rms():
    """Tests RMS calculation on a constant signal and impulse."""
    sig = np.zeros(360)
    # Fill core QRS region with 2.0 mV
    sig[144 - 25 : 144 + 26] = 2.0

    rms = compute_qrs_rms(sig, r_peak_idx=144, half_window=25)
    assert pytest.approx(rms, rel=1e-4) == 2.0

    # Test all-zero signal
    zero_sig = np.zeros(360)
    assert compute_qrs_rms(zero_sig) == 0.0


def test_qrs_duration():
    """Tests duration estimation on a rectangular pulse of known width."""
    sig = np.zeros(360)
    # Create a 20-sample pulse centered at 144 (from 134 to 154)
    sig[134:155] = 1.0

    # With relative threshold 0.20, duration should detect the pulse width
    dur = compute_qrs_duration(sig, r_peak_idx=144, half_window=36, relative_threshold=0.20, sampling_rate=360.0)
    # 20 samples at 360 Hz = 20 / 360 = 0.0555 s
    assert dur > 0.04 and dur < 0.07

    # Flatline signal should return 0.0 safely
    flat_sig = np.zeros(360)
    assert compute_qrs_duration(flat_sig) == 0.0


def test_peak_to_peak_amplitude():
    """Tests dynamic amplitude excursion."""
    sig = np.linspace(-1.5, 2.5, 360)
    p2p = compute_peak_to_peak_amplitude(sig)
    assert pytest.approx(p2p, rel=1e-4) == 4.0


def test_spectral_band_power_ratio():
    """Tests spectral ratio on pure sine waves in and outside target band."""
    fs = 360.0
    t = np.linspace(0, 1.0, 360, endpoint=False)

    # 1. Pure sine wave at 15 Hz (inside 10-25 Hz band and inside 0.5-40 Hz band)
    sig_15hz = np.sin(2 * np.pi * 15.0 * t)
    ratio_15hz = compute_spectral_band_power_ratio(sig_15hz, sampling_rate=fs)
    # Should be close to 1.0
    assert ratio_15hz > 0.90

    # 2. Pure sine wave at 2 Hz (outside 10-25 Hz band, inside 0.5-40 Hz band)
    sig_2hz = np.sin(2 * np.pi * 2.0 * t)
    ratio_2hz = compute_spectral_band_power_ratio(sig_2hz, sampling_rate=fs)
    # Should be close to 0.0
    assert ratio_2hz < 0.10

    # 3. Flatline (all zeros) should handle zero denominator without error
    flat = np.zeros(360)
    ratio_zero = compute_spectral_band_power_ratio(flat, sampling_rate=fs)
    assert ratio_zero == 0.0
