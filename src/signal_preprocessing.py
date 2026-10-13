"""
ECG Signal Preprocessing & Segmentation Module
==============================================
Provides fixed-length beat segmentation with strict boundary checking,
signal filtering utilities, and patient/record tracking to eliminate patient-level leakage.

Leakage Prevention Design:
--------------------------
Every segment explicitly maintains its source `record_id` (patient identifier).
This guarantees that during training/validation/test splitting, splits can be partitioned
strictly at the patient/record level (AAMI inter-patient split), rather than randomly pooling
beats across patients.

Annotation Mapping Deferral:
----------------------------
Raw clinical annotation symbols (e.g. 'N', 'V', 'A', 'L', 'R') are preserved intact.
Binary label assignment (normal vs abnormal) is deferred pending organizer clarification.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np


@dataclass
class ECGSegment:
    """
    Fixed-length segmented ECG beat with associated clinical and patient metadata.
    """
    record_id: str                 # Patient / record identifier (essential to prevent leakage)
    beat_index: int                # Beat ordinal in the parent recording
    r_peak_sample: int             # Original sample index of the R-peak in parent recording
    signal: np.ndarray             # 1D array of length (window_before + window_after)
    lead_name: str                 # Lead name (e.g. 'MLII')
    annotation_symbol: str         # Unmapped clinical symbol (e.g. 'N', 'V', 'A')
    label: Optional[int] = None    # Binary label (left None until mapping confirmed)


def check_segment_boundaries(
    r_peak: int,
    signal_length: int,
    window_before: int,
    window_after: int
) -> bool:
    """
    Checks whether a candidate R-peak allows extraction of a complete, fixed-length window
    without exceeding signal boundaries.

    Parameters
    ----------
    r_peak : int
        Sample index of the R-peak.
    signal_length : int
        Total length of the continuous signal in samples.
    window_before : int
        Number of samples required before the R-peak.
    window_after : int
        Number of samples required after the R-peak.

    Returns
    -------
    bool
        True if the entire window [r_peak - window_before, r_peak + window_after) lies within [0, signal_length).
    """
    if window_before < 0 or window_after < 0:
        raise ValueError("Window lengths must be non-negative integers.")
    
    start_idx = r_peak - window_before
    end_idx = r_peak + window_after

    return (start_idx >= 0) and (end_idx <= signal_length)


def segment_ecg_signal(
    signal: np.ndarray,
    annotation_samples: np.ndarray,
    annotation_symbols: List[str],
    record_id: str,
    window_before: int = 144,
    window_after: int = 216,
    lead_idx: int = 0,
    lead_name: str = "MLII"
) -> Tuple[List[ECGSegment], int]:
    """
    Segments a continuous 1D ECG lead into fixed-length windows centered on R-peaks.

    Parameters
    ----------
    signal : np.ndarray
        ECG signal array. Can be 1D (n_samples,) or 2D (n_samples, n_leads).
    annotation_samples : np.ndarray
        Array of annotated R-peak sample indices.
    annotation_symbols : List[str]
        List of clinical annotation strings matching annotation_samples.
    record_id : str
        Unique record or patient identifier.
    window_before : int, default=144
        Samples preceding the R-peak (144 samples = 400 ms at 360 Hz).
    window_after : int, default=216
        Samples following the R-peak (216 samples = 600 ms at 360 Hz).
        Total window length = 360 samples (1.0 second at 360 Hz).
    lead_idx : int, default=0
        Index of the lead to segment if signal is 2D.
    lead_name : str, default='MLII'
        Name of the lead being segmented.

    Returns
    -------
    Tuple[List[ECGSegment], int]
        (valid_segments, dropped_boundary_count)
    """
    if len(annotation_samples) != len(annotation_symbols):
        raise ValueError("Length mismatch between annotation samples and symbols.")

    # Select lead if multi-channel
    if signal.ndim == 2:
        lead_signal = signal[:, lead_idx]
    elif signal.ndim == 1:
        lead_signal = signal
    else:
        raise ValueError(f"Signal must be 1D or 2D, got shape {signal.shape}")

    signal_length = len(lead_signal)
    segments: List[ECGSegment] = []
    dropped_count = 0

    for idx, (r_peak, symbol) in enumerate(zip(annotation_samples, annotation_symbols)):
        r_peak = int(r_peak)
        if not check_segment_boundaries(r_peak, signal_length, window_before, window_after):
            dropped_count += 1
            continue

        start_idx = r_peak - window_before
        end_idx = r_peak + window_after
        seg_data = lead_signal[start_idx:end_idx].copy()

        # Check for non-finite values in the segment
        if not np.isfinite(seg_data).all():
            dropped_count += 1
            continue

        segment = ECGSegment(
            record_id=str(record_id),
            beat_index=idx,
            r_peak_sample=r_peak,
            signal=seg_data,
            lead_name=lead_name,
            annotation_symbol=symbol,
            label=None  # Left unassigned per hackathon instructions
        )
        segments.append(segment)

    return segments, dropped_count


def scale_features_to_quantum_range(
    features: np.ndarray,
    min_val: float = 0.0,
    max_val: float = np.pi
) -> np.ndarray:
    """
    Utility template to linearly scale numerical feature vectors to the rotational range [min_val, max_val].
    NOTE: In production, scalers must be fitted strictly on training partition features
    to prevent distribution leakage into evaluation folds.

    Parameters
    ----------
    features : np.ndarray
        Array of shape (n_samples, n_features).
    min_val : float, default=0.0
        Lower bound of quantum rotational angle (typically 0).
    max_val : float, default=np.pi
        Upper bound of quantum rotational angle (typically pi).

    Returns
    -------
    np.ndarray
        Scaled feature array strictly bounded within [min_val, max_val].
    """
    col_min = np.min(features, axis=0)
    col_max = np.max(features, axis=0)
    range_diff = np.where(col_max - col_min == 0, 1e-8, col_max - col_min)

    normalized = (features - col_min) / range_diff
    return min_val + normalized * (max_val - min_val)
