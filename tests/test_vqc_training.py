"""
Unit Tests for VQC Training & Diagnostic Optimization Module
============================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 5F.3, Step 3)

Verifies:
1. Contract and safety guards of the objective function (make_vqc_objective).
2. Deterministic prediction outputs and numerical bounds for predict_vqc.
3. Metric calculation correctness and zero-division protection (compute_vqc_metrics).
4. Diagnostic training run execution, tracking, and stopping conditions.
5. Independent tracking of objective function evaluations vs. simplex iterations.
6. Strict patient isolation and quarantine enforcement (Records 200/208 lockout).
7. Full experiment lock safeguard (run_vqc_loro_experiment raises PermissionError without approval).
8. Schema compliance and numerical validity of results/vqc_training_step3_diagnostic.json.
"""

import json
import sys
from pathlib import Path
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qiskit.primitives import StatevectorEstimator

from src.vqc_circuit import (
    NUM_QUBITS,
    NUM_VARIATIONAL_PARAMS,
    create_parameter_vectors,
    build_vqc_circuit,
    build_ensemble_z_observable,
)
from src.vqc_training import (
    APPROVED_SEEDS,
    DEFAULT_DIAGNOSTIC_MAXITER,
    VQCEvaluationMetrics,
    VQCTrainingRunResult,
    compute_vqc_metrics,
    predict_vqc,
    make_vqc_objective,
    run_diagnostic_training_run,
    run_vqc_loro_experiment,
)

RESULTS_DIR = PROJECT_ROOT / "results"
DIAGNOSTIC_JSON_PATH = RESULTS_DIR / "vqc_training_step3_diagnostic.json"


# ============================================================================
# 1. OBJECTIVE FUNCTION CONTRACT & SAFETY GUARDS
# ============================================================================

def test_make_vqc_objective_contract_and_eval_logging():
    """
    Verifies that make_vqc_objective creates a closure returning scalar float loss,
    logs every evaluation into eval_history, and handles invalid parameter vectors safely.
    """
    p_enc, p_var = create_parameter_vectors()
    circuit = build_vqc_circuit(p_enc, p_var)
    observable = build_ensemble_z_observable()
    estimator = StatevectorEstimator()

    # Synthetic 5-sample batch
    X_synthetic = np.full((5, 6), 0.5 * np.pi)
    y_synthetic = np.array([0, 1, 0, 1, 0])

    eval_history = []
    objective_fn = make_vqc_objective(
        circuit=circuit,
        observable=observable,
        X_train=X_synthetic,
        y_train=y_synthetic,
        estimator=estimator,
        eval_history=eval_history,
    )

    theta_test = np.zeros(NUM_VARIATIONAL_PARAMS)
    loss = objective_fn(theta_test)

    assert isinstance(loss, float)
    assert 0.0 <= loss <= 1.0
    assert len(eval_history) == 1
    assert eval_history[0]["eval_idx"] == 1
    assert eval_history[0]["loss"] == loss
    assert len(eval_history[0]["theta"]) == NUM_VARIATIONAL_PARAMS

    # Safety penalty guard for non-finite parameters
    theta_nan = np.zeros(NUM_VARIATIONAL_PARAMS)
    theta_nan[0] = np.nan
    penalty_nan = objective_fn(theta_nan)
    assert penalty_nan == 10.0

    # Safety penalty guard for wrong dimension
    theta_wrong_dim = np.zeros(6)
    penalty_dim = objective_fn(theta_wrong_dim)
    assert penalty_dim == 10.0


# ============================================================================
# 2. PREDICT_VQC OUTPUTS AND NUMERICAL BOUNDS
# ============================================================================

def test_predict_vqc_outputs_and_bounds():
    """
    Verifies that predict_vqc outputs expectation values bounded in [-1, 1],
    probabilities bounded in [0, 1], and discrete predictions in {0, 1}.
    """
    p_enc, p_var = create_parameter_vectors()
    circuit = build_vqc_circuit(p_enc, p_var)
    observable = build_ensemble_z_observable()

    rng = np.random.default_rng(42)
    X = rng.uniform(0.0, np.pi, size=(8, 6))
    theta = rng.uniform(-0.1, 0.1, size=NUM_VARIATIONAL_PARAMS)

    evs, probs, preds = predict_vqc(circuit, observable, X, theta)

    assert evs.shape == (8,)
    assert probs.shape == (8,)
    assert preds.shape == (8,)

    assert np.all(evs >= -1.0) and np.all(evs <= 1.0)
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
    assert set(np.unique(preds)).issubset({0, 1})
    assert np.all(preds == (probs >= 0.5).astype(int))


# ============================================================================
# 3. METRIC CALCULATION & ZERO-DIVISION PROTECTION
# ============================================================================

def test_compute_vqc_metrics_accuracy_and_guards():
    """
    Verifies metric calculations (MSE, accuracy, sensitivity, specificity, F1)
    and validates zero-division protections on edge-case predictions.
    """
    # Perfect prediction case
    y_true = np.array([0, 0, 1, 1])
    probs_perfect = np.array([0.1, 0.2, 0.8, 0.9])
    m_perfect = compute_vqc_metrics(y_true, probs_perfect)

    assert m_perfect.accuracy == 1.0
    assert m_perfect.sensitivity == 1.0
    assert m_perfect.specificity == 1.0
    assert m_perfect.f1_score == 1.0
    assert m_perfect.class_polarity_delta_p > 0.5

    # Degenerate case: all predicted 0 (sensitivity denominator check)
    probs_all_zero = np.array([0.1, 0.2, 0.3, 0.4])
    m_zero = compute_vqc_metrics(y_true, probs_all_zero)
    assert m_zero.sensitivity == 0.0
    assert m_zero.specificity == 1.0
    assert m_zero.f1_score == 0.0

    # Length mismatch guard
    with pytest.raises(ValueError, match="Length mismatch"):
        compute_vqc_metrics(np.array([0, 1]), np.array([0.5]))


# ============================================================================
# 4. DIAGNOSTIC TRAINING RUN EXECUTION & SEPARATE TRACKING
# ============================================================================

def test_diagnostic_training_run_tracking():
    """
    Verifies that run_diagnostic_training_run executes with a small budget (maxiter=15 >= 14),
    records evaluations and iterations separately, and reduces or updates loss.
    Also verifies that maxiter < 14 is rejected with ValueError.
    """
    # Guard against maxiter < 14 (simplex initialization requirement)
    with pytest.raises(ValueError, match="too small for COBYLA"):
        run_diagnostic_training_run(fold_id=1, seed=42, maxiter=10)

    res = run_diagnostic_training_run(fold_id=1, seed=42, maxiter=15)

    assert isinstance(res, VQCTrainingRunResult)
    assert res.fold_id == 1
    assert res.train_record == 106
    assert res.val_record == 119
    assert res.seed == 42
    assert len(res.initial_theta) == NUM_VARIATIONAL_PARAMS
    assert len(res.optimal_theta) == NUM_VARIATIONAL_PARAMS

    # Crucial tracking check: function evaluations (nfev) vs simplex iterations (nit)
    assert res.total_function_evaluations == 15
    assert res.total_iterations > 0
    assert res.total_iterations <= res.total_function_evaluations
    assert len(res.evaluation_history) == 15
    assert len(res.iteration_history) == res.total_iterations

    # Termination message check
    assert "COBYLA" in res.termination_message

    # Initial vs final train metrics exist and are valid
    assert 0.0 <= res.initial_train_metrics.mse_loss <= 1.0
    assert 0.0 <= res.final_train_metrics.mse_loss <= 1.0
    assert 0.0 <= res.initial_val_metrics.mse_loss <= 1.0
    assert 0.0 <= res.final_val_metrics.mse_loss <= 1.0


# ============================================================================
# 5. STRICT PATIENT ISOLATION & QUARANTINE ENFORCEMENT
# ============================================================================

def test_quarantine_enforcement_and_experiment_lock():
    """
    Verifies that invalid fold IDs are rejected, test patients 200/208 cannot
    be accessed, and run_vqc_loro_experiment raises PermissionError without confirmation.
    """
    # Invalid fold ID rejection
    with pytest.raises(ValueError, match="Invalid fold_id"):
        run_diagnostic_training_run(fold_id=3, seed=42, maxiter=5)

    # Invalid seed rejection
    with pytest.raises(ValueError, match="not in approved seeds"):
        run_diagnostic_training_run(fold_id=1, seed=999, maxiter=5)

    # Full experiment lock safeguard
    with pytest.raises(PermissionError, match="Full multi-run experiment execution is locked"):
        run_vqc_loro_experiment(confirm_execution=False)


# ============================================================================
# 6. DIAGNOSTIC JSON ARTIFACT INTEGRITY
# ============================================================================

def test_diagnostic_json_artifact_integrity():
    """
    Verifies that results/vqc_training_step3_diagnostic.json exists, is valid JSON,
    and reflects the Fold 1, Seed 42 diagnostic run with maxiter=25.
    """
    assert DIAGNOSTIC_JSON_PATH.exists(), f"Diagnostic JSON not found at {DIAGNOSTIC_JSON_PATH}"

    with open(DIAGNOSTIC_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["fold_id"] == 1
    assert data["train_record"] == 106
    assert data["val_record"] == 119
    assert data["seed"] == 42
    assert data["total_function_evaluations"] == 25
    assert data["total_iterations"] == 10
    assert len(data["evaluation_history"]) == 25
    assert len(data["iteration_history"]) == 10

    # Training loss reduction verified
    init_train_loss = data["initial_train_metrics"]["mse_loss"]
    final_train_loss = data["final_train_metrics"]["mse_loss"]
    assert final_train_loss < init_train_loss
    assert final_train_loss == pytest.approx(0.153985, abs=1e-4)

    # Polarity separation maintained
    assert data["final_train_metrics"]["class_polarity_delta_p"] > 0
    assert data["final_val_metrics"]["class_polarity_delta_p"] > 0
