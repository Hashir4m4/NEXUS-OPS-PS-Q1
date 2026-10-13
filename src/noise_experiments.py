"""
Noisy Simulation & Quantum Noise Resilience Experiments
========================================================
NEXUS-OPS | PS-Q1: Biomedical Classifier (Phase 6: Hardware Experiments)

Responsibilities:
-----------------
1. Execute full-cohort (N=100) noise experiments comparing ideal statevector simulation
   against the official Processor B synthetic noise model.
2. Compile the approved 6Q VQC to Processor B native basis ['rz', 'sx', 'x', 'cx']
   and map the logical observable to physical qubits via transpile layout.
3. Apply the authoritative challenge noise model:
   - 1Q depolarizing error: p = 0.001 (on 'x', 'sx')
   - 2Q (CX) depolarizing error: p = 0.005 (on 'cx')
   - Readout error: p = 0.01 (on measured physical qubits)
4. Distinguish between two simulation execution paths:
   A. EstimatorV2 Path: Evaluates gate-depolarizing noise on compiled native gates;
      does NOT apply ReadoutError (as verified by diagnostic audit).
   B. Measurement-Based AerSimulator Path: Applies measurement operations to physical
      qubits, genuinely simulating BOTH gate noise AND readout bit-flip noise.
5. Provide a controlled validation with deliberately exaggerated readout error.
6. Evaluate metric degradation (Accuracy, F1, Sensitivity, Specificity, Precision, ROC-AUC, MSE, Delta p).
7. Perform patient-stratified noise impact analysis (Record 200 vs. Record 208).
8. Serialize comprehensive results to results/noisy_simulation_results.json.
"""

from collections import defaultdict
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import ClassicalRegister
from qiskit.primitives import StatevectorEstimator
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
from qiskit_aer.primitives import EstimatorV2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.vqc_circuit import (
    NUM_QUBITS,
    NUM_VARIATIONAL_PARAMS,
    create_parameter_vectors,
    build_vqc_circuit,
    build_ensemble_z_observable,
    format_pub_parameters,
    expectation_to_probability,
)
from src.vqc_training import compute_vqc_metrics
from src.vqc_preprocessing import prepare_final_benchmark_datasets
from processors.processor_b import (
    build_processor_b_coupling_map,
    build_processor_b_noise_model,
)

RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def verify_readout_error_diagnostic() -> Dict[str, Any]:
    """
    Executes a controlled diagnostic proving that EstimatorV2 bypasses ReadoutError,
    while AerSimulator with measurement operations correctly applies it.

    Uses a single-qubit state |0> (theoretical Z expectation = +1.0) with an
    exaggerated 50% readout error probability (ReadoutError([[0.5, 0.5], [0.5, 0.5]])).

    Returns
    -------
    Dict[str, Any]
        Diagnostic verification findings.
    """
    from qiskit.quantum_info import SparsePauliOp

    qc_no_meas = QuantumCircuit(1)
    obs = SparsePauliOp.from_list([("Z", 1.0)])

    noise_ro_50 = NoiseModel()
    noise_ro_50.add_all_qubit_readout_error(ReadoutError([[0.5, 0.5], [0.5, 0.5]]))

    # 1. EstimatorV2 execution
    est = EstimatorV2(
        options={
            "run_options": {"shots": 10000},
            "backend_options": {"noise_model": noise_ro_50, "seed_simulator": 42},
        }
    )
    job_est = est.run([(qc_no_meas, obs)])
    ev_est = float(job_est.result()[0].data.evs)

    # 2. AerSimulator with measurement
    qc_meas = QuantumCircuit(1, 1)
    qc_meas.measure(0, 0)
    sim = AerSimulator(noise_model=noise_ro_50, seed_simulator=42)
    counts = sim.run(qc_meas, shots=10000).result().get_counts()
    ev_meas = (counts.get("0", 0) - counts.get("1", 0)) / 10000.0

    return {
        "diagnostic_description": "Exaggerated 50% readout error test on single qubit |0>",
        "theoretical_ideal_expectation": 1.0,
        "theoretical_attenuated_expectation_under_50pct_readout": 0.0,
        "estimator_v2_measured_expectation": ev_est,
        "estimator_v2_applied_readout_error": bool(abs(ev_est - 1.0) > 0.1),
        "measurement_sampler_measured_expectation": float(ev_meas),
        "measurement_sampler_applied_readout_error": bool(abs(ev_meas - 0.0) < 0.1),
        "conclusion": (
            "EstimatorV2 ignores ReadoutError because it evaluates snapshot expectations "
            "without measurement operations. Measurement-based AerSimulator correctly applies ReadoutError."
        ),
    }


def simulate_full_measurement_noise(
    compiled_circuit: QuantumCircuit,
    logical_to_physical: List[int],
    X_samples: np.ndarray,
    theta: np.ndarray,
    noise_model: NoiseModel,
    shots: int = 4096,
    seed_simulator: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Executes a measurement-based noisy simulation on Processor B applying
    both gate depolarizing error and classical readout bit-flip errors.

    Parameters
    ----------
    compiled_circuit : QuantumCircuit
        Transpiled circuit on Processor B.
    logical_to_physical : List[int]
        Physical qubit index mapped to each logical qubit 0..5.
    X_samples : np.ndarray
        Array of feature vectors shape (N, 6).
    theta : np.ndarray
        Variational parameter vector shape (12,).
    noise_model : NoiseModel
        Qiskit Aer NoiseModel with gate and readout error.
    shots : int
        Shot count per sample (default: 4096).
    seed_simulator : int
        RNG seed for simulation.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray, np.ndarray]
        (expectations, probabilities, binary_predictions).
    """
    p_enc = [p for p in compiled_circuit.parameters if p.name.startswith("p_enc")]
    p_var = [p for p in compiled_circuit.parameters if p.name.startswith("p_var")]
    p_enc.sort(key=lambda p: int(p.name.split("[")[-1].split("]")[0]) if "[" in p.name else p.name)
    p_var.sort(key=lambda p: int(p.name.split("[")[-1].split("]")[0]) if "[" in p.name else p.name)

    # Add 6 classical measurement bits
    meas_circuit = compiled_circuit.copy()
    creg = ClassicalRegister(6, "meas")
    meas_circuit.add_register(creg)
    for log_i, phys_i in enumerate(logical_to_physical):
        meas_circuit.measure(phys_i, creg[log_i])

    sim = AerSimulator(noise_model=noise_model, seed_simulator=seed_simulator)

    circuits_to_run = []
    for i in range(len(X_samples)):
        param_dict = {p_enc[j]: X_samples[i, j] for j in range(6)}
        param_dict.update({p_var[j]: theta[j] for j in range(12)})
        bound = meas_circuit.assign_parameters(param_dict)
        circuits_to_run.append(bound)

    job = sim.run(circuits_to_run, shots=shots)
    result = job.result()

    evs = []
    for i in range(len(X_samples)):
        counts = result.get_counts(i)
        total_ev = 0.0
        for bitstring, count in counts.items():
            # bitstring ordered from right to left: creg[0] is at bitstring[5]
            bits = [int(bitstring[5 - k]) for k in range(6)]
            ev_sample = np.mean([1 - 2 * b for b in bits])
            total_ev += ev_sample * count
        evs.append(total_ev / float(shots))

    evs_arr = np.clip(np.array(evs, dtype=float), -1.0, 1.0)
    probs_arr = expectation_to_probability(evs_arr)
    preds_arr = (probs_arr >= 0.5).astype(int)

    return evs_arr, probs_arr, preds_arr


def run_cohort_noise_experiment(
    shots: int = 4096,
    seed_transpiler: int = 42,
    seed_simulator: int = 42,
    additional_sim_seeds: Optional[List[int]] = None,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes a comprehensive, full-cohort noisy simulation on Processor B
    incorporating both gate noise and measurement-based readout noise paths.

    Parameters
    ----------
    shots : int
        Measurement shot budget for Aer simulation (default: 4096).
    seed_transpiler : int
        RNG seed for SABRE circuit transpilation.
    seed_simulator : int
        Primary RNG seed for Aer noisy simulation.
    additional_sim_seeds : Optional[List[int]]
        Optional additional simulator seeds for multi-seed noise verification.
    output_path : Optional[Path]
        Output path for results JSON.

    Returns
    -------
    Dict[str, Any]
        Complete noisy simulation results dictionary.
    """
    out_file = output_path or (RESULTS_DIR / "noisy_simulation_results.json")
    sim_seeds = [seed_simulator]
    if additional_sim_seeds:
        for s in additional_sim_seeds:
            if s not in sim_seeds:
                sim_seeds.append(s)

    # 1. Diagnostic audit check
    ro_diagnostic = verify_readout_error_diagnostic()

    # 2. Load frozen selected model
    sel_path = RESULTS_DIR / "vqc_model_selection.json"
    if not sel_path.exists():
        raise FileNotFoundError(f"Model selection file not found at {sel_path}")
    with open(sel_path, "r", encoding="utf-8") as f:
        selected_model_data = json.load(f)

    winner = selected_model_data["selected_candidate"]
    theta_opt = np.array(winner["optimal_theta"], dtype=float)

    # 3. Load held-out test cohort
    train_csv = DATA_DIR / "features_train.csv"
    test_csv = DATA_DIR / "features_test.csv"
    df_train = pd.read_csv(train_csv)
    df_test = pd.read_csv(test_csv)

    final_train, final_test, _ = prepare_final_benchmark_datasets(df_train, df_test)
    X_test, y_test = final_test.X, final_test.y
    num_samples = len(y_test)

    # 4. Construct and transpile approved circuit for Processor B
    p_enc, p_var = create_parameter_vectors()
    vqc_circuit = build_vqc_circuit(p_enc, p_var)
    logical_obs = build_ensemble_z_observable()

    cmap = build_processor_b_coupling_map(variant="canonical")
    basis_gates = ["rz", "sx", "x", "cx"]
    compiled_circuit = transpile(
        vqc_circuit,
        coupling_map=cmap,
        basis_gates=basis_gates,
        optimization_level=1,
        seed_transpiler=seed_transpiler,
    )

    # Map observable to compiled physical layout
    physical_obs = logical_obs.apply_layout(compiled_circuit.layout)
    pub_params = format_pub_parameters(X_test, theta_opt)

    # Map logical qubits to physical qubits at the output of the circuit.
    # Using final_index_layout() accounts for any potential routing/SWAP permutations.
    if hasattr(compiled_circuit.layout, "final_index_layout"):
        logical_to_physical = compiled_circuit.layout.final_index_layout()
    else:
        logical_to_physical = [compiled_circuit.layout.initial_layout[vqc_circuit.qubits[i]] for i in range(6)]

    # 5. Ideal Simulation (Statevector linear algebra baseline)
    sv_estimator = StatevectorEstimator()
    job_ideal = sv_estimator.run([(compiled_circuit, physical_obs, pub_params)])
    res_ideal = job_ideal.result()
    evs_ideal = np.asarray(res_ideal[0].data.evs, dtype=float)
    probs_ideal = expectation_to_probability(evs_ideal)
    preds_ideal = (probs_ideal >= 0.5).astype(int)
    metrics_ideal = compute_vqc_metrics(y_test, probs_ideal).to_dict()

    # 6. Execution Path A: EstimatorV2 (Gate Depolarizing Noise + Finite Shots Only)
    noise_model = build_processor_b_noise_model()
    precision = 1.0 / np.sqrt(shots)

    aer_estimator = EstimatorV2(
        options={
            "default_precision": precision,
            "run_options": {"shots": shots},
            "backend_options": {
                "noise_model": noise_model,
                "seed_simulator": seed_simulator,
            },
        }
    )
    job_est = aer_estimator.run([(compiled_circuit, physical_obs, pub_params)])
    evs_gate_only = np.clip(np.asarray(job_est.result()[0].data.evs, dtype=float), -1.0, 1.0)
    probs_gate_only = expectation_to_probability(evs_gate_only)
    preds_gate_only = (probs_gate_only >= 0.5).astype(int)
    metrics_gate_only = compute_vqc_metrics(y_test, probs_gate_only).to_dict()

    # 7. Execution Path B: Measurement-Based AerSimulator (Gate Noise + Readout Noise + Shots)
    evs_full_noise, probs_full_noise, preds_full_noise = simulate_full_measurement_noise(
        compiled_circuit=compiled_circuit,
        logical_to_physical=logical_to_physical,
        X_samples=X_test,
        theta=theta_opt,
        noise_model=noise_model,
        shots=shots,
        seed_simulator=seed_simulator,
    )
    metrics_full_noise = compute_vqc_metrics(y_test, probs_full_noise).to_dict()

    # Degradation metrics
    def _calc_degradation(m_noisy: Dict[str, Any], m_base: Dict[str, Any]) -> Dict[str, float]:
        return {
            "delta_accuracy": float(m_noisy["accuracy"] - m_base["accuracy"]),
            "delta_f1_score": float(m_noisy["f1_score"] - m_base["f1_score"]),
            "delta_sensitivity": float(m_noisy["sensitivity"] - m_base["sensitivity"]),
            "delta_specificity": float(m_noisy["specificity"] - m_base["specificity"]),
            "delta_precision": float(m_noisy["precision"] - m_base["precision"]),
            "delta_roc_auc": float(m_noisy["roc_auc"] - m_base["roc_auc"]),
            "delta_mse_loss": float(m_noisy["mse_loss"] - m_base["mse_loss"]),
            "delta_class_polarity_delta_p": float(m_noisy["class_polarity_delta_p"] - m_base["class_polarity_delta_p"]),
        }

    degradation_gate_only = _calc_degradation(metrics_gate_only, metrics_ideal)
    degradation_full_noise = _calc_degradation(metrics_full_noise, metrics_ideal)

    # Flips vs Ideal
    flips_gate = (preds_ideal != preds_gate_only)
    flips_full = (preds_ideal != preds_full_noise)

    # Patient-stratified comparison for Full Noise
    patient_stratified = {}
    for rec_id in [200, 208]:
        mask = (df_test["record_id"] == rec_id).values
        p_y = y_test[mask]
        p_id_prob = probs_ideal[mask]
        p_fn_prob = probs_full_noise[mask]
        m_p_id = compute_vqc_metrics(p_y, p_id_prob).to_dict()
        m_p_fn = compute_vqc_metrics(p_y, p_fn_prob).to_dict()
        patient_stratified[str(rec_id)] = {
            "num_samples": int(np.sum(mask)),
            "ideal_metrics": m_p_id,
            "full_noise_metrics": m_p_fn,
            "metric_delta": {
                "delta_accuracy": float(m_p_fn["accuracy"] - m_p_id["accuracy"]),
                "delta_f1": float(m_p_fn["f1_score"] - m_p_id["f1_score"]),
                "delta_sensitivity": float(m_p_fn["sensitivity"] - m_p_id["sensitivity"]),
                "delta_specificity": float(m_p_fn["specificity"] - m_p_id["specificity"]),
                "delta_mse": float(m_p_fn["mse_loss"] - m_p_id["mse_loss"]),
            },
            "flip_count": int(np.sum((p_id_prob >= 0.5) != (p_fn_prob >= 0.5))),
            "mean_abs_error_prob": float(np.mean(np.abs(p_fn_prob - p_id_prob))),
        }

    # Multi-seed evaluation for Full Noise
    multi_seed_full_noise = []
    for s in sim_seeds:
        evs_s, probs_s, _ = simulate_full_measurement_noise(
            compiled_circuit=compiled_circuit,
            logical_to_physical=logical_to_physical,
            X_samples=X_test,
            theta=theta_opt,
            noise_model=noise_model,
            shots=shots,
            seed_simulator=s,
        )
        met_s = compute_vqc_metrics(y_test, probs_s).to_dict()
        multi_seed_full_noise.append({
            "seed_simulator": s,
            "accuracy": met_s["accuracy"],
            "f1_score": met_s["f1_score"],
            "sensitivity": met_s["sensitivity"],
            "specificity": met_s["specificity"],
            "precision": met_s["precision"],
            "mse_loss": met_s["mse_loss"],
            "roc_auc": met_s["roc_auc"],
            "polarity_delta_p": met_s["class_polarity_delta_p"],
            "mae_vs_ideal_exp": float(np.mean(np.abs(evs_s - evs_ideal))),
        })

    payload = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "processor": "Processor B (Canonical Sparse Tree, 9Q)",
            "selected_model_run_id": winner["run_id"],
            "shots": shots,
            "seed_transpiler": seed_transpiler,
            "primary_seed_simulator": seed_simulator,
            "noise_model_parameters": {
                "single_qubit_depolarizing_p": 0.001,
                "cx_depolarizing_p": 0.005,
                "readout_error_p": 0.01,
            },
            "total_test_samples": num_samples,
            "basis_gates": basis_gates,
            "transpiled_circuit_depth": compiled_circuit.depth(),
            "transpiled_circuit_ops": dict(compiled_circuit.count_ops()),
            "logical_to_physical_qubits": logical_to_physical,
        },
        "readout_diagnostic_audit": ro_diagnostic,
        "ideal_baseline": metrics_ideal,
        "path_a_gate_noise_only": {
            "execution_method": "Qiskit Aer EstimatorV2 (operator snapshot expectation)",
            "readout_error_applied": False,
            "gate_noise_applied": True,
            "metrics": metrics_gate_only,
            "degradation_delta": degradation_gate_only,
            "flip_count": int(np.sum(flips_gate)),
            "flip_rate": float(np.mean(flips_gate)),
            "mae_expectation": float(np.mean(np.abs(evs_gate_only - evs_ideal))),
        },
        "path_b_full_noise_combined": {
            "execution_method": "Qiskit AerSimulator with physical measurements",
            "readout_error_applied": True,
            "gate_noise_applied": True,
            "metrics": metrics_full_noise,
            "degradation_delta": degradation_full_noise,
            "flip_count": int(np.sum(flips_full)),
            "flip_rate": float(np.mean(flips_full)),
            "mae_expectation": float(np.mean(np.abs(evs_full_noise - evs_ideal))),
            "rmse_expectation": float(np.sqrt(np.mean((evs_full_noise - evs_ideal) ** 2))),
            "max_expectation_error": float(np.max(np.abs(evs_full_noise - evs_ideal))),
        },
        "patient_stratified_full_noise": patient_stratified,
        "multi_seed_simulations_full_noise": multi_seed_full_noise,
    }

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


if __name__ == "__main__":
    res = run_cohort_noise_experiment(shots=4096, additional_sim_seeds=[101, 202])
    print("Full-cohort noisy simulation completed successfully!")
    print(f"Saved to: {RESULTS_DIR / 'noisy_simulation_results.json'}")
    diag = res["readout_diagnostic_audit"]
    print("Readout Diagnostic: EstimatorV2 applied readout error?", diag["estimator_v2_applied_readout_error"], "| Measurement Sampler applied?", diag["measurement_sampler_applied_readout_error"])
    print("Path A (Gate Noise Only) Acc:", res["path_a_gate_noise_only"]["metrics"]["accuracy"], "| F1:", res["path_a_gate_noise_only"]["metrics"]["f1_score"])
    print("Path B (Gate + Readout Noise) Acc:", res["path_b_full_noise_combined"]["metrics"]["accuracy"], "| F1:", res["path_b_full_noise_combined"]["metrics"]["f1_score"])
    print("Path B Sensitivity:", res["path_b_full_noise_combined"]["metrics"]["sensitivity"])
