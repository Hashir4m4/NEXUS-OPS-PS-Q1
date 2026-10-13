"""
Unit Tests for VQC Evaluation & Model Selection Module
======================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier
"""

import json
import sys
from pathlib import Path
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.vqc_evaluation import (
    compute_expected_calibration_error,
    select_best_vqc_model,
    evaluate_held_out_cohort,
)

RESULTS_DIR = PROJECT_ROOT / "results"


def test_compute_expected_calibration_error_bounds_and_values():
    """Verifies that ECE calculation is strictly bounded in [0, 1] and accurate."""
    # Perfectly calibrated
    y_true = np.array([0, 0, 1, 1])
    probs_perfect = np.array([0.0, 0.0, 1.0, 1.0])
    ece_perf = compute_expected_calibration_error(y_true, probs_perfect)
    assert 0.0 <= ece_perf <= 0.05

    # Completely uncalibrated
    probs_inverted = np.array([1.0, 1.0, 0.0, 0.0])
    ece_inv = compute_expected_calibration_error(y_true, probs_inverted)
    assert ece_inv > 0.5


def test_select_best_vqc_model_ranking_and_contract():
    """Verifies that select_best_vqc_model accurately evaluates composite scores and ranks candidates."""
    mock_runs = {
        "folds": {
            "fold_1": {
                "seed_42": {
                    "seed": 42,
                    "train_record": 106,
                    "val_record": 119,
                    "final_train_metrics": {"mse_loss": 0.08, "f1_score": 1.0},
                    "final_val_metrics": {
                        "mse_loss": 0.12,
                        "f1_score": 0.95,
                        "accuracy": 0.95,
                        "sensitivity": 1.0,
                        "specificity": 0.9,
                        "precision": 0.91,
                        "roc_auc": 0.99,
                    },
                    "optimal_theta": [0.1] * 12,
                },
                "seed_101": {
                    "seed": 101,
                    "train_record": 106,
                    "val_record": 119,
                    "final_train_metrics": {"mse_loss": 0.08, "f1_score": 1.0},
                    "final_val_metrics": {
                        "mse_loss": 0.05,
                        "f1_score": 1.0,
                        "accuracy": 1.0,
                        "sensitivity": 1.0,
                        "specificity": 1.0,
                        "precision": 1.0,
                        "roc_auc": 1.0,
                    },
                    "optimal_theta": [0.2] * 12,
                },
            }
        }
    }

    selection = select_best_vqc_model(mock_runs)
    assert selection["selected_candidate"]["run_id"] == "fold_1_seed_101"
    assert selection["selected_candidate"]["composite_score"] > selection["all_ranked_candidates"][1]["composite_score"]
    assert len(selection["selected_candidate"]["optimal_theta"]) == 12


def test_vqc_model_selection_and_heldout_artifacts_exist_and_valid():
    """Verifies schema and validity of results/vqc_model_selection.json and vqc_heldout_evaluation.json."""
    sel_path = RESULTS_DIR / "vqc_model_selection.json"
    heldout_path = RESULTS_DIR / "vqc_heldout_evaluation.json"

    assert sel_path.exists(), f"Missing {sel_path}"
    assert heldout_path.exists(), f"Missing {heldout_path}"

    with open(sel_path, "r", encoding="utf-8") as f:
        sel = json.load(f)
    assert "selected_candidate" in sel
    assert "optimal_theta" in sel["selected_candidate"]
    assert len(sel["selected_candidate"]["optimal_theta"]) == 12

    with open(heldout_path, "r", encoding="utf-8") as f:
        hov = json.load(f)
    assert hov["metadata"]["total_test_samples"] == 100
    assert hov["overall_test_metrics"]["sensitivity"] == 1.0
    assert hov["overall_test_metrics"]["accuracy"] >= 0.70
    assert 0.0 <= hov["expected_calibration_error"] <= 1.0
    assert "200" in hov["patient_stratified_results"]
    assert "208" in hov["patient_stratified_results"]
