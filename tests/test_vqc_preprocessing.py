"""
Unit Tests for Leak-Free VQC Preprocessing Module
=================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 5D)

Verifies:
1. Strict scaler isolation under LORO: Validation perturbations do not alter training scaler.
2. Strict scaler isolation under Final Benchmark: Test perturbations do not alter training scaler.
3. Total independence from precomputed *_scaled columns in LORO.
4. Correct clipping counts at both element-level and beat-level.
5. Preservation of sample ordering, labels, and metadata.
6. Strict confinement of all scaled matrices to [0, pi] without NaNs or Infs.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_extraction import FEATURE_NAMES
from src.vqc_preprocessing import (
    compute_clipping_statistics,
    prepare_loro_fold,
    prepare_loro_datasets,
    prepare_final_benchmark_datasets,
    prepare_all_vqc_datasets,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"


@pytest.fixture(scope="module")
def raw_dataframes():
    train_df = pd.read_csv(DATA_DIR / "features_train.csv")
    test_df = pd.read_csv(DATA_DIR / "features_test.csv")
    return train_df, test_df


def test_loro_scaler_isolation_from_validation_perturbations(raw_dataframes):
    """
    Proves that modifying validation record features has ZERO effect
    on the fitted training scaler parameters in LORO cross-validation.
    """
    train_df, _ = raw_dataframes

    # --- Fold 1 Isolation Test (Train: 106, Val: 119) ---
    corrupted_df_val119 = train_df.copy()
    mask_119 = corrupted_df_val119["record_id"] == 119
    # Add large extreme values to validation patient 119
    for fn in FEATURE_NAMES:
        corrupted_df_val119.loc[mask_119, fn] += 5000.0

    fold1_clean = prepare_loro_fold(train_df, train_record=106, val_record=119, fold_id=1)
    fold1_corrupted = prepare_loro_fold(corrupted_df_val119, train_record=106, val_record=119, fold_id=1)

    # Scaler parameters for Fold 1 must remain 100% identical
    np.testing.assert_array_equal(fold1_clean.scaler.data_min_, fold1_corrupted.scaler.data_min_)
    np.testing.assert_array_equal(fold1_clean.scaler.data_max_, fold1_corrupted.scaler.data_max_)
    np.testing.assert_array_equal(fold1_clean.scaler.scale_, fold1_corrupted.scaler.scale_)
    np.testing.assert_array_equal(fold1_clean.train.X, fold1_corrupted.train.X)

    # --- Fold 2 Isolation Test (Train: 119, Val: 106) ---
    corrupted_df_val106 = train_df.copy()
    mask_106 = corrupted_df_val106["record_id"] == 106
    # Add large extreme values to validation patient 106
    for fn in FEATURE_NAMES:
        corrupted_df_val106.loc[mask_106, fn] -= 2500.0

    fold2_clean = prepare_loro_fold(train_df, train_record=119, val_record=106, fold_id=2)
    fold2_corrupted = prepare_loro_fold(corrupted_df_val106, train_record=119, val_record=106, fold_id=2)

    # Scaler parameters for Fold 2 must remain 100% identical
    np.testing.assert_array_equal(fold2_clean.scaler.data_min_, fold2_corrupted.scaler.data_min_)
    np.testing.assert_array_equal(fold2_clean.scaler.data_max_, fold2_corrupted.scaler.data_max_)
    np.testing.assert_array_equal(fold2_clean.scaler.scale_, fold2_corrupted.scaler.scale_)
    np.testing.assert_array_equal(fold2_clean.train.X, fold2_corrupted.train.X)


def test_final_scaler_isolation_from_test_perturbations(raw_dataframes):
    """
    Proves that test set features (Records 200 & 208) have ZERO effect
    on the final training scaler parameters.
    """
    train_df, test_df = raw_dataframes

    corrupted_test_df = test_df.copy()
    for fn in FEATURE_NAMES:
        corrupted_test_df[fn] = corrupted_test_df[fn] * 100.0 - 50.0

    _, _, clean_scaler = prepare_final_benchmark_datasets(train_df, test_df)
    _, _, corrupted_scaler = prepare_final_benchmark_datasets(train_df, corrupted_test_df)

    # The training scaler must be bitwise identical regardless of test features
    np.testing.assert_array_equal(clean_scaler.data_min_, corrupted_scaler.data_min_)
    np.testing.assert_array_equal(clean_scaler.data_max_, corrupted_scaler.data_max_)
    np.testing.assert_array_equal(clean_scaler.scale_, corrupted_scaler.scale_)


def test_loro_ignores_precomputed_scaled_columns(raw_dataframes):
    """
    Proves that LORO cross-validation never consumes or depends on
    the precomputed *_scaled columns in features_train.csv.
    """
    train_df, _ = raw_dataframes

    # 1. Dataset completely stripped of *_scaled columns
    scaled_cols = [c for c in train_df.columns if c.endswith("_scaled")]
    df_no_scaled = train_df.drop(columns=scaled_cols)
    assert not any(c.endswith("_scaled") for c in df_no_scaled.columns)

    loro_from_clean = prepare_loro_datasets(train_df)
    loro_from_stripped = prepare_loro_datasets(df_no_scaled)

    # Must produce identical transformed matrices and stats
    for fold_id in (1, 2):
        np.testing.assert_array_equal(loro_from_clean[fold_id].train.X, loro_from_stripped[fold_id].train.X)
        np.testing.assert_array_equal(loro_from_clean[fold_id].val.X, loro_from_stripped[fold_id].val.X)

    # 2. Dataset with deliberately poisoned *_scaled columns
    df_poisoned = train_df.copy()
    for sc in scaled_cols:
        df_poisoned[sc] = 99999.9  # Poison with invalid values

    loro_from_poisoned = prepare_loro_datasets(df_poisoned)
    for fold_id in (1, 2):
        np.testing.assert_array_equal(loro_from_clean[fold_id].train.X, loro_from_poisoned[fold_id].train.X)
        np.testing.assert_array_equal(loro_from_clean[fold_id].val.X, loro_from_poisoned[fold_id].val.X)


def test_value_bounds_and_finiteness():
    """Verifies that all partitions output X bounded in [0, pi] without NaNs/Infs."""
    bundle = prepare_all_vqc_datasets(DATA_DIR)

    partitions = [
        bundle.fold1.train,
        bundle.fold1.val,
        bundle.fold2.train,
        bundle.fold2.val,
        bundle.final_train,
        bundle.final_test,
    ]

    for part in partitions:
        assert part.X.dtype == np.float64
        assert not np.isnan(part.X).any(), f"NaN found in {part.name}"
        assert not np.isinf(part.X).any(), f"Inf found in {part.name}"
        assert (part.X >= 0.0).all(), f"Values < 0 found in {part.name}"
        assert (part.X <= np.pi).all(), f"Values > pi found in {part.name}"


def test_metadata_and_order_preservation(raw_dataframes):
    """Verifies preservation of sample ordering, labels, and identifiers."""
    train_df, test_df = raw_dataframes
    bundle = prepare_all_vqc_datasets(DATA_DIR)

    # Final Train
    assert bundle.final_train.segment_ids == train_df["segment_id"].tolist()
    assert bundle.final_train.record_ids == train_df["record_id"].tolist()
    assert (bundle.final_train.y == train_df["label"].to_numpy(dtype=int)).all()
    assert bundle.final_train.annotation_symbols == train_df["annotation_symbol"].tolist()

    # Final Test
    assert bundle.final_test.segment_ids == test_df["segment_id"].tolist()
    assert bundle.final_test.record_ids == test_df["record_id"].tolist()
    assert (bundle.final_test.y == test_df["label"].to_numpy(dtype=int)).all()
    assert bundle.final_test.annotation_symbols == test_df["annotation_symbol"].tolist()

    # Fold 1 Train (Record 106)
    rec106_df = train_df[train_df["record_id"] == 106].reset_index(drop=True)
    assert bundle.fold1.train.segment_ids == rec106_df["segment_id"].tolist()
    assert (bundle.fold1.train.y == rec106_df["label"].to_numpy(dtype=int)).all()

    # Fold 1 Val (Record 119)
    rec119_df = train_df[train_df["record_id"] == 119].reset_index(drop=True)
    assert bundle.fold1.val.segment_ids == rec119_df["segment_id"].tolist()
    assert (bundle.fold1.val.y == rec119_df["label"].to_numpy(dtype=int)).all()


def test_clipping_statistics_exact_counts():
    """
    Verifies that empirical clipping statistics match audited scientific values exactly:
    - Fold 1 Val (119 vs scaler 106): 120 values / 54 beats
    - Fold 2 Val (106 vs scaler 119): 154 values / 89 beats
    - Final Test (200 & 208 vs scaler 106+119): 14 values / 13 beats
    - Training partitions: 0 values / 0 beats
    """
    bundle = prepare_all_vqc_datasets(DATA_DIR)

    # 1. Training Partitions (0 clipping)
    assert bundle.fold1.train.clipping_stats["total_clipped_values"] == 0
    assert bundle.fold1.train.clipping_stats["affected_beats_count"] == 0

    assert bundle.fold2.train.clipping_stats["total_clipped_values"] == 0
    assert bundle.fold2.train.clipping_stats["affected_beats_count"] == 0

    assert bundle.final_train.clipping_stats["total_clipped_values"] == 0
    assert bundle.final_train.clipping_stats["affected_beats_count"] == 0

    # 2. Fold 1 Validation Partition (Record 119 vs Scaler 106)
    f1_stats = bundle.fold1.val.clipping_stats
    assert f1_stats["total_clipped_values"] == 120
    assert f1_stats["clipping_rate_values_pct"] == 20.0
    assert f1_stats["affected_beats_count"] == 54
    assert f1_stats["affected_beats_pct"] == 54.0

    # Specific feature clipping in Fold 1 Val:
    assert f1_stats["by_feature"]["pre_rr"]["total_clipped"] == 4
    assert f1_stats["by_feature"]["post_rr"]["total_clipped"] == 0
    assert f1_stats["by_feature"]["qrs_rms"]["total_clipped"] == 15
    assert f1_stats["by_feature"]["qrs_duration"]["total_clipped"] == 50
    assert f1_stats["by_feature"]["p2p_amplitude"]["total_clipped"] == 50
    assert f1_stats["by_feature"]["spectral_ratio"]["total_clipped"] == 1

    # 3. Fold 2 Validation Partition (Record 106 vs Scaler 119)
    f2_stats = bundle.fold2.val.clipping_stats
    assert f2_stats["total_clipped_values"] == 154
    assert f2_stats["clipping_rate_values_pct"] == 25.6667
    assert f2_stats["affected_beats_count"] == 89
    assert f2_stats["affected_beats_pct"] == 89.0

    # Specific feature clipping in Fold 2 Val:
    assert f2_stats["by_feature"]["pre_rr"]["total_clipped"] == 21
    assert f2_stats["by_feature"]["post_rr"]["total_clipped"] == 14
    assert f2_stats["by_feature"]["qrs_rms"]["total_clipped"] == 36
    assert f2_stats["by_feature"]["qrs_duration"]["total_clipped"] == 5
    assert f2_stats["by_feature"]["p2p_amplitude"]["total_clipped"] == 41
    assert f2_stats["by_feature"]["spectral_ratio"]["total_clipped"] == 37

    # 4. Final Benchmark Quarantined Test Partition
    test_stats = bundle.final_test.clipping_stats
    assert test_stats["total_clipped_values"] == 14
    assert test_stats["clipping_rate_values_pct"] == 2.3333
    assert test_stats["affected_beats_count"] == 13
    assert test_stats["affected_beats_pct"] == 13.0
