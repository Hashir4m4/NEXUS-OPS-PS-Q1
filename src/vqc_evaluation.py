"""
VQC Performance Evaluation & Model Selection Module
===================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Phase 5: QML)

Responsibilities:
-----------------
1. Parse and analyze multi-seed, multi-fold LORO training runs.
2. Compute calibration error (Expected Calibration Error - ECE) and Brier scores.
3. Generate confusion matrices, ROC metrics, and probability distributions.
4. Execute reproducible, multi-criteria model selection based STRICTLY on
   cross-validation performance (Records 106 and 119 only).
5. Freeze selected model parameters and preprocessing artifacts before held-out evaluation.
6. Evaluate the frozen model on the quarantined held-out cohort (Records 200 and 208).
7. Benchmark VQC against classical baselines (Logistic Regression, SVM-RBF, Random Forest)
   with explicit disclosure of classical test-set selection bias.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

from src.feature_extraction import FEATURE_NAMES
from src.vqc_circuit import (
    NUM_QUBITS,
    NUM_VARIATIONAL_PARAMS,
    create_parameter_vectors,
    build_vqc_circuit,
    build_ensemble_z_observable,
    format_pub_parameters,
    expectation_to_probability,
)
from src.vqc_training import (
    VQCEvaluationMetrics,
    compute_vqc_metrics,
    predict_vqc,
)
from src.vqc_preprocessing import prepare_loro_fold, prepare_final_benchmark_datasets

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def compute_expected_calibration_error(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Computes Expected Calibration Error (ECE) across uniform probability bins.

    Parameters
    ----------
    y_true : np.ndarray
        Binary labels in {0, 1}.
    probabilities : np.ndarray
        Predicted probabilities in [0.0, 1.0].
    n_bins : int
        Number of equal-width bins (default: 10).

    Returns
    -------
    float
        ECE score in [0.0, 1.0].
    """
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total = len(y)

    for i in range(n_bins):
        bin_mask = (p >= bin_edges[i]) & (p < bin_edges[i + 1] if i < n_bins - 1 else p <= bin_edges[i + 1])
        bin_count = np.sum(bin_mask)
        if bin_count > 0:
            bin_acc = np.mean(y[bin_mask])
            bin_conf = np.mean(p[bin_mask])
            ece += (bin_count / total) * abs(bin_acc - bin_conf)

    return float(ece)


def select_best_vqc_model(
    runs_data: Dict[str, Any],
    selection_criterion: str = "balanced_validation",
) -> Dict[str, Any]:
    """
    Selects the optimal VQC model checkpoint using LORO cross-validation evidence only.

    Selection Criteria:
    -------------------
    'balanced_validation' (Default, scientifically defensible):
        Balances low validation MSE, high validation F1, and balanced sensitivity/specificity.
        Composite Score = (1 - Val_MSE) * 0.4 + Val_F1 * 0.4 + (1 - |Sens - Spec|) * 0.2

    Parameters
    ----------
    runs_data : Dict[str, Any]
        Dictionary loaded from results/vqc_training_runs.json.
    selection_criterion : str
        Selection rule identifier.

    Returns
    -------
    Dict[str, Any]
        Structured record containing selected run details, optimal theta, and justification.
    """
    candidates = []

    for fold_key, fold_runs in runs_data["folds"].items():
        fold_id = 1 if fold_key == "fold_1" else 2
        for seed_key, run in fold_runs.items():
            val_m = run["final_val_metrics"]
            train_m = run["final_train_metrics"]

            val_mse = val_m["mse_loss"]
            val_f1 = val_m["f1_score"]
            sens = val_m["sensitivity"]
            spec = val_m["specificity"]

            # Balance score: reward low MSE, high F1, low disparity between sens & spec
            disparity = abs(sens - spec)
            score = (1.0 - val_mse) * 0.4 + val_f1 * 0.4 + (1.0 - disparity) * 0.2

            candidates.append({
                "run_id": f"{fold_key}_{seed_key}",
                "fold_id": fold_id,
                "seed": run["seed"],
                "train_record": run["train_record"],
                "val_record": run["val_record"],
                "composite_score": float(score),
                "val_mse": float(val_mse),
                "val_f1": float(val_f1),
                "val_accuracy": float(val_m["accuracy"]),
                "val_sensitivity": float(sens),
                "val_specificity": float(spec),
                "val_precision": float(val_m["precision"]),
                "val_roc_auc": float(val_m["roc_auc"]),
                "train_mse": float(train_m["mse_loss"]),
                "train_f1": float(train_m["f1_score"]),
                "optimal_theta": run["optimal_theta"],
            })

    # Sort descending by composite score, then ascending by val_mse
    candidates.sort(key=lambda c: (-c["composite_score"], c["val_mse"]))

    winner = candidates[0]
    return {
        "selection_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selection_rule": selection_criterion,
        "rule_description": "Composite score = 0.4*(1-Val_MSE) + 0.4*Val_F1 + 0.2*(1-|Sens-Spec|)",
        "selected_candidate": winner,
        "all_ranked_candidates": candidates,
    }


def evaluate_held_out_cohort(
    selected_model: Dict[str, Any],
    features_train_path: Optional[Path] = None,
    features_test_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Evaluates the frozen selected VQC model on the held-out test cohort (Records 200 & 208).

    Mandatory Scientific Protocol:
    ------------------------------
    1. Scaler is fit exclusively on the complete training cohort (Records 106 & 119, N=200).
    2. The held-out test cohort (Records 200 & 208, N=100) is transformed using the training scaler.
    3. Optimal parameters theta* are loaded directly from the frozen selected model.
    4. Evaluates both overall performance and patient-stratified performance.

    Returns
    -------
    Dict[str, Any]
        Complete held-out test evaluation report.
    """
    train_csv = features_train_path or (DATA_DIR / "features_train.csv")
    test_csv = features_test_path or (DATA_DIR / "features_test.csv")

    if not train_csv.exists() or not test_csv.exists():
        raise FileNotFoundError("Training or test dataset not found.")

    df_train = pd.read_csv(train_csv)
    df_test = pd.read_csv(test_csv)

    # Prepare final benchmark datasets using approved leak-free pipeline
    final_train, final_test, final_scaler = prepare_final_benchmark_datasets(df_train, df_test)
    X_test, y_test = final_test.X, final_test.y

    # Circuit setup
    p_enc, p_var = create_parameter_vectors()
    circuit = build_vqc_circuit(p_enc, p_var)
    observable = build_ensemble_z_observable()

    cand = selected_model["selected_candidate"]
    theta_opt = np.array(cand["optimal_theta"], dtype=float)

    # Forward pass on held-out test set
    exp_test, prob_test, preds_test = predict_vqc(circuit, observable, X_test, theta_opt)

    # Overall metrics
    overall_metrics = compute_vqc_metrics(y_test, prob_test)
    ece_score = compute_expected_calibration_error(y_test, prob_test)

    # Patient-stratified metrics (Records 200 and 208)
    patient_results = {}
    for rec_id in [200, 208]:
        rec_mask = (df_test["record_id"] == rec_id).values
        rec_y = y_test[rec_mask]
        rec_prob = prob_test[rec_mask]
        rec_m = compute_vqc_metrics(rec_y, rec_prob)
        patient_results[str(rec_id)] = rec_m.to_dict()

    return {
        "metadata": {
            "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "held_out_records": [200, 208],
            "total_test_samples": len(y_test),
            "selected_model_run_id": cand["run_id"],
            "selected_model_source_fold": cand["fold_id"],
            "selected_model_seed": cand["seed"],
        },
        "overall_test_metrics": overall_metrics.to_dict(),
        "expected_calibration_error": ece_score,
        "clipping_statistics": final_test.clipping_stats,
        "patient_stratified_results": patient_results,
        "sample_predictions": [
            {
                "sample_idx": idx,
                "record_id": int(df_test.iloc[idx]["record_id"]),
                "true_label": int(y_test[idx]),
                "predicted_label": int(preds_test[idx]),
                "probability_veb": float(prob_test[idx]),
                "expectation": float(exp_test[idx]),
            }
            for idx in range(len(y_test))
        ],
    }
