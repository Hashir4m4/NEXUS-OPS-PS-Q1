"""
Unit Tests for Quantum Hardware & Processor Experiments
=======================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier
"""

import json
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.transpilation_experiments import build_reference_5q_vqc
from processors.processor_a import transpile_for_processor_a
from processors.processor_b import transpile_for_processor_b
from src.vqc_circuit import build_vqc_circuit

RESULTS_DIR = PROJECT_ROOT / "results"


def test_build_reference_5q_vqc_structure():
    """Verifies that the reference 5Q VQC has 5 qubits, 15 parameters, and correct structure."""
    qc = build_reference_5q_vqc()
    assert qc.num_qubits == 5
    assert len(qc.parameters) == 15


def test_processor_a_capacity_limit_enforcement():
    """Verifies that the approved 6-qubit VQC cannot be transpiled on 5-qubit Processor A."""
    qc_6q = build_vqc_circuit()
    res = transpile_for_processor_a(qc_6q, variant="canonical")
    assert res["success"] is False
    assert res["capacity_exceeded"] is True
    assert res["error_type"] == "CircuitTooWideForTarget"


def test_processor_b_approved_6q_transpilation_metrics():
    """Verifies that the approved 6-qubit VQC transpiles onto Processor B with depth 15 and 5 CX."""
    qc_6q = build_vqc_circuit()
    res = transpile_for_processor_b(qc_6q, variant="canonical", optimization_level=1, seed_transpiler=42)
    assert res["success"] is True
    assert res["depth"] == 15
    assert res["cx_count"] == 5
    assert res["swap_count"] == 0
    assert res["routing_overhead_cx"] == 0


def test_phase6_artifacts_exist_and_conform_to_schema():
    """Verifies the existence and schema validity of Phase 6 results JSON files."""
    transp_path = RESULTS_DIR / "transpilation_comparison.json"
    noisy_path = RESULTS_DIR / "noisy_simulation_results.json"
    shot_path = RESULTS_DIR / "shot_based_results.json"

    assert transp_path.exists(), f"Missing {transp_path}"
    assert noisy_path.exists(), f"Missing {noisy_path}"
    assert shot_path.exists(), f"Missing {shot_path}"

    with open(transp_path, "r", encoding="utf-8") as f:
        t_data = json.load(f)
    assert "statistical_summary" in t_data
    assert "processor_b_approved_6q" in t_data["statistical_summary"]

    with open(noisy_path, "r", encoding="utf-8") as f:
        n_data = json.load(f)
    assert "readout_diagnostic_audit" in n_data
    assert "path_a_gate_noise_only" in n_data
    assert "path_b_full_noise_combined" in n_data
    assert n_data["path_b_full_noise_combined"]["metrics"]["sensitivity"] == 1.0
    assert 0.0 <= n_data["path_b_full_noise_combined"]["mae_expectation"] <= 0.05

    with open(shot_path, "r", encoding="utf-8") as f:
        s_data = json.load(f)
    assert "shot_scaling_results" in s_data
    assert "256" in s_data["shot_scaling_results"]
    assert "4096" in s_data["shot_scaling_results"]
    assert s_data["shot_scaling_results"]["4096"]["empirical_mean_std"] < s_data["shot_scaling_results"]["256"]["empirical_mean_std"]


def test_readout_error_diagnostic_distinguishes_estimator_and_sampler():
    """Verifies that EstimatorV2 bypasses ReadoutError, while AerSimulator with measurements applies it."""
    from src.noise_experiments import verify_readout_error_diagnostic

    diag = verify_readout_error_diagnostic()
    assert diag["estimator_v2_applied_readout_error"] is False
    assert diag["measurement_sampler_applied_readout_error"] is True
    assert abs(diag["measurement_sampler_measured_expectation"]) < 0.1
    assert abs(diag["estimator_v2_measured_expectation"] - 1.0) < 0.01


def test_transpiler_mapping_and_ideal_measurement_equivalence():
    """
    Verifies that:
    1. Transpilation onto Processor B produces identity routing permutation (zero SWAPs).
    2. final_index_layout() matches [0, 1, 2, 4, 5, 6].
    3. Classical-bit ordering in measurement circuit correctly extracts logical expectation values.
    4. Ideal Aer measurement expectations match Statevector expectations across multiple parameterized samples.
    """
    import numpy as np
    from qiskit import ClassicalRegister, transpile
    from qiskit.primitives import StatevectorEstimator
    from qiskit_aer import AerSimulator
    from src.vqc_circuit import (
        create_parameter_vectors,
        build_vqc_circuit,
        build_ensemble_z_observable,
        format_pub_parameters,
    )
    from processors.processor_b import build_processor_b_coupling_map

    p_enc, p_var = create_parameter_vectors()
    vqc = build_vqc_circuit(p_enc, p_var)
    cmap = build_processor_b_coupling_map()

    c = transpile(
        vqc,
        coupling_map=cmap,
        basis_gates=["rz", "sx", "x", "cx"],
        optimization_level=1,
        seed_transpiler=42,
    )

    # 1. Verify routing permutation and final layout
    assert c.layout is not None, "Compiled circuit must possess layout"
    routing_perm = c.layout.routing_permutation()
    assert routing_perm == list(range(9)), f"Expected identity routing permutation, got {routing_perm}"

    final_layout = c.layout.final_index_layout()
    assert final_layout == [0, 1, 2, 4, 5, 6], f"Unexpected final_index_layout: {final_layout}"

    ops = c.count_ops()
    assert ops.get("swap", 0) == 0, "No SWAP gates should be inserted"

    # 2. Setup multiple parameterized test samples
    np.random.seed(42)
    n_samples = 5
    X_test_samples = np.random.uniform(0.0, np.pi, size=(n_samples, 6))
    theta_test = np.random.uniform(-np.pi, np.pi, size=12)

    # 3. Statevector exact expectations
    phys_obs = build_ensemble_z_observable().apply_layout(c.layout)
    pub_params = format_pub_parameters(X_test_samples, theta_test)
    est = StatevectorEstimator()
    res_est = est.run([(c, phys_obs, pub_params)]).result()
    sv_expectations = np.asarray(res_est[0].data.evs, dtype=float)

    # 4. Ideal Aer measurement sampler with classical register
    p_enc_list = [p for p in c.parameters if p.name.startswith("p_enc")]
    p_var_list = [p for p in c.parameters if p.name.startswith("p_var")]
    p_enc_list.sort(key=lambda p: int(p.name.split("[")[-1].split("]")[0]))
    p_var_list.sort(key=lambda p: int(p.name.split("[")[-1].split("]")[0]))
    ordered_params = p_enc_list + p_var_list

    meas_c = c.copy()
    creg = ClassicalRegister(6, "meas")
    meas_c.add_register(creg)
    for log_i, phys_i in enumerate(final_layout):
        meas_c.measure(phys_i, creg[log_i])

    sim = AerSimulator(seed_simulator=42)
    shots = 50000
    aer_expectations = []

    for i in range(n_samples):
        param_dict = dict(zip(ordered_params, list(X_test_samples[i]) + list(theta_test)))
        bound = meas_c.assign_parameters(param_dict)
        counts = sim.run(bound, shots=shots).result().get_counts()

        total_ev = 0.0
        for bitstring, count in counts.items():
            # In Qiskit little-endian: creg[k] is at bitstring[5 - k]
            bits = [int(bitstring[5 - k]) for k in range(6)]
            ev_sample = np.mean([1 - 2 * b for b in bits])
            total_ev += ev_sample * count
        aer_expectations.append(total_ev / float(shots))

    aer_expectations = np.array(aer_expectations)
    diffs = np.abs(sv_expectations - aer_expectations)

    # Discrepancy must be within statistical shot noise tolerance for 50k shots
    # Standard error SE = sqrt(Var/S) <= 1/sqrt(50000) ~= 0.00447. 3.5 * SE ~= 0.015
    assert np.all(diffs < 0.015), f"Discrepancy exceeds sampling noise tolerance: max diff {np.max(diffs)}"


