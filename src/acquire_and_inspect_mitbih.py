"""
MIT-BIH Acquisition and Inspection Script
==========================================
NEXUS-OPS PS-Q1: Biomedical Signal Classifier (Milestone 2A)

Scope & Objective:
------------------
Reproducibly acquires the minimal set of candidate records from the MIT-BIH
Arrhythmia Database (PhysioNet), inspects .hea, .dat, and .atr structures,
verifies physical signal integrity and sampling frequency, computes exact
annotation distributions for Normal ('N') and Ventricular Ectopic ('V') beats,
and evaluates 360-sample window boundary constraints.

Inter-Patient Leakage Prevention:
---------------------------------
Each MIT-BIH record corresponds to a distinct subject. Record IDs are strictly
retained across all extracted segments to ensure that partitions (train vs test)
contain mutually exclusive sets of patients.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collections import Counter
from typing import Dict, List, Tuple
import numpy as np
import wfdb

from src.data_loader import (
    validate_sampling_frequency,
    validate_signal_integrity,
    validate_annotation_alignment,
)
from src.signal_preprocessing import check_segment_boundaries

# Minimal candidate records selected from diverse patients:
# Record 106: Subject 207 (F, 24) - High N and V presence
# Record 119: Subject 218 (F, 51) - High N and V presence
# Record 200: Subject 219 (M, 64) - Distinct patient, rich V beats
# Record 208: Subject 220 (F, 63) - Distinct patient, rich V beats
CANDIDATE_RECORDS = ["106", "119", "200", "208"]
MITBIH_DATA_DIR = Path("data") / "mitbih"
WINDOW_BEFORE = 144  # 400 ms at 360 Hz
WINDOW_AFTER = 216   # 600 ms at 360 Hz
TOTAL_WINDOW = WINDOW_BEFORE + WINDOW_AFTER  # 360 samples = 1.0 second


def acquire_candidate_records(
    records: List[str] = CANDIDATE_RECORDS,
    dest_dir: Path = MITBIH_DATA_DIR
) -> List[Path]:
    """
    Downloads only the minimal specified candidate records (.hea, .dat, .atr)
    from PhysioNet's mitdb into the local data directory.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    acquired_paths: List[Path] = []

    print(f"[*] Checking/Acquiring {len(records)} candidate records from PhysioNet mitdb...")
    for rec_id in records:
        record_base = dest_dir / rec_id
        hea_file = dest_dir / f"{rec_id}.hea"
        dat_file = dest_dir / f"{rec_id}.dat"
        atr_file = dest_dir / f"{rec_id}.atr"

        if hea_file.exists() and dat_file.exists() and atr_file.exists():
            print(f"  [+] Record {rec_id} already present locally. Skipping download.")
        else:
            print(f"  [>] Downloading record {rec_id} from PhysioNet...")
            wfdb.dl_database("mitdb", dl_dir=str(dest_dir), records=[rec_id])

        acquired_paths.append(record_base)

    return acquired_paths


def inspect_record(
    record_path: Path,
    window_before: int = WINDOW_BEFORE,
    window_after: int = WINDOW_AFTER
) -> Dict:
    """
    Inspects a single record (.hea, .dat, .atr), validating metadata,
    signal channels, sampling frequency, annotation distributions,
    and boundary compliance.
    """
    record_id = record_path.name
    record_str = str(record_path)

    # 1. Read header and signals (.hea, .dat)
    record = wfdb.rdrecord(record_str)
    # 2. Read annotations (.atr)
    annotation = wfdb.rdann(record_str, "atr")

    fs = float(record.fs)
    n_samples = record.sig_len
    duration_sec = n_samples / fs if fs > 0 else 0
    channels = list(record.sig_name)
    units = list(record.units)

    # Validate sampling rate
    fs_valid = validate_sampling_frequency(fs, expected_fs=360.0)

    # Validate physical signals
    sig_valid, sig_errors = validate_signal_integrity(record.p_signal)

    # Validate annotations
    ann_samples = np.asarray(annotation.sample, dtype=np.int64)
    ann_symbols = list(annotation.symbol)
    ann_valid, ann_errors = validate_annotation_alignment(ann_samples, n_samples)

    # Count clinical symbols
    symbol_counts = Counter(ann_symbols)
    count_N = symbol_counts.get("N", 0)
    count_V = symbol_counts.get("V", 0)

    # Inspect 360-sample window boundary compliance for N and V
    valid_window_N = 0
    dropped_boundary_N = 0
    valid_window_V = 0
    dropped_boundary_V = 0

    for sample_idx, sym in zip(ann_samples, ann_symbols):
        is_boundary_ok = check_segment_boundaries(
            int(sample_idx), n_samples, window_before, window_after
        )
        if sym == "N":
            if is_boundary_ok:
                valid_window_N += 1
            else:
                dropped_boundary_N += 1
        elif sym == "V":
            if is_boundary_ok:
                valid_window_V += 1
            else:
                dropped_boundary_V += 1

    return {
        "record_id": record_id,
        "sampling_rate": fs,
        "fs_valid": fs_valid,
        "n_samples": n_samples,
        "duration_sec": duration_sec,
        "channels": channels,
        "units": units,
        "signal_valid": sig_valid,
        "annotation_valid": ann_valid,
        "total_annotations": len(ann_symbols),
        "symbol_counts": dict(symbol_counts),
        "count_N": count_N,
        "count_V": count_V,
        "valid_window_N": valid_window_N,
        "dropped_boundary_N": dropped_boundary_N,
        "valid_window_V": valid_window_V,
        "dropped_boundary_V": dropped_boundary_V,
    }


def run_inspection() -> List[Dict]:
    """Orchestrates download and inspection across all candidate records."""
    acquired = acquire_candidate_records()
    results = []

    print("\n" + "=" * 80)
    print("MIT-BIH CANDIDATE RECORDS INSPECTION REPORT")
    print("=" * 80)

    for rec_path in acquired:
        info = inspect_record(rec_path)
        results.append(info)

        print(f"\n--- Record {info['record_id']} ---")
        print(f"  Sampling Rate: {info['sampling_rate']} Hz (Valid: {info['fs_valid']})")
        print(f"  Duration: {info['duration_sec']:.1f} s ({info['n_samples']} samples)")
        print(f"  Channels: {info['channels']} | Units: {info['units']}")
        print(f"  Signal Finite & Intact: {info['signal_valid']}")
        print(f"  Annotations Aligned: {info['annotation_valid']}")
        print(f"  Observed 'N' (Normal): {info['count_N']} (Boundary valid: {info['valid_window_N']}, Dropped: {info['dropped_boundary_N']})")
        print(f"  Observed 'V' (VEB):    {info['count_V']} (Boundary valid: {info['valid_window_V']}, Dropped: {info['dropped_boundary_V']})")
        print(f"  All Observed Symbols:  {info['symbol_counts']}")

    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE. NO SPLITS CREATED. NO LABELS FABRICATED.")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_inspection()
