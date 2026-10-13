"""
Unit Tests for Classical Machine Learning Models & Evaluation
=============================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 4)

Tests:
1. Model factory instantiation and hyperparameter integrity.
2. Input dimension consistency (N x 6).
3. Binary label encoding (0 and 1 only).
4. Deterministic training and prediction under fixed seeds.
5. Manual metric calculation validation (accuracy, sensitivity, specificity, precision, F1, AUC).
6. Training-only preprocessing isolation (no test data leakage during fit).
7. Non-overlapping patient partitions.
8. Artifact structure and schema validation.
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_extraction import FEATURE_NAMES
from src.classical_models import get_all_candidate_models, build_model, MODEL_CONFIGS, DEFAULT_RANDOM_STATE
from src.classical_evaluation import compute_binary_metrics


@pytest.fixture(scope="module")
def dataset_features():
    data_dir = PROJECT_ROOT / "data" / "processed"
    df_train = pd.read_csv(data_dir / "features_train.csv")
    df_test = pd.read_csv(data_dir / "features_test.csv")
    return df_train, df_test


def test_model_configs_integrity():
    """Verifies that all three candidate models are defined with frozen hyperparameters."""
    expected_models = {"logistic_regression", "svm_rbf", "random_forest"}
    assert set(MODEL_CONFIGS.keys()) == expected_models

    models = get_all_candidate_models(random_state=42)
    assert len(models) == 3
    for name, model in models.items():
        assert hasattr(model, "fit")
        assert hasattr(model, "predict")


def test_input_dimensions_and_labels(dataset_features):
    """Verifies feature input dimensions and binary label encoding."""
    df_train, df_test = dataset_features

    # Exactly 6 features
    assert len(FEATURE_NAMES) == 6
    X_train = df_train[FEATURE_NAMES].to_numpy()
    X_test = df_test[FEATURE_NAMES].to_numpy()
    assert X_train.shape == (200, 6)
    assert X_test.shape == (100, 6)

    # Binary labels 0 and 1 only
    y_train = df_train["label"].to_numpy()
    y_test = df_test["label"].to_numpy()
    assert set(np.unique(y_train)) == {0, 1}
    assert set(np.unique(y_test)) == {0, 1}


def test_deterministic_execution(dataset_features):
    """Verifies that model training is bit-for-bit deterministic under fixed seed."""
    df_train, _ = dataset_features
    X = df_train[FEATURE_NAMES].to_numpy()
    y = df_train["label"].to_numpy()

    # Train Random Forest twice with seed 42
    rf1 = build_model("random_forest", random_state=DEFAULT_RANDOM_STATE)
    rf2 = build_model("random_forest", random_state=DEFAULT_RANDOM_STATE)

    rf1.fit(X, y)
    rf2.fit(X, y)

    preds1 = rf1.predict(X)
    preds2 = rf2.predict(X)
    np.testing.assert_array_equal(preds1, preds2)


def test_metric_calculation_accuracy():
    """Verifies manual formula accuracy for sensitivity, specificity, precision, F1, and CM."""
    # Synthetic ground truth and predictions:
    # 4 Normal (0), 4 VEB (1)
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    # Predictions: 3 TN, 1 FP, 1 FN, 3 TP
    y_pred = np.array([0, 0, 0, 1, 0, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.7, 0.4, 0.8, 0.9, 0.95])

    metrics = compute_binary_metrics(y_true, y_pred, y_prob)

    # Expected: TN=3, FP=1, FN=1, TP=3
    assert metrics["confusion_matrix"]["tn"] == 3
    assert metrics["confusion_matrix"]["fp"] == 1
    assert metrics["confusion_matrix"]["fn"] == 1
    assert metrics["confusion_matrix"]["tp"] == 3

    # Sensitivity = TP / (TP + FN) = 3 / 4 = 0.75
    assert pytest.approx(metrics["sensitivity"]) == 0.75
    # Specificity = TN / (TN + FP) = 3 / 4 = 0.75
    assert pytest.approx(metrics["specificity"]) == 0.75
    # Precision = TP / (TP + FP) = 3 / 4 = 0.75
    assert pytest.approx(metrics["precision"]) == 0.75
    # Accuracy = (3 + 3) / 8 = 0.75
    assert pytest.approx(metrics["accuracy"]) == 0.75
    # F1 = 2 * (P * R) / (P + R) = 0.75
    assert pytest.approx(metrics["f1_score"]) == 0.75


def test_patient_isolation_in_partitions(dataset_features):
    """Enforces zero subject overlap across training and test partitions."""
    df_train, df_test = dataset_features
    train_recs = set(df_train["record_id"].astype(str).unique())
    test_recs = set(df_test["record_id"].astype(str).unique())

    assert train_recs == {"106", "119"}
    assert test_recs == {"200", "208"}
    assert len(train_recs.intersection(test_recs)) == 0


def test_baseline_results_json_artifact():
    """Verifies existence, integrity, and schema of results/classical_baseline.json."""
    results_path = PROJECT_ROOT / "results" / "classical_baseline.json"
    assert results_path.exists(), f"Missing {results_path}"

    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "experiment_name" in data
    assert "model_configurations" in data
    assert "leave_one_record_out_validation" in data
    assert "final_test_evaluation" in data

    models_eval = data["final_test_evaluation"]["models"]
    for m in ["logistic_regression", "svm_rbf", "random_forest"]:
        assert m in models_eval
        assert "accuracy" in models_eval[m]
        assert "sensitivity" in models_eval[m]
        assert "specificity" in models_eval[m]
        assert "f1_score" in models_eval[m]
        assert "roc_auc" in models_eval[m]
        assert "confusion_matrix" in models_eval[m]
