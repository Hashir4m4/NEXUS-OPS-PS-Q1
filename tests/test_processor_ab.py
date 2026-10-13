import sys
from pathlib import Path
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector

from processors.processor_a import (
    build_processor_a_coupling_map,
    build_processor_a_noise_model,
    get_processor_a_config,
    transpile_for_processor_a,
)
from processors.processor_b import (
    build_processor_b_coupling_map,
    build_processor_b_noise_model,
    get_processor_b_config,
    simulate_processor_b,
    transpile_for_processor_b,
)
from src.vqc_circuit import (
    build_ensemble_z_observable,
    build_vqc_circuit,
    create_parameter_vectors,
    format_pub_parameters,
)


# --- Processor A Config & Topology Tests ---


def test_processor_a_config_integrity():
    """Verify Processor A JSON configuration integrity."""
    config = get_processor_a_config()
    assert config["name"] == "Processor_A"
    assert config["num_qubits"] == 5
    assert config["basis_gates"] == ["rz", "sx", "x", "cx"]
    assert config["noise_model"]["single_qubit_depolarizing_p"] == 0.001
    assert config["noise_model"]["cx_depolarizing_p"] == 0.005
    assert config["noise_model"]["readout_error_p"] == 0.01
    # 4 unique undirected edges -> 8 directed edges
    assert len(config["coupling_map"]) == 8
    assert len(config["unique_undirected_edges"]) == 4


def test_processor_a_coupling_map_structure():
    """Verify CouplingMap graph properties for Processor A."""
    cmap = build_processor_a_coupling_map()
    assert cmap.size() == 5
    # Canonical line has edges: (0,1), (1,2), (2,3), (3,4)
    expected_undirected = {(0, 1), (1, 2), (2, 3), (3, 4)}
    actual_undirected = {tuple(sorted(edge)) for edge in cmap.get_edges()}
    assert actual_undirected == expected_undirected


def test_processor_a_noise_model_structure():
    """Verify Processor A noise model contains required error terms."""
    noise_model = build_processor_a_noise_model()
    basis = noise_model.basis_gates
    assert "cx" in basis
    assert "x" in basis
    assert "sx" in basis


# --- Processor B Config & Topology Tests ---


def test_processor_b_config_integrity():
    """Verify Processor B JSON configuration integrity."""
    config = get_processor_b_config()
    assert config["name"] == "Processor_B"
    assert config["num_qubits"] == 9
    assert config["basis_gates"] == ["rz", "sx", "x", "cx"]
    assert config["noise_model"]["single_qubit_depolarizing_p"] == 0.001
    assert config["noise_model"]["cx_depolarizing_p"] == 0.005
    assert config["noise_model"]["readout_error_p"] == 0.01
    # 8 unique undirected edges -> 16 directed edges
    assert len(config["coupling_map"]) == 16
    assert len(config["unique_undirected_edges"]) == 8


def test_processor_b_coupling_map_structure():
    """Verify CouplingMap graph properties for Processor B."""
    cmap = build_processor_b_coupling_map()
    assert cmap.size() == 9
    # Canonical sparse graph: 0-1, 1-2, 2-3, 2-4, 4-5, 5-6, 4-7, 7-8
    expected_undirected = {(0, 1), (1, 2), (2, 3), (2, 4), (4, 5), (5, 6), (4, 7), (7, 8)}
    actual_undirected = {tuple(sorted(edge)) for edge in cmap.get_edges()}
    assert actual_undirected == expected_undirected


# --- Capacity Constraint & VQC Mapping Tests ---


def test_processor_a_capacity_rejection_for_6q_vqc():
    """Verify 6-qubit approved VQC is rejected on 5-qubit Processor A with diagnostic message."""
    p_enc, p_var = create_parameter_vectors()
    qc_6q = build_vqc_circuit(p_enc, p_var)

    result = transpile_for_processor_a(qc_6q)
    assert result["success"] is False
    assert result["capacity_exceeded"] is True
    assert result["error_type"] == "CircuitTooWideForTarget"
    assert "exceeds Processor A physical capacity" in result["message"]
    assert result["transpiled_circuit"] is None


def test_processor_a_5q_reference_transpilation():
    """Verify 5-qubit reference circuit transpiles cleanly on Processor A line."""
    p_enc = ParameterVector("p_enc", 5)
    p_var = ParameterVector("p_var", 10)
    qc_5q = QuantumCircuit(5)
    for i in range(5):
        qc_5q.ry(p_enc[i], i)
    for i in range(5):
        qc_5q.ry(p_var[i], i)
    for i in range(4):
        qc_5q.cx(i, i + 1)
    for i in range(5):
        qc_5q.ry(p_var[5 + i], i)

    # 1. Canonical Line
    res_line = transpile_for_processor_a(qc_5q, variant="canonical")
    assert res_line["success"] is True
    assert res_line["cx_count"] == 4  # Exactly 4 CX gates, 0 SWAPs
    assert res_line["swap_count"] == 0
    assert res_line["depth"] == 14

    # 2. Branching Tree Variant (requires SWAP)
    res_tree = transpile_for_processor_a(qc_5q, variant="branching")
    assert res_tree["success"] is True
    assert res_tree["cx_count"] == 7  # 4 CX + 1 SWAP (3 CX) = 7 CX
    assert res_tree["depth"] == 21


def test_processor_b_vqc_transpilation_zero_swap_overhead():
    """Verify approved 6-qubit VQC transpiles onto Processor B with 0 SWAPs."""
    p_enc, p_var = create_parameter_vectors()
    qc_6q = build_vqc_circuit(p_enc, p_var)

    res = transpile_for_processor_b(qc_6q, variant="canonical", optimization_level=1, seed_transpiler=42)
    assert res["success"] is True
    assert res["logical_qubits"] == 6
    assert res["physical_qubits"] == 9
    assert res["cx_count"] == 5  # Exactly 5 CX gates, 0 SWAPs!
    assert res["swap_count"] == 0
    assert res["routing_overhead_cx"] == 0
    assert res["depth"] == 15
    # Gate counts: 36 rz, 24 sx, 5 cx -> 65 total gates
    assert res["ops"]["rz"] == 36
    assert res["ops"]["sx"] == 24
    assert res["ops"]["cx"] == 5
    assert res["total_ops"] == 65


def test_processor_b_cyclic_variant_transpilation():
    """Verify approved 6-qubit VQC transpiles onto Processor B cyclic mesh variant."""
    p_enc, p_var = create_parameter_vectors()
    qc_6q = build_vqc_circuit(p_enc, p_var)

    res = transpile_for_processor_b(qc_6q, variant="cyclic", optimization_level=1, seed_transpiler=42)
    assert res["success"] is True
    assert res["cx_count"] == 5
    assert res["routing_overhead_cx"] == 0
    assert res["depth"] == 15


# --- Processor B Simulation Integration Tests ---


def test_processor_b_ideal_and_noisy_simulation():
    """Verify Processor B ideal and noisy simulation pipeline under EstimatorV2."""
    p_enc, p_var = create_parameter_vectors()
    qc = build_vqc_circuit(p_enc, p_var)
    obs = build_ensemble_z_observable()

    x_dummy = np.array([0.5, 1.2, 0.8, 1.5, 0.3, 2.1])
    theta_dummy = np.zeros(12)
    pub_params = format_pub_parameters(x_dummy, theta_dummy)

    sim_res = simulate_processor_b(
        circuit=qc,
        observable=obs,
        pub_parameters=pub_params,
        shots=4096,
        seed_simulator=42,
        run_noisy=True,
    )

    assert "ideal_expectation" in sim_res
    assert "noisy_expectation" in sim_res
    assert "noisy_std_error" in sim_res
    assert "absolute_deviation" in sim_res

    # Check bounds
    assert -1.0 <= sim_res["ideal_expectation"] <= 1.0
    assert -1.0 <= sim_res["noisy_expectation"] <= 1.0
    # Standard error for 4096 shots is 1 / sqrt(4096) = 0.015625
    assert pytest.approx(sim_res["noisy_std_error"], rel=1e-3) == 0.015625
    # Ideal vs noisy should be close (within 3 standard errors + gate error shift)
    assert sim_res["absolute_deviation"] < 0.10
