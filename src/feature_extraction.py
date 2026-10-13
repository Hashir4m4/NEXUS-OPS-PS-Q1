"""
ECG Feature Extraction Module
=============================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 3)

Implements six physiologically grounded, scientifically validated numerical features
extracted from 360-sample MLII ECG segments:
1. Pre-RR interval (seconds): Time from previous annotated R-peak to current R-peak.
2. Post-RR interval (seconds): Time from current annotated R-peak to subsequent annotated R-peak.
3. QRS RMS amplitude (mV): Root mean square amplitude in a [-25, +25] sample window (~140 ms) around R-peak.
4. QRS duration / spread (seconds): QRS width estimated by envelope thresholding (20% of peak amplitude).
5. Peak-to-peak amplitude (mV): Dynamic range max(s) - min(s) across the 360-sample window.
6. Spectral band power ratio (dimensionless): Ratio of power in [10, 25] Hz to power in [0.5, 40] Hz.

Leakage Note:
-------------
RR intervals are computed from the complete continuous annotation stream of the originating
recording (.atr file), ensuring true physiological interval measurement.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import wfdb

# Physical Constants
SAMPLING_RATE = 360.0
QRS_INDEX = 144  # Center R-peak index in 360-sample window
RMS_HALF_WINDOW = 25  # +/- 25 samples = +/- 69.4 ms (~140 ms total QRS complex)
DURATION_HALF_WINDOW = 36  # +/- 36 samples = +/- 100 ms search region around R-peak

# Recognized ECG heartbeat annotations in MIT-BIH
BEAT_SYMBOLS = set([
    "N", "L", "R", "B", "A", "a", "J", "S", "V", "r", "F", "e", "j", "n", "E", "/", "f", "Q", "?"
])

FEATURE_NAMES = [
    "pre_rr",
    "post_rr",
    "qrs_rms",
    "qrs_duration",
    "p2p_amplitude",
    "spectral_ratio",
]

FEATURE_METADATA = {
    "pre_rr": {"unit": "seconds", "description": "Preceding RR interval from prior annotated R-peak"},
    "post_rr": {"unit": "seconds", "description": "Succeeding RR interval to subsequent annotated R-peak"},
    "qrs_rms": {"unit": "mV", "description": "Root Mean Square signal amplitude across core QRS window"},
    "qrs_duration": {"unit": "seconds", "description": "QRS complex temporal width via 20% envelope threshold"},
    "p2p_amplitude": {"unit": "mV", "description": "Peak-to-peak amplitude excursion in 360-sample window"},
    "spectral_ratio": {"unit": "dimensionless", "description": "Power spectral ratio: P(10-25 Hz) / P(0.5-40 Hz)"},
}


def compute_rr_intervals_from_annotations(
    beat_index: int,
    ann_samples: np.ndarray,
    ann_symbols: List[str],
    sampling_rate: float = SAMPLING_RATE
) -> Tuple[float, float]:
    """
    Computes preceding (Pre-RR) and succeeding (Post-RR) intervals using
    neighbouring heartbeat annotations in the full recording annotation array.

    Parameters
    ----------
    beat_index : int
        Index of the target beat in the full recording annotation stream.
    ann_samples : np.ndarray
        Sample locations of all annotations in the parent record.
    ann_symbols : List[str]
        Symbols of all annotations in the parent record.
    sampling_rate : float
        Sampling frequency in Hz.

    Returns
    -------
    Tuple[float, float]
        (pre_rr_seconds, post_rr_seconds)
    """
    # Find previous true heartbeat annotation
    p = beat_index - 1
    while p >= 0 and ann_symbols[p] not in BEAT_SYMBOLS:
        p -= 1

    if p >= 0:
        pre_rr = float((ann_samples[beat_index] - ann_samples[p]) / sampling_rate)
    else:
        # Fallback if first beat in record has no prior beat (should not occur in sampled set)
        pre_rr = np.nan

    # Find next true heartbeat annotation
    n = beat_index + 1
    while n < len(ann_symbols) and ann_symbols[n] not in BEAT_SYMBOLS:
        n += 1

    if n < len(ann_symbols):
        post_rr = float((ann_samples[n] - ann_samples[beat_index]) / sampling_rate)
    else:
        post_rr = np.nan

    return pre_rr, post_rr


def compute_qrs_rms(
    signal: np.ndarray,
    r_peak_idx: int = QRS_INDEX,
    half_window: int = RMS_HALF_WINDOW
) -> float:
    """
    Computes Root Mean Square (RMS) amplitude within [-half_window, +half_window]
    around the annotated R-peak.

    Parameters
    ----------
    signal : np.ndarray
        1D ECG segment of length 360 samples in physical units (mV).
    r_peak_idx : int
        Sample index of the R-peak (144).
    half_window : int
        Number of samples to each side of R-peak (default 25 samples = ~69.4 ms).

    Returns
    -------
    float
        RMS amplitude in mV.
    """
    start_idx = max(0, r_peak_idx - half_window)
    end_idx = min(len(signal), r_peak_idx + half_window + 1)
    qrs_core = signal[start_idx:end_idx]

    rms = np.sqrt(np.mean(qrs_core ** 2))
    return float(rms)


def compute_qrs_duration(
    signal: np.ndarray,
    r_peak_idx: int = QRS_INDEX,
    half_window: int = DURATION_HALF_WINDOW,
    relative_threshold: float = 0.20,
    sampling_rate: float = SAMPLING_RATE
) -> float:
    """
    Estimates QRS complex temporal width (duration) using envelope thresholding:
    1. Extracts region of interest around R-peak: [-half_window, +half_window].
    2. Subtracts local baseline (median of ROI).
    3. Computes rectified envelope |s - baseline|.
    4. Finds onset and offset boundaries where envelope drops below relative_threshold * peak_amplitude.
    5. Duration = (offset - onset) / sampling_rate.

    Parameters
    ----------
    signal : np.ndarray
        1D ECG segment of length 360 samples.
    r_peak_idx : int
        Center R-peak sample (144).
    half_window : int
        Search window half-width (default 36 samples = +/- 100 ms).
    relative_threshold : float
        Fraction of peak envelope defining QRS limits (default 0.20 = 20%).
    sampling_rate : float
        Sampling frequency in Hz.

    Returns
    -------
    float
        QRS duration in seconds.
    """
    start_idx = max(0, r_peak_idx - half_window)
    end_idx = min(len(signal), r_peak_idx + half_window + 1)
    roi = signal[start_idx:end_idx]

    local_baseline = np.median(roi)
    envelope = np.abs(roi - local_baseline)
    peak_val = np.max(envelope)

    if peak_val <= 1e-6:
        # Flatline / zero amplitude edge case
        return 0.0

    threshold = relative_threshold * peak_val
    local_r_idx = r_peak_idx - start_idx

    # Scan left from R-peak to find onset
    left_bound = local_r_idx
    while left_bound > 0 and envelope[left_bound] >= threshold:
        left_bound -= 1

    # Scan right from R-peak to find offset
    right_bound = local_r_idx
    while right_bound < len(envelope) - 1 and envelope[right_bound] >= threshold:
        right_bound += 1

    duration_samples = right_bound - left_bound
    return float(duration_samples / sampling_rate)


def compute_peak_to_peak_amplitude(signal: np.ndarray) -> float:
    """
    Computes peak-to-peak dynamic amplitude range: max(signal) - min(signal).

    Parameters
    ----------
    signal : np.ndarray
        1D ECG segment.

    Returns
    -------
    float
        Peak-to-peak amplitude in mV.
    """
    return float(np.ptp(signal))


def compute_spectral_band_power_ratio(
    signal: np.ndarray,
    sampling_rate: float = SAMPLING_RATE,
    low_band: Tuple[float, float] = (10.0, 25.0),
    total_band: Tuple[float, float] = (0.5, 40.0),
    n_fft: int = 720,
    eps: float = 1e-12
) -> float:
    """
    Computes the spectral band power ratio: Power(10-25 Hz) / Power(0.5-40 Hz)
    using zero-padded Real Fast Fourier Transform (RFFT) for high frequency resolution.

    Parameters
    ----------
    signal : np.ndarray
        1D ECG segment.
    sampling_rate : float
        Sampling rate in Hz (360.0).
    low_band : Tuple[float, float]
        Target high-energy QRS band (default 10.0 to 25.0 Hz).
    total_band : Tuple[float, float]
        Reference broadband baseline (default 0.5 to 40.0 Hz).
    n_fft : int
        FFT size (720 points yields 0.5 Hz bin spacing).
    eps : float
        Numerical regularizer to prevent zero division.

    Returns
    -------
    float
        Dimensionless spectral power ratio in [0, 1].
    """
    fft_vals = np.fft.rfft(signal, n=n_fft)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sampling_rate)
    psd = np.abs(fft_vals) ** 2

    qrs_mask = (freqs >= low_band[0]) & (freqs <= low_band[1])
    tot_mask = (freqs >= total_band[0]) & (freqs <= total_band[1])

    power_qrs = np.sum(psd[qrs_mask])
    power_tot = np.sum(psd[tot_mask])

    ratio = power_qrs / (power_tot + eps)
    return float(np.clip(ratio, 0.0, 1.0))


def extract_features_for_dataframe(
    df: pd.DataFrame,
    data_dir: Path = Path("data") / "mitbih"
) -> pd.DataFrame:
    """
    Extracts all six candidate features for all rows in the dataset DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing segment metadata and signal samples s_0 to s_359.
    data_dir : Path
        Directory containing raw WFDB record files (.atr) for true RR lookups.

    Returns
    -------
    pd.DataFrame
        DataFrame with metadata, class labels, and 6 raw feature columns.
    """
    # Pre-load all required annotations once per record
    unique_records = df["record_id"].astype(str).unique()
    cached_annotations: Dict[str, Tuple[np.ndarray, List[str]]] = {}

    for rec_id in unique_records:
        rec_path = data_dir / rec_id
        ann = wfdb.rdann(str(rec_path), "atr")
        cached_annotations[rec_id] = (
            np.asarray(ann.sample, dtype=np.int64),
            list(ann.symbol),
        )

    sig_cols = [f"s_{i}" for i in range(360)]
    feature_rows = []

    for _, row in df.iterrows():
        rec_id = str(row["record_id"])
        ann_samples, ann_symbols = cached_annotations[rec_id]
        beat_idx = int(row["beat_index"])

        # 1 & 2. RR intervals
        pre_rr, post_rr = compute_rr_intervals_from_annotations(
            beat_idx, ann_samples, ann_symbols, sampling_rate=row["sampling_rate"]
        )

        # Signal array
        sig = row[sig_cols].to_numpy(dtype=float)

        # 3. QRS RMS
        qrs_rms = compute_qrs_rms(sig, r_peak_idx=QRS_INDEX)

        # 4. QRS Duration
        qrs_dur = compute_qrs_duration(sig, r_peak_idx=QRS_INDEX)

        # 5. Peak-to-peak amplitude
        p2p = compute_peak_to_peak_amplitude(sig)

        # 6. Spectral ratio
        spec_ratio = compute_spectral_band_power_ratio(sig, sampling_rate=row["sampling_rate"])

        feat_dict = {
            "segment_id": row["segment_id"],
            "record_id": rec_id,
            "split": row["split"],
            "label": int(row["label"]),
            "annotation_symbol": row["annotation_symbol"],
            "pre_rr": pre_rr,
            "post_rr": post_rr,
            "qrs_rms": qrs_rms,
            "qrs_duration": qrs_dur,
            "p2p_amplitude": p2p,
            "spectral_ratio": spec_ratio,
        }
        feature_rows.append(feat_dict)

    df_features = pd.DataFrame(feature_rows)
    return df_features
