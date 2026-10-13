"""
Dataset Builder Module
======================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 2B)

Constructs the standardized, leak-free 300-segment ECG dataset from
the MIT-BIH Arrhythmia Database for binary classification:
  Class 0: Normal Sinus Beat ('N')
  Class 1: Ventricular Ectopic Beat ('V')

Split Configuration:
--------------------
- Training partition (Records 106 & 119):
    * 100 N segments (50 from 106, 50 from 119)
    * 100 V segments (50 from 106, 50 from 119)
    * Total: 200 segments
- Test partition (Records 200 & 208):
    * 50 N segments (25 from 200, 25 from 208)
    * 50 V segments (25 from 200, 25 from 208)
    * Total: 100 segments
- Total dataset: 300 segments (150 N, 150 V, 1:1 balance)
- Inter-patient isolation: Exactly zero subject overlap between partitions.
- Random Seed: 42 (strictly deterministic selection).
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import wfdb

# Project root in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_loader import (
    validate_sampling_frequency,
    validate_signal_integrity,
    validate_annotation_alignment,
)
from src.signal_preprocessing import check_segment_boundaries

# Constants
SAMPLING_RATE = 360.0
WINDOW_BEFORE = 144   # 400 ms
WINDOW_AFTER = 216    # 600 ms
TOTAL_WINDOW = WINDOW_BEFORE + WINDOW_AFTER  # 360 samples
LEAD_NAME = "MLII"
RANDOM_SEED = 42

TRAIN_RECORDS = ["106", "119"]
TEST_RECORDS = ["200", "208"]

# Quotas per record: (N_count, V_count)
RECORD_QUOTAS = {
    "106": {"N": 50, "V": 50, "split": "train"},
    "119": {"N": 50, "V": 50, "split": "train"},
    "200": {"N": 25, "V": 25, "split": "test"},
    "208": {"N": 25, "V": 25, "split": "test"},
}

LABEL_MAPPING = {"N": 0, "V": 1}


def extract_candidate_segments_from_record(
    record_id: str,
    data_dir: Path = PROJECT_ROOT / "data" / "mitbih"
) -> Tuple[List[Dict], List[Dict]]:
    """
    Extracts all valid N and V segments from a specified record.
    Returns:
        (valid_segments, excluded_segments)
    """
    record_path = data_dir / record_id
    record = wfdb.rdrecord(str(record_path))
    annotation = wfdb.rdann(str(record_path), "atr")

    lead_names = list(record.sig_name)
    if LEAD_NAME not in lead_names:
        raise ValueError(f"Record {record_id} does not contain lead '{LEAD_NAME}'. Leads: {lead_names}")
    lead_idx = lead_names.index(LEAD_NAME)
    lead_signal = record.p_signal[:, lead_idx]
    sig_len = len(lead_signal)

    ann_samples = np.asarray(annotation.sample, dtype=np.int64)
    ann_symbols = list(annotation.symbol)

    valid_segments: List[Dict] = []
    excluded_segments: List[Dict] = []

    for beat_idx, (r_peak, symbol) in enumerate(zip(ann_samples, ann_symbols)):
        r_peak = int(r_peak)

        # Check target symbol
        if symbol not in LABEL_MAPPING:
            excluded_segments.append({
                "record_id": record_id,
                "beat_index": beat_idx,
                "r_peak_sample": r_peak,
                "annotation_symbol": symbol,
                "reason": f"Non-target annotation symbol '{symbol}'",
            })
            continue

        # Check boundary compliance
        if not check_segment_boundaries(r_peak, sig_len, WINDOW_BEFORE, WINDOW_AFTER):
            excluded_segments.append({
                "record_id": record_id,
                "beat_index": beat_idx,
                "r_peak_sample": r_peak,
                "annotation_symbol": symbol,
                "reason": "Boundary violation (within 144 samples of start or 216 samples of end)",
            })
            continue

        # Extract window
        start_idx = r_peak - WINDOW_BEFORE
        end_idx = r_peak + WINDOW_AFTER
        segment_data = lead_signal[start_idx:end_idx]

        # Check finiteness
        if not np.isfinite(segment_data).all():
            excluded_segments.append({
                "record_id": record_id,
                "beat_index": beat_idx,
                "r_peak_sample": r_peak,
                "annotation_symbol": symbol,
                "reason": "Non-finite (NaN or Inf) signal samples in segment",
            })
            continue

        valid_segments.append({
            "record_id": record_id,
            "beat_index": beat_idx,
            "r_peak_sample": r_peak,
            "window_start": start_idx,
            "window_end": end_idx,
            "annotation_symbol": symbol,
            "label": LABEL_MAPPING[symbol],
            "lead_name": LEAD_NAME,
            "sampling_rate": float(record.fs),
            "signal": segment_data,
        })

    return valid_segments, excluded_segments


def sample_segments_deterministically(
    valid_segments: List[Dict],
    quota_n: int,
    quota_v: int,
    seed: int = RANDOM_SEED
) -> List[Dict]:
    """
    Subsamples exact quotas of N and V segments using a fixed random seed.
    """
    rng = np.random.default_rng(seed)

    n_pool = [s for s in valid_segments if s["annotation_symbol"] == "N"]
    v_pool = [s for s in valid_segments if s["annotation_symbol"] == "V"]

    if len(n_pool) < quota_n:
        raise ValueError(f"Insufficient N segments: requested {quota_n}, available {len(n_pool)}")
    if len(v_pool) < quota_v:
        raise ValueError(f"Insufficient V segments: requested {quota_v}, available {len(v_pool)}")

    chosen_n_indices = rng.choice(len(n_pool), size=quota_n, replace=False)
    chosen_v_indices = rng.choice(len(v_pool), size=quota_v, replace=False)

    selected_n = [n_pool[i] for i in sorted(chosen_n_indices)]
    selected_v = [v_pool[i] for i in sorted(chosen_v_indices)]

    combined = selected_n + selected_v
    # Sort deterministically by r_peak_sample
    combined.sort(key=lambda x: x["r_peak_sample"])
    return combined


def build_dataset(
    seed: int = RANDOM_SEED,
    output_dir: Path = PROJECT_ROOT / "data" / "processed"
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]:
    """
    Orchestrates extraction, sampling, metadata formatting, and CSV exports.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    all_selected_segments: List[Dict] = []
    all_exclusions: List[Dict] = []
    record_stats: Dict[str, Dict] = {}

    print(f"[*] Building dataset with seed={seed}...")

    for rec_id, config in RECORD_QUOTAS.items():
        # Derive record-specific seed to ensure reproducibility independent of execution order
        rec_seed = seed + int(rec_id)
        valid_segs, excluded_segs = extract_candidate_segments_from_record(rec_id)
        all_exclusions.extend(excluded_segs)

        selected = sample_segments_deterministically(
            valid_segs,
            quota_n=config["N"],
            quota_v=config["V"],
            seed=rec_seed
        )

        for s in selected:
            s["split"] = config["split"]
            s["segment_id"] = f"REC{rec_id}_B{s['beat_index']:04d}_{s['annotation_symbol']}"
            all_selected_segments.append(s)

        record_stats[rec_id] = {
            "split": config["split"],
            "total_valid_N": sum(1 for s in valid_segs if s["annotation_symbol"] == "N"),
            "total_valid_V": sum(1 for s in valid_segs if s["annotation_symbol"] == "V"),
            "selected_N": config["N"],
            "selected_V": config["V"],
            "total_selected": len(selected),
            "excluded_count": len(excluded_segs),
        }
        print(f"  [+] Record {rec_id} ({config['split']}): Selected {config['N']} N, {config['V']} V (Total: {len(selected)})")

    # Construct DataFrame
    rows = []
    for s in all_selected_segments:
        row = {
            "segment_id": s["segment_id"],
            "record_id": s["record_id"],
            "split": s["split"],
            "beat_index": s["beat_index"],
            "r_peak_sample": s["r_peak_sample"],
            "window_start": s["window_start"],
            "window_end": s["window_end"],
            "lead_name": s["lead_name"],
            "sampling_rate": s["sampling_rate"],
            "annotation_symbol": s["annotation_symbol"],
            "label": s["label"],
        }
        # Add 360 signal samples as columns s_0 to s_359
        for i, val in enumerate(s["signal"]):
            row[f"s_{i}"] = float(val)
        rows.append(row)

    df_all = pd.DataFrame(rows)
    df_train = df_all[df_all["split"] == "train"].copy().reset_index(drop=True)
    df_test = df_all[df_all["split"] == "test"].copy().reset_index(drop=True)

    # Save CSVs
    all_csv = output_dir / "ecg_segments.csv"
    train_csv = output_dir / "train.csv"
    test_csv = output_dir / "test.csv"

    df_all.to_csv(all_csv, index=False)
    df_train.to_csv(train_csv, index=False)
    df_test.to_csv(test_csv, index=False)

    print(f"[*] Exported {len(df_all)} total segments:")
    print(f"    - {all_csv} ({len(df_all)} rows)")
    print(f"    - {train_csv} ({len(df_train)} rows: {sum(df_train['label']==0)} N, {sum(df_train['label']==1)} V)")
    print(f"    - {test_csv} ({len(df_test)} rows: {sum(df_test['label']==0)} N, {sum(df_test['label']==1)} V)")

    summary_metadata = {
        "dataset_name": "MIT-BIH_Arrhythmia_NEXUS-OPS_PS-Q1_Phase1",
        "random_seed": seed,
        "sampling_rate_hz": SAMPLING_RATE,
        "window_before_samples": WINDOW_BEFORE,
        "window_after_samples": WINDOW_AFTER,
        "total_window_samples": TOTAL_WINDOW,
        "lead_name": LEAD_NAME,
        "total_samples": len(df_all),
        "train_samples": len(df_train),
        "test_samples": len(df_test),
        "train_records": TRAIN_RECORDS,
        "test_records": TEST_RECORDS,
        "record_statistics": record_stats,
        "total_exclusions": len(all_exclusions),
        "exclusion_breakdown_by_reason": dict(pd.Series([e["reason"] for e in all_exclusions]).value_counts()),
    }

    return df_all, df_train, df_test, summary_metadata


if __name__ == "__main__":
    build_dataset()
