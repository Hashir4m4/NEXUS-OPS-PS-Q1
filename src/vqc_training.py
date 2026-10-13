"""
VQC Training & Diagnostic Optimization Module
=============================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 5F.3, Step 3)

Architecture & Optimization Standards:
--------------------------------------
- 6-Qubit parameterized quantum classifier (frozen decision D1-D10)
- Objective Function: Mean Squared Error (Brier Loss) on probabilities:
    L(theta) = (1/N) * sum((p_i(theta) - y_i)^2), where p_i = (E_i + 1) / 2
- Optimizer: SciPy COBYLA (Constrained Optimization BY Linear Approximation)
- Independent tracking of:
    1. Objective function evaluations (nfev / forward passes)
    2. Simplex iterations (nit / major trust region updates)
- Patient-Level Isolation: Leave-One-Record-Out (LORO) Protocol A:
    * Fold 1: Train on Record 106, Validate on Record 119
    * Fold 2: Train on Record 119, Validate on Record 106
- Held-out Quarantine: Records 200 & 208 strictly quarantined from all training routines.
- Multi-run Safeguard: Diagnostic single-run enabled; full 10-run experiment gated behind
  explicit authorization parameter.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import scipy.optimize as opt
from sklearn.metrics import roc_auc_score
from qiskit.circuit import QuantumCircuit
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp

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
from src.vqc_preprocessing import prepare_loro_fold, LOROFoldData

# Architectural & Optimization Constants
APPROVED_SEEDS: List[int] = [42, 101, 202, 303, 404]
MIN_COBYLA_EVALUATIONS: int = NUM_VARIATIONAL_PARAMS + 2  # 14 evaluations for 12 params (simplex base + vertices + 1)
DEFAULT_DIAGNOSTIC_MAXITER: int = 25
DEFAULT_RHOBEG: float = 0.1
DEFAULT_TOL: float = 1e-4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "features_train.csv"


@dataclass
class VQCEvaluationMetrics:
    """Evaluation metrics for a VQC forward pass on a patient partition."""
    mse_loss: float
    accuracy: float
    sensitivity: float
    specificity: float
    f1_score: float
    mean_p_normal: float
    mean_p_veb: float
    class_polarity_delta_p: float
    predicted_normal_count: int
    predicted_veb_count: int
    precision: float = 0.0
    roc_auc: float = 0.5
    confusion_matrix: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VQCTrainingRunResult:
    """Container holding complete audit metadata and results for a training run."""
    fold_id: int
    train_record: int
    val_record: int
    seed: int
    initial_theta: List[float]
    optimal_theta: List[float]
    initial_train_metrics: VQCEvaluationMetrics
    final_train_metrics: VQCEvaluationMetrics
    initial_val_metrics: VQCEvaluationMetrics
    final_val_metrics: VQCEvaluationMetrics
    total_function_evaluations: int
    total_iterations: int
    convergence_status: bool
    termination_message: str
    elapsed_seconds: float
    evaluation_history: List[Dict[str, Any]]
    iteration_history: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


def compute_vqc_metrics(y_true: np.ndarray, probabilities: np.ndarray) -> VQCEvaluationMetrics:
    """
    Computes classification and calibration metrics from ground truth labels and probabilities.

    Parameters
    ----------
    y_true : np.ndarray
        Binary labels in {0, 1}, shape (N,).
    probabilities : np.ndarray
        Model output probabilities in [0.0, 1.0], shape (N,).

    Returns
    -------
    VQCEvaluationMetrics
    """
    y_true = np.asarray(y_true, dtype=int)
    probs = np.asarray(probabilities, dtype=float)

    if len(y_true) != len(probs):
        raise ValueError(f"Length mismatch: len(y_true)={len(y_true)}, len(probs)={len(probs)}")

    # Loss
    mse = float(np.mean((probs - y_true) ** 2))

    # Binary predictions using 0.5 threshold
    preds = (probs >= 0.5).astype(int)

    tp = int(np.sum((preds == 1) & (y_true == 1)))
    tn = int(np.sum((preds == 0) & (y_true == 0)))
    fp = int(np.sum((preds == 1) & (y_true == 0)))
    fn = int(np.sum((preds == 0) & (y_true == 1)))

    total = len(y_true)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * (precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0.0

    # ROC-AUC calculation with single-class edge case protection
    try:
        if len(np.unique(y_true)) > 1:
            roc_auc = float(roc_auc_score(y_true, probs))
        else:
            roc_auc = 0.5
    except Exception:
        roc_auc = 0.5

    # Confusion matrix structure
    cm = {
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "matrix": [[tn, fp], [fn, tp]],
    }

    # Class-conditional probability spreads
    norm_mask = (y_true == 0)
    veb_mask = (y_true == 1)

    mean_p_norm = float(np.mean(probs[norm_mask])) if np.any(norm_mask) else 0.0
    mean_p_veb = float(np.mean(probs[veb_mask])) if np.any(veb_mask) else 0.0
    delta_p = mean_p_veb - mean_p_norm

    pred_norm_count = int(np.sum(preds == 0))
    pred_veb_count = int(np.sum(preds == 1))

    return VQCEvaluationMetrics(
        mse_loss=mse,
        accuracy=accuracy,
        sensitivity=sensitivity,
        specificity=specificity,
        f1_score=f1,
        mean_p_normal=mean_p_norm,
        mean_p_veb=mean_p_veb,
        class_polarity_delta_p=delta_p,
        predicted_normal_count=pred_norm_count,
        predicted_veb_count=pred_veb_count,
        precision=precision,
        roc_auc=roc_auc,
        confusion_matrix=cm,
    )


def predict_vqc(
    circuit: QuantumCircuit,
    observable: SparsePauliOp,
    X: np.ndarray,
    theta: np.ndarray,
    estimator: Optional[StatevectorEstimator] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Performs a deterministic forward pass over samples X using variational parameters theta.

    Parameters
    ----------
    circuit : QuantumCircuit
        Assembled 6-qubit VQC circuit.
    observable : SparsePauliOp
        Ensemble average Pauli-Z observable.
    X : np.ndarray
        Scaled feature matrix in [0, pi], shape (N, 6).
    theta : np.ndarray
        Variational parameter vector, shape (12,).
    estimator : StatevectorEstimator, optional
        Estimator instance; if None, instantiates a new StatevectorEstimator.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray, np.ndarray]
        (expectations, probabilities, discrete_predictions)
    """
    if estimator is None:
        estimator = StatevectorEstimator()

    pub_params = format_pub_parameters(X, theta)
    pub = (circuit, [observable], pub_params)

    job = estimator.run([pub])
    result = job.result()
    expectations = np.asarray(result[0].data.evs, dtype=float)

    probabilities = expectation_to_probability(expectations)
    predictions = (probabilities >= 0.5).astype(int)

    return expectations, probabilities, predictions


def make_vqc_objective(
    circuit: QuantumCircuit,
    observable: SparsePauliOp,
    X_train: np.ndarray,
    y_train: np.ndarray,
    estimator: StatevectorEstimator,
    eval_history: Optional[List[Dict[str, Any]]] = None,
) -> Callable[[np.ndarray], float]:
    """
    Constructs an objective function closure for SciPy optimization.

    Parameters
    ----------
    circuit : QuantumCircuit
        Assembled 6-qubit VQC circuit.
    observable : SparsePauliOp
        Ensemble average Pauli-Z observable.
    X_train : np.ndarray
        Training feature matrix in [0, pi], shape (N, 6).
    y_train : np.ndarray
        Ground-truth labels, shape (N,).
    estimator : StatevectorEstimator
        Statevector estimator for noiseless simulation.
    eval_history : list, optional
        Mutable list to append evaluation records for audit logging.

    Returns
    -------
    Callable[[np.ndarray], float]
        Objective function mapping theta (12,) to MSE loss.
    """
    y_target = np.asarray(y_train, dtype=float)

    def objective(theta: np.ndarray) -> float:
        theta_arr = np.asarray(theta, dtype=float)

        # Numerical safety guard
        if not np.all(np.isfinite(theta_arr)) or len(theta_arr) != NUM_VARIATIONAL_PARAMS:
            return 10.0  # Penalty value for non-finite parameter proposals

        pub_params = format_pub_parameters(X_train, theta_arr)
        pub = (circuit, [observable], pub_params)

        job = estimator.run([pub])
        result = job.result()
        evs = result[0].data.evs

        probs = expectation_to_probability(evs)
        loss = float(np.mean((probs - y_target) ** 2))

        if eval_history is not None:
            eval_history.append({
                "eval_idx": len(eval_history) + 1,
                "loss": loss,
                "theta": theta_arr.tolist(),
                "timestamp": time.time(),
            })

        return loss

    return objective


def run_diagnostic_training_run(
    fold_id: int = 1,
    seed: int = 42,
    maxiter: int = DEFAULT_DIAGNOSTIC_MAXITER,
    rhobeg: float = DEFAULT_RHOBEG,
    tol: float = DEFAULT_TOL,
    data_path: Optional[Path] = None,
    estimator: Optional[StatevectorEstimator] = None,
) -> VQCTrainingRunResult:
    """
    Executes a single LORO fold, single seed diagnostic training run with a small optimizer budget.

    Parameters
    ----------
    fold_id : int
        LORO fold ID: 1 (Train 106, Val 119) or 2 (Train 119, Val 106).
    seed : int
        Random seed for initial parameter drawing from U[-0.1, 0.1].
    maxiter : int
        Maximum objective function evaluations for COBYLA.
    rhobeg : float
        Initial simplex change radius (default: 0.1).
    tol : float
        Final objective convergence tolerance (default: 1e-4).
    data_path : Path, optional
        Path to features_train.csv.
    estimator : StatevectorEstimator, optional
        StatevectorEstimator instance.

    Returns
    -------
    VQCTrainingRunResult
        Comprehensive structured result with training history and metrics.
    """
    if fold_id not in (1, 2):
        raise ValueError(f"Invalid fold_id {fold_id}. Must be 1 or 2.")
    if seed not in APPROVED_SEEDS:
        raise ValueError(f"Seed {seed} not in approved seeds: {APPROVED_SEEDS}")
    if maxiter < MIN_COBYLA_EVALUATIONS:
        raise ValueError(
            f"maxiter ({maxiter}) is too small for COBYLA on {NUM_VARIATIONAL_PARAMS} parameters. "
            f"The initial simplex requires at least {MIN_COBYLA_EVALUATIONS} evaluations."
        )

    csv_path = data_path or DEFAULT_DATA_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Training dataset not found at {csv_path}")

    df_train = pd.read_csv(csv_path)

    # Integrity safeguard: verify test patients are strictly quarantined
    if 200 in df_train["record_id"].values or 208 in df_train["record_id"].values:
        raise ValueError("Data leakage hazard: Test records 200/208 detected in training set!")

    # Prepare LORO fold with strict scaler isolation
    if fold_id == 1:
        train_rec, val_rec = 106, 119
    else:
        train_rec, val_rec = 119, 106

    fold_data: LOROFoldData = prepare_loro_fold(
        df_train,
        train_record=train_rec,
        val_record=val_rec,
        fold_id=fold_id,
    )

    X_train, y_train = fold_data.train.X, fold_data.train.y
    X_val, y_val = fold_data.val.X, fold_data.val.y

    # Circuit assembly
    p_enc, p_var = create_parameter_vectors()
    circuit = build_vqc_circuit(p_enc, p_var)
    observable = build_ensemble_z_observable()

    if estimator is None:
        estimator = StatevectorEstimator()

    # Parameter initialization: theta_0 in U[-0.1, 0.1]
    rng = np.random.default_rng(seed)
    theta_0 = rng.uniform(-0.1, 0.1, size=NUM_VARIATIONAL_PARAMS)

    # Initial pre-training evaluations
    _, train_probs_0, _ = predict_vqc(circuit, observable, X_train, theta_0, estimator)
    _, val_probs_0, _ = predict_vqc(circuit, observable, X_val, theta_0, estimator)

    init_train_metrics = compute_vqc_metrics(y_train, train_probs_0)
    init_val_metrics = compute_vqc_metrics(y_val, val_probs_0)

    # Audit tracking lists
    eval_history: List[Dict[str, Any]] = []
    iteration_history: List[Dict[str, Any]] = []

    def iteration_callback(xk: np.ndarray) -> None:
        iteration_history.append({
            "iter_idx": len(iteration_history) + 1,
            "theta": np.asarray(xk, dtype=float).tolist(),
            "timestamp": time.time(),
        })

    objective_fn = make_vqc_objective(
        circuit=circuit,
        observable=observable,
        X_train=X_train,
        y_train=y_train,
        estimator=estimator,
        eval_history=eval_history,
    )

    start_time = time.time()

    opt_result = opt.minimize(
        fun=objective_fn,
        x0=theta_0,
        method="COBYLA",
        callback=iteration_callback,
        options={
            "maxiter": maxiter,
            "rhobeg": rhobeg,
            "tol": tol,
        },
    )

    elapsed_time = time.time() - start_time
    theta_opt = np.asarray(opt_result.x, dtype=float)

    # Final post-training evaluations
    _, train_probs_final, _ = predict_vqc(circuit, observable, X_train, theta_opt, estimator)
    _, val_probs_final, _ = predict_vqc(circuit, observable, X_val, theta_opt, estimator)

    final_train_metrics = compute_vqc_metrics(y_train, train_probs_final)
    final_val_metrics = compute_vqc_metrics(y_val, val_probs_final)

    return VQCTrainingRunResult(
        fold_id=fold_id,
        train_record=train_rec,
        val_record=val_rec,
        seed=seed,
        initial_theta=theta_0.tolist(),
        optimal_theta=theta_opt.tolist(),
        initial_train_metrics=init_train_metrics,
        final_train_metrics=final_train_metrics,
        initial_val_metrics=init_val_metrics,
        final_val_metrics=final_val_metrics,
        total_function_evaluations=len(eval_history),
        total_iterations=len(iteration_history),
        convergence_status=bool(opt_result.success),
        termination_message=str(opt_result.message),
        elapsed_seconds=elapsed_time,
        evaluation_history=eval_history,
        iteration_history=iteration_history,
    )


def compute_fold_summary_stats(runs_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Computes summary statistics (mean, std, min, max) across seeds for a fold."""
    metrics_to_aggregate = [
        ("train_mse", lambda r: r["final_train_metrics"]["mse_loss"]),
        ("val_mse", lambda r: r["final_val_metrics"]["mse_loss"]),
        ("train_accuracy", lambda r: r["final_train_metrics"]["accuracy"]),
        ("val_accuracy", lambda r: r["final_val_metrics"]["accuracy"]),
        ("val_sensitivity", lambda r: r["final_val_metrics"]["sensitivity"]),
        ("val_specificity", lambda r: r["final_val_metrics"]["specificity"]),
        ("val_precision", lambda r: r["final_val_metrics"]["precision"]),
        ("val_f1_score", lambda r: r["final_val_metrics"]["f1_score"]),
        ("val_roc_auc", lambda r: r["final_val_metrics"]["roc_auc"]),
        ("val_polarity_delta_p", lambda r: r["final_val_metrics"]["class_polarity_delta_p"]),
        ("evaluations", lambda r: r["total_function_evaluations"]),
        ("iterations", lambda r: r["total_iterations"]),
        ("runtime_sec", lambda r: r["elapsed_seconds"]),
    ]

    summary: Dict[str, Any] = {"num_runs": len(runs_dict)}
    for name, extractor in metrics_to_aggregate:
        values = [extractor(r) for r in runs_dict.values()]
        summary[name] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }
    return summary


def run_vqc_loro_experiment(
    confirm_execution: bool = False,
    seeds: Optional[List[int]] = None,
    maxiter: int = 50,
    output_path: Optional[Path] = None,
    summary_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Safeguarded entrypoint for running the full multi-fold, multi-seed LORO training experiment.

    Requires explicit confirmation to prevent unauthorized batch execution.

    Parameters
    ----------
    confirm_execution : bool
        Must be explicitly set to True by the caller.
    seeds : list of int, optional
        Random seeds to evaluate (default: APPROVED_SEEDS = [42, 101, 202, 303, 404]).
    maxiter : int
        Maximum function evaluations per run (default: 50).
    output_path : Path, optional
        Destination path for full runs JSON (default: results/vqc_training_runs.json).
    summary_path : Path, optional
        Destination path for summary JSON (default: results/vqc_loro_summary.json).

    Returns
    -------
    Dict[str, Any]
        Dictionary of all fold and seed experiment results along with statistical summary.
    """
    if not confirm_execution:
        raise PermissionError(
            "Full multi-run experiment execution is locked. "
            "Explicit authorization from the project owner is required. "
            "Use run_diagnostic_training_run() for single-fold diagnostic validation."
        )

    eval_seeds = seeds or APPROVED_SEEDS
    runs_output: Dict[str, Any] = {
        "metadata": {
            "experiment_name": "Phase5_VQC_LORO_Full_Experiment",
            "model_architecture": "6Q_RY_RealAmplitudes_Linear_Reps1_12Params",
            "observable": "Average_Pauli_Z_6Q",
            "optimizer": "COBYLA",
            "maxiter": maxiter,
            "seeds": eval_seeds,
            "evaluation_backend": "StatevectorEstimator",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "folds": {"fold_1": {}, "fold_2": {}},
    }

    print(f"Starting Phase 5 Full 10-Run LORO Experiment (maxiter={maxiter}, seeds={eval_seeds})...")
    total_start = time.time()

    for fold_id in (1, 2):
        fold_key = f"fold_{fold_id}"
        train_p = 106 if fold_id == 1 else 119
        val_p = 119 if fold_id == 1 else 106
        print(f"\n--- Executing {fold_key.upper()} (Train: {train_p}, Val: {val_p}) ---")

        for seed in eval_seeds:
            seed_key = f"seed_{seed}"
            print(f"  Running {seed_key} ...", end=" ", flush=True)
            run_res = run_diagnostic_training_run(fold_id=fold_id, seed=seed, maxiter=maxiter)
            runs_output["folds"][fold_key][seed_key] = run_res.to_dict()
            print(
                f"Done ({run_res.elapsed_seconds:.2f}s) | "
                f"Train MSE: {run_res.initial_train_metrics.mse_loss:.4f} -> {run_res.final_train_metrics.mse_loss:.4f} | "
                f"Val F1: {run_res.final_val_metrics.f1_score:.4f}"
            )

    total_elapsed = time.time() - total_start
    runs_output["metadata"]["total_elapsed_seconds"] = total_elapsed

    # Compute fold-level and macro summary
    f1_summary = compute_fold_summary_stats(runs_output["folds"]["fold_1"])
    f2_summary = compute_fold_summary_stats(runs_output["folds"]["fold_2"])

    macro_summary: Dict[str, Any] = {
        "num_folds": 2,
        "total_runs": len(eval_seeds) * 2,
        "total_elapsed_seconds": total_elapsed,
    }
    for metric_name in f1_summary.keys():
        if metric_name != "num_runs":
            m1 = f1_summary[metric_name]["mean"]
            m2 = f2_summary[metric_name]["mean"]
            macro_summary[metric_name] = {
                "macro_mean": float(0.5 * (m1 + m2)),
                "fold_1_mean": float(m1),
                "fold_2_mean": float(m2),
            }

    summary_output: Dict[str, Any] = {
        "metadata": runs_output["metadata"],
        "fold_1_summary": f1_summary,
        "fold_2_summary": f2_summary,
        "macro_summary": macro_summary,
    }

    # Save to disk
    runs_file = output_path or (PROJECT_ROOT / "results" / "vqc_training_runs.json")
    summary_file = summary_path or (PROJECT_ROOT / "results" / "vqc_loro_summary.json")

    runs_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)

    with open(runs_file, "w", encoding="utf-8") as f:
        json.dump(runs_output, f, indent=2)
    print(f"\n[OK] Saved all 10 training runs to: {runs_file}")

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_output, f, indent=2)
    print(f"[OK] Saved LORO statistical summary to: {summary_file}")

    return {
        "runs": runs_output,
        "summary": summary_output,
    }
