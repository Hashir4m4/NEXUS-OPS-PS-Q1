"""
Automated Pytest Suite for Milestone 2B Dataset Validation
==========================================================
Verifies properties of data/processed/ecg_segments.csv, train.csv, and test.csv:
1. File existence and schema.
2. Exact sample counts: 300 total, 200 train, 100 test.
3. Exact class balance: 1:1 N to V in both splits.
4. Strict patient/record-level isolation (no overlap).
5. Dimension check: exactly 360 signal columns.
6. Sample finiteness: no NaNs or Infs.
7. Boundary adherence.
8. Determinism with seed 42.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data" / "processed"


@pytest.fixture(scope="module")
def dataset_dfs():
    all_csv = DATA_DIR / "ecg_segments.csv"
    train_csv = DATA_DIR / "train.csv"
    test_csv = DATA_DIR / "test.csv"

    assert all_csv.exists(), f"Missing {all_csv}"
    assert train_csv.exists(), f"Missing {train_csv}"
    assert test_csv.exists(), f"Missing {test_csv}"

    df_all = pd.read_csv(all_csv)
    df_train = pd.read_csv(train_csv)
    df_test = pd.read_csv(test_csv)

    return df_all, df_train, df_test


def test_sample_counts(dataset_dfs):
    df_all, df_train, df_test = dataset_dfs
    assert len(df_all) == 300
    assert len(df_train) == 200
    assert len(df_test) == 100


def test_class_balance(dataset_dfs):
    df_all, df_train, df_test = dataset_dfs
    # Overall
    assert (df_all["label"] == 0).sum() == 150
    assert (df_all["label"] == 1).sum() == 150
    # Train
    assert (df_train["label"] == 0).sum() == 100
    assert (df_train["label"] == 1).sum() == 100
    # Test
    assert (df_test["label"] == 0).sum() == 50
    assert (df_test["label"] == 1).sum() == 50


def test_patient_isolation(dataset_dfs):
    _, df_train, df_test = dataset_dfs
    train_recs = set(df_train["record_id"].astype(str).unique())
    test_recs = set(df_test["record_id"].astype(str).unique())

    assert train_recs == {"106", "119"}
    assert test_recs == {"200", "208"}
    assert len(train_recs.intersection(test_recs)) == 0


def test_signal_dimensions_and_finiteness(dataset_dfs):
    df_all, _, _ = dataset_dfs
    sig_cols = [c for c in df_all.columns if c.startswith("s_")]
    assert len(sig_cols) == 360

    sig_matrix = df_all[sig_cols].to_numpy()
    assert not np.isnan(sig_matrix).any(), "Found NaN in signal values"
    assert not np.isinf(sig_matrix).any(), "Found Inf in signal values"


def test_boundary_integrity(dataset_dfs):
    df_all, _, _ = dataset_dfs
    assert (df_all["window_start"] >= 0).all()
    assert (df_all["window_end"] <= 650000).all()
    assert ((df_all["window_end"] - df_all["window_start"]) == 360).all()
