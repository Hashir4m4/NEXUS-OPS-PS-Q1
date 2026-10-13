"""
ECG Data Loader Module
======================
Infrastructure for loading and validating ECG records and clinical annotations
from the MIT-BIH Arrhythmia Database (PhysioNet WFDB format).

WFDB File Structure Overview:
-----------------------------
A standard WFDB record consists of three complementary files sharing a common basename:
  1. `<record_id>.hea` (Header File - Text/ASCII):
     - Specifies sampling frequency (e.g., 360 Hz for MIT-BIH).
     - Number of leads / signals (typically 2: MLII and V1/V5).
     - Total signal length (sample count and duration).
     - ADC gain, baseline offset, ADC resolution, and physical units (typically mV).
  2. `<record_id>.dat` (Signal File - Binary):
     - Raw multiplexed 12-bit or 16-bit binary samples.
     - Converted into physical units (mV) via: (raw_adc - baseline) / gain.
  3. `<record_id>.atr` (Annotation File - Binary):
     - Beat-by-beat clinical annotations timestamped by sample index.
     - Clinical annotation symbols indicating rhythm and beat types (e.g., 'N', 'V', 'A', 'L', 'R').

Note:
-----
Final annotation-to-binary-label mapping and dataset splits are intentionally deferred
pending explicit hackathon organizer specification.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import wfdb
except ImportError:
    wfdb = None


@dataclass
class ECGRecord:
    """Container holding loaded ECG signal, metadata, and clinical annotations."""
    record_id: str
    sampling_rate: float
    lead_names: List[str]
    signal: np.ndarray  # Shape: (n_samples, n_leads) in physical units (mV)
    annotation_samples: np.ndarray  # Shape: (n_annotations,), sample indices
    annotation_symbols: List[str]  # Clinical symbol strings (e.g., 'N', 'V')
    units: List[str]


def check_wfdb_installed() -> None:
    """Verifies whether the wfdb library is installed and importable."""
    if wfdb is None:
        raise ImportError(
            "The 'wfdb' package is required to load PhysioNet WFDB files. "
            "Please install it in your environment using: pip install wfdb"
        )


def validate_sampling_frequency(
    actual_fs: float,
    expected_fs: float = 360.0,
    tolerance: float = 0.1
) -> bool:
    """
    Validates that the record sampling frequency matches the expected rate.

    Parameters
    ----------
    actual_fs : float
        Sampling frequency parsed from the record header.
    expected_fs : float, default=360.0
        Expected sampling rate (MIT-BIH standard is 360 Hz).
    tolerance : float, default=0.1
        Allowable absolute deviation in Hz.

    Returns
    -------
    bool
        True if within tolerance, False otherwise.
    """
    if actual_fs is None or np.isnan(actual_fs) or actual_fs <= 0:
        return False
    return abs(actual_fs - expected_fs) <= tolerance


def validate_signal_integrity(
    signal: np.ndarray,
    min_length: int = 1
) -> Tuple[bool, List[str]]:
    """
    Validates physical signal integrity against non-finites and invalid shapes.

    Parameters
    ----------
    signal : np.ndarray
        Array representing the multi-channel or single-channel ECG signal.
    min_length : int, default=1
        Minimum acceptable sample count.

    Returns
    -------
    Tuple[bool, List[str]]
        (is_valid, list_of_error_messages)
    """
    errors: List[str] = []

    if signal is None:
        return False, ["Signal array is None."]

    if not isinstance(signal, np.ndarray):
        return False, ["Signal must be a numpy ndarray."]

    if signal.size == 0 or len(signal) < min_length:
        errors.append(f"Signal length {len(signal)} is below minimum length {min_length}.")

    if np.isnan(signal).any():
        errors.append("Signal contains NaN (missing) values.")

    if np.isinf(signal).any():
        errors.append("Signal contains infinite values.")

    return (len(errors) == 0, errors)


def validate_annotation_alignment(
    annotation_samples: np.ndarray,
    signal_length: int
) -> Tuple[bool, List[str]]:
    """
    Validates that annotation sample indices are properly aligned within signal bounds.

    Parameters
    ----------
    annotation_samples : np.ndarray
        Sample indices of marked annotations.
    signal_length : int
        Total sample length of the ECG recording.

    Returns
    -------
    Tuple[bool, List[str]]
        (is_valid, list_of_error_messages)
    """
    errors: List[str] = []

    if annotation_samples is None:
        return False, ["Annotation samples array is None."]

    if len(annotation_samples) == 0:
        return True, []  # Empty annotations valid structurally, but flagged if non-empty needed

    if (annotation_samples < 0).any():
        errors.append("Annotation sample index contains negative values.")

    if (annotation_samples >= signal_length).any():
        errors.append(
            f"Annotation sample indices exceed signal length ({signal_length})."
        )

    # Check temporal ordering
    if not np.all(np.diff(annotation_samples) >= 0):
        errors.append("Annotation samples are not strictly monotonically non-decreasing.")

    return (len(errors) == 0, errors)


def load_wfdb_record(
    record_path_or_id: Union[str, Path],
    expected_fs: Optional[float] = 360.0
) -> ECGRecord:
    """
    Loads an ECG recording (.hea, .dat) and corresponding reference annotations (.atr).

    Parameters
    ----------
    record_path_or_id : Union[str, Path]
        Path or identifier to the WFDB record without extension (e.g. 'data/mitbih/100').
    expected_fs : Optional[float], default=360.0
        If provided, validates the sampling frequency.

    Returns
    -------
    ECGRecord
        Structured dataclass holding the signal and annotations.
    """
    check_wfdb_installed()

    record_str = str(record_path_or_id)
    record = wfdb.rdrecord(record_str)
    annotation = wfdb.rdann(record_str, "atr")

    # Validate sampling frequency
    if expected_fs is not None:
        if not validate_sampling_frequency(record.fs, expected_fs=expected_fs):
            raise ValueError(
                f"Sampling rate mismatch for {record.record_name}: "
                f"expected {expected_fs} Hz, found {record.fs} Hz"
            )

    # Validate signal integrity
    valid_sig, sig_errors = validate_signal_integrity(record.p_signal)
    if not valid_sig:
        raise ValueError(
            f"Signal validation failed for record {record.record_name}: {'; '.join(sig_errors)}"
        )

    # Validate annotation alignment
    valid_ann, ann_errors = validate_annotation_alignment(
        annotation.sample, len(record.p_signal)
    )
    if not valid_ann:
        raise ValueError(
            f"Annotation alignment failed for record {record.record_name}: {'; '.join(ann_errors)}"
        )

    return ECGRecord(
        record_id=record.record_name,
        sampling_rate=float(record.fs),
        lead_names=list(record.sig_name),
        signal=record.p_signal,
        annotation_samples=np.asarray(annotation.sample, dtype=np.int64),
        annotation_symbols=list(annotation.symbol),
        units=list(record.units),
    )
