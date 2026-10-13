"""
Dataset Validation Module
=========================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 2B)

Executes rigorous automated verification of the constructed ECG dataset:
1. Segment dimensions equal 360 samples (144 before, 216 after).
2. Zero boundary-violating segments.
3. Total sample count equals 300.
4. Exact class balance: 150 N and 150 V.
5. Exact partition sizes: 200 Train (100 N, 100 V) and 100 Test (50 N, 50 V).
6. Strict patient/record-level isolation (no record overlap between train and test).
7. Zero missing or non-finite signal samples.
8. Complete reproducibility: identical sample selection upon re-execution with seed 42.
9. Adjacent sampled beat overlap analysis.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.dataset_builder import (
    build_dataset,
    TRAIN_RECORDS,
    TEST_RECORDS,
    RANDOM_SEED,
    TOTAL_WINDOW,
)


def validate_dataset_properties(
    df_all: pd.DataFrame,
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    metadata: Dict
) -> Dict:
    """
    Runs comprehensive programmatic verification checks against dataset rules.
    """
    results: Dict[str, Dict] = {}

    # Check 1: Total sample counts
    total_samples = len(df_all)
    train_samples = len(df_train)
    test_samples = len(df_test)
    check1_passed = (total_samples == 300) and (train_samples == 200) and (test_samples == 100)
    results["check_sample_counts"] = {
        "passed": bool(check1_passed),
        "total_samples": total_samples,
        "train_samples": train_samples,
        "test_samples": test_samples,
        "expected": {"total": 300, "train": 200, "test": 100},
    }

    # Check 2: Class balance overall and within splits
    n_total = int((df_all["label"] == 0).sum())
    v_total = int((df_all["label"] == 1).sum())
    n_train = int((df_train["label"] == 0).sum())
    v_train = int((df_train["label"] == 1).sum())
    n_test = int((df_test["label"] == 0).sum())
    v_test = int((df_test["label"] == 1).sum())

    check2_passed = (
        (n_total == 150) and (v_total == 150) and
        (n_train == 100) and (v_train == 100) and
        (n_test == 50) and (v_test == 50)
    )
    results["check_class_balance"] = {
        "passed": bool(check2_passed),
        "overall": {"N": n_total, "V": v_total},
        "train": {"N": n_train, "V": v_train},
        "test": {"N": n_test, "V": v_test},
    }

    # Check 3: Inter-patient record isolation (Zero Leakage)
    train_recs = set(df_train["record_id"].astype(str).unique())
    test_recs = set(df_test["record_id"].astype(str).unique())
    overlap = train_recs.intersection(test_recs)
    expected_train_recs = set(TRAIN_RECORDS)
    expected_test_recs = set(TEST_RECORDS)

    check3_passed = (
        (len(overlap) == 0) and
        (train_recs == expected_train_recs) and
        (test_recs == expected_test_recs)
    )
    results["check_patient_isolation"] = {
        "passed": bool(check3_passed),
        "train_records": sorted(list(train_recs)),
        "test_records": sorted(list(test_recs)),
        "record_overlap": sorted(list(overlap)),
    }

    # Check 4: Signal dimensions and sample completeness
    signal_cols = [c for c in df_all.columns if c.startswith("s_")]
    dim_matches = len(signal_cols) == TOTAL_WINDOW
    window_calc_matches = ((df_all["window_end"] - df_all["window_start"]) == TOTAL_WINDOW).all()

    check4_passed = dim_matches and window_calc_matches
    results["check_segment_dimensions"] = {
        "passed": bool(check4_passed),
        "signal_columns_count": len(signal_cols),
        "expected_window_size": TOTAL_WINDOW,
        "window_duration_seconds": TOTAL_WINDOW / 360.0,
    }

    # Check 5: Signal sample integrity (No NaNs, Infs, or Nulls)
    signal_matrix = df_all[signal_cols].to_numpy()
    has_nan = bool(np.isnan(signal_matrix).any())
    has_inf = bool(np.isinf(signal_matrix).any())
    has_null = bool(df_all[signal_cols].isnull().any().any())

    check5_passed = (not has_nan) and (not has_inf) and (not has_null)
    results["check_signal_finiteness"] = {
        "passed": bool(check5_passed),
        "has_nan": has_nan,
        "has_inf": has_inf,
        "has_null": has_null,
    }

    # Check 6: Boundary validity
    boundary_valid = (
        (df_all["window_start"] >= 0) &
        (df_all["window_end"] <= 650000)
    ).all()
    results["check_boundary_compliance"] = {
        "passed": bool(boundary_valid),
        "min_window_start": int(df_all["window_start"].min()),
        "max_window_end": int(df_all["window_end"].max()),
        "max_record_samples": 650000,
    }

    # Check 7: Overlapping adjacent beat windows among sampled segments
    overlap_count_within_sample = 0
    overlapping_pairs = []
    for rec_id, group in df_all.groupby("record_id"):
        sorted_beats = group.sort_values("r_peak_sample").reset_index()
        for i in range(len(sorted_beats) - 1):
            curr_end = sorted_beats.loc[i, "window_end"]
            next_start = sorted_beats.loc[i + 1, "window_start"]
            if next_start < curr_end:
                overlap_count_within_sample += 1
                overlapping_pairs.append({
                    "record_id": rec_id,
                    "beat_1": sorted_beats.loc[i, "segment_id"],
                    "beat_2": sorted_beats.loc[i + 1, "segment_id"],
                    "overlap_samples": int(curr_end - next_start),
                })

    results["check_sampled_window_overlap"] = {
        "overlap_count_in_selected_subset": overlap_count_within_sample,
        "overlapping_pairs": overlapping_pairs,
        "note": (
            "Because 300 beats are sparsely subsampled across ~9,100 total beats, "
            "most selected beats do not overlap with each other."
        ),
    }

    # Check 8: Determinism verification
    print("[*] Re-running dataset build to verify seed determinism...")
    df_all_repeat, _, _, _ = build_dataset(seed=RANDOM_SEED)
    is_identical = df_all.equals(df_all_repeat)
    results["check_seed_determinism"] = {
        "passed": bool(is_identical),
        "seed_used": RANDOM_SEED,
        "repeated_run_exact_match": bool(is_identical),
    }

    # Global status
    all_critical_passed = (
        check1_passed and check2_passed and check3_passed and
        check4_passed and check5_passed and boundary_valid and is_identical
    )
    results["overall_validation_status"] = "PASSED" if all_critical_passed else "FAILED"

    return results


def run_validation():
    """Generates dataset, validates all criteria, and saves validation JSON."""
    df_all, df_train, df_test, metadata = build_dataset(seed=RANDOM_SEED)
    val_report = validate_dataset_properties(df_all, df_train, df_test, metadata)

    # Attach summary metadata
    val_report["dataset_metadata"] = metadata

    # Save to results/dataset_validation.json
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / "dataset_validation.json"

    def np_encoder(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(val_report, f, indent=2, default=np_encoder)

    print(f"\n[+] Validation JSON written to: {json_path}")
    print(f"[+] Overall Status: {val_report['overall_validation_status']}")

    return val_report


if __name__ == "__main__":
    run_validation()
