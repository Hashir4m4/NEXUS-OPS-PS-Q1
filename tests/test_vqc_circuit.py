"""
Unit Tests for Core VQC Circuit Module
======================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 5F.2)

Verifies:
- Step 1: Parameter vector creation, deterministic prefix hygiene, and feature map construction.
- Step 2-4: Ansatz, composite circuit, observable, and batch execution (scaffolded test stubs).
"""

import sys
from pathlib import Path
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qiskit.circuit import ParameterVector, QuantumCircuit
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp, Statevector

from src.vqc_circuit import (
    NUM_QUBITS,
    NUM_ENCODING_PARAMS,
    NUM_VARIATIONAL_PARAMS,
    TOTAL_CIRCUIT_PARAMS,
    ENCODING_PREFIX,
    VARIATIONAL_PREFIX,
    create_parameter_vectors,
    build_feature_map,
    build_ansatz,
    build_vqc_circuit,
    build_ensemble_z_observable,
    format_pub_parameters,
    expectation_to_probability,
    VQCCircuitBundle,
)


# ============================================================================
# STEP 1 TESTS: Parameter Vectors & Feature Map Invariants
# ============================================================================

def test_parameter_vectors_creation_and_prefixes():
    """
    Verifies that create_parameter_vectors creates two independent ParameterVectors
    with lengths 6 and 12, satisfying the prefix ordering condition: 'p_enc' < 'p_var'.
    """
    p_enc, p_var = create_parameter_vectors()

    assert isinstance(p_enc, ParameterVector)
    assert isinstance(p_var, ParameterVector)
    assert len(p_enc) == NUM_ENCODING_PARAMS
    assert len(p_var) == NUM_VARIATIONAL_PARAMS
    assert p_enc.name == ENCODING_PREFIX
    assert p_var.name == VARIATIONAL_PREFIX

    # Crucial alphabetical safeguard
    assert p_enc.name < p_var.name, (
        f"Encoding prefix '{p_enc.name}' must precede variational prefix '{p_var.name}' "
        "to ensure deterministic parameter ordering in Qiskit circuit.parameters."
    )


def test_parameter_vectors_element_names():
    """Verifies that individual parameters follow the expected indexed naming convention."""
    p_enc, p_var = create_parameter_vectors()

    for i in range(NUM_ENCODING_PARAMS):
        assert p_enc[i].name == f"{ENCODING_PREFIX}[{i}]"

    for j in range(NUM_VARIATIONAL_PARAMS):
        assert p_var[j].name == f"{VARIATIONAL_PREFIX}[{j}]"


def test_feature_map_structure_and_gates():
    """
    Verifies that build_feature_map constructs an untranspiled circuit with
    exactly 6 qubits, 6 Ry gates, 0 two-qubit gates, and depth 1.
    """
    qc_enc = build_feature_map()

    assert isinstance(qc_enc, QuantumCircuit)
    assert qc_enc.num_qubits == NUM_QUBITS
    assert qc_enc.num_parameters == NUM_ENCODING_PARAMS
    assert qc_enc.depth() == 1

    ops = dict(qc_enc.count_ops())
    assert ops == {"ry": NUM_ENCODING_PARAMS}, f"Expected only Ry gates, got {ops}"
    assert "cx" not in ops, "Feature map must not contain two-qubit entangling gates."


def test_feature_map_statevector_separable_product_state():
    """
    Verifies statevector evolution under the feature map:
    - At x = 0: All qubits remain |0>, state is |000000>
    - At x = pi: All qubits rotate to |1>, state is |111111>
    - At x = pi/2: Equal superposition state with strictly real amplitudes.
    """
    p_enc, _ = create_parameter_vectors()
    qc_enc = build_feature_map(p_enc)

    # 1. Evaluate at x = 0
    zero_vals = {p_enc[i]: 0.0 for i in range(NUM_QUBITS)}
    qc_zero = qc_enc.assign_parameters(zero_vals)
    sv_zero = Statevector(qc_zero)
    # Basis state |000000> has index 0
    assert np.isclose(sv_zero.data[0].real, 1.0)
    assert np.isclose(sv_zero.data[0].imag, 0.0)

    # 2. Evaluate at x = pi
    pi_vals = {p_enc[i]: np.pi for i in range(NUM_QUBITS)}
    qc_pi = qc_enc.assign_parameters(pi_vals)
    sv_pi = Statevector(qc_pi)
    # Basis state |111111> has index 63
    assert np.isclose(np.abs(sv_pi.data[63]), 1.0)
    assert np.isclose(sv_pi.data[63].imag, 0.0)

    # 3. Evaluate at x = pi/2 (equal superposition of 64 basis states)
    half_pi_vals = {p_enc[i]: np.pi / 2.0 for i in range(NUM_QUBITS)}
    qc_half_pi = qc_enc.assign_parameters(half_pi_vals)
    sv_half_pi = Statevector(qc_half_pi)
    expected_amplitude = 1.0 / np.sqrt(64)  # 1/8 = 0.125
    np.testing.assert_allclose(sv_half_pi.data.real, expected_amplitude, atol=1e-12)
    np.testing.assert_allclose(sv_half_pi.data.imag, 0.0, atol=1e-12)


# ============================================================================
# STEP 2 TESTS: Variational Ansatz Invariants
# ============================================================================

def test_ansatz_qubit_and_parameter_counts():
    """
    Verifies that build_ansatz constructs a circuit with exactly 6 qubits
    and exactly 12 variational parameters.
    """
    ansatz = build_ansatz()

    assert isinstance(ansatz, QuantumCircuit)
    assert ansatz.num_qubits == NUM_QUBITS
    assert ansatz.num_parameters == NUM_VARIATIONAL_PARAMS
    assert len(ansatz.parameters) == NUM_VARIATIONAL_PARAMS


def test_ansatz_gate_counts_and_measured_depth():
    """
    Verifies that build_ansatz has exactly 12 Ry gates, 5 CX gates,
    and a measured untranspiled circuit depth of 7.
    """
    ansatz = build_ansatz()

    ops = dict(ansatz.count_ops())
    assert ops == {"ry": 12, "cx": 5}, f"Expected 12 Ry and 5 CX gates, got {ops}"
    assert ansatz.depth() == 7, f"Measured depth mismatch: expected 7, got {ansatz.depth()}"


def test_ansatz_linear_cnot_entanglement_cascade():
    """
    Verifies the linear nearest-neighbor CNOT entanglement topology:
    Cascade pairs must be strictly: (0, 1), (1, 2), (2, 3), (3, 4), (4, 5).
    """
    ansatz = build_ansatz()

    cnot_pairs = []
    for instruction in ansatz.data:
        if instruction.operation.name == "cx":
            ctrl = ansatz.find_bit(instruction.qubits[0]).index
            tgt = ansatz.find_bit(instruction.qubits[1]).index
            cnot_pairs.append((ctrl, tgt))

    expected_pairs = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    assert cnot_pairs == expected_pairs, (
        f"Linear entanglement cascade mismatch: expected {expected_pairs}, got {cnot_pairs}"
    )


def test_ansatz_parameters_match_p_var_instance():
    """
    Verifies that passing a ParameterVector to build_ansatz binds the exact
    ParameterVectorElement instances with the approved 'p_var' prefix.
    """
    _, p_var = create_parameter_vectors()
    ansatz = build_ansatz(p_var)

    assert list(ansatz.parameters) == list(p_var)

    for idx, param in enumerate(ansatz.parameters):
        assert param.name == f"{VARIATIONAL_PREFIX}[{idx}]"
        # In Qiskit 2.x, circuit.parameters yields Rust-backed wrapper instances on each access,
        # so Python pointer identity (`is`) does not hold across the Rust boundary.
        # Parameter identity is verified via equality (__eq__), index, and vector name.
        assert param == p_var[idx]
        assert param.index == idx
        assert param.vector.name == VARIATIONAL_PREFIX


# ============================================================================
# STEP 3 TESTS: Composite VQC Circuit Invariants
# ============================================================================

def test_composite_vqc_circuit_qubits_and_parameters():
    """
    Verifies that build_vqc_circuit constructs a composite circuit with exactly
    6 qubits and exactly 18 parameters.
    """
    vqc = build_vqc_circuit()

    assert isinstance(vqc, QuantumCircuit)
    assert vqc.name == "VQC_Biomedical"
    assert vqc.num_qubits == NUM_QUBITS
    assert vqc.num_parameters == TOTAL_CIRCUIT_PARAMS
    assert len(vqc.parameters) == TOTAL_CIRCUIT_PARAMS


def test_composite_vqc_circuit_parameter_ordering():
    """
    Verifies deterministic parameter ordering:
    circuit.parameters must strictly contain encoding parameters p_enc[0..5]
    followed by variational parameters p_var[0..11].
    """
    p_enc, p_var = create_parameter_vectors()
    vqc = build_vqc_circuit(p_enc, p_var)

    assert len(vqc.parameters) == TOTAL_CIRCUIT_PARAMS
    expected_params = list(p_enc) + list(p_var)
    assert list(vqc.parameters) == expected_params

    # Verify element-by-element equality and attribute matching
    for idx, param in enumerate(vqc.parameters):
        if idx < NUM_ENCODING_PARAMS:
            assert param.name == f"{ENCODING_PREFIX}[{idx}]"
            assert param == p_enc[idx]
            assert param.index == idx
            assert param.vector.name == ENCODING_PREFIX
        else:
            var_idx = idx - NUM_ENCODING_PARAMS
            assert param.name == f"{VARIATIONAL_PREFIX}[{var_idx}]"
            assert param == p_var[var_idx]
            assert param.index == var_idx
            assert param.vector.name == VARIATIONAL_PREFIX


def test_composite_vqc_circuit_gate_counts_and_measured_depth():
    """
    Verifies that composite gate counts match the sum of component circuits
    (18 Ry gates, 5 CX gates) and that untranspiled circuit depth is exactly 8.
    """
    p_enc, p_var = create_parameter_vectors()
    qc_enc = build_feature_map(p_enc)
    ansatz = build_ansatz(p_var)
    vqc = build_vqc_circuit(qc_enc=qc_enc, ansatz=ansatz)

    ops = dict(vqc.count_ops())
    assert ops.get("ry", 0) == qc_enc.count_ops().get("ry", 0) + ansatz.count_ops().get("ry", 0)
    assert ops.get("cx", 0) == ansatz.count_ops().get("cx", 0)
    assert ops == {"ry": 18, "cx": 5}

    # Depth invariant: 1 (feature map) + 1 (ansatz rot1) + 5 (linear CX cascade) + 1 (ansatz rot2) = 8
    assert vqc.depth() == 8


def test_composite_vqc_circuit_gate_execution_order():
    """
    Verifies that feature map gates strictly precede variational ansatz gates in circuit.data.
    """
    vqc = build_vqc_circuit()

    # Total instructions: 6 (enc) + 17 (ansatz) = 23
    assert len(vqc.data) == 23

    # First 6 operations belong to feature map: Ry gates with p_enc parameters on qubits 0..5
    for i in range(NUM_QUBITS):
        inst = vqc.data[i]
        assert inst.operation.name == "ry"
        assert inst.operation.params[0].name == f"{ENCODING_PREFIX}[{i}]"
        assert vqc.find_bit(inst.qubits[0]).index == i

    # Subsequent operations belong to ansatz: 6 Ry, 5 CX, 6 Ry with p_var parameters
    for i in range(NUM_QUBITS, len(vqc.data)):
        inst = vqc.data[i]
        if inst.operation.name == "ry":
            assert inst.operation.params[0].name.startswith(VARIATIONAL_PREFIX)
        elif inst.operation.name == "cx":
            pass  # Entangling gates in ansatz


def test_composite_vqc_circuit_input_validation_and_errors():
    """
    Verifies input validation: rejects invalid parameter vector lengths,
    incompatible circuit inputs, and invalid types with descriptive exceptions.
    """
    # 1. Reject invalid encoding parameter vector length
    bad_enc = ParameterVector("p_enc", 5)
    with pytest.raises(ValueError, match="Encoding parameter vector length"):
        build_vqc_circuit(p_enc=bad_enc)

    # 2. Reject invalid variational parameter vector length
    bad_var = ParameterVector("p_var", 10)
    with pytest.raises(ValueError, match="Variational parameter vector length"):
        build_vqc_circuit(p_var=bad_var)

    # 3. Reject incompatible circuit with mismatched qubit count
    bad_circuit = QuantumCircuit(5)
    with pytest.raises(ValueError, match="qubit count"):
        build_vqc_circuit(qc_enc=bad_circuit)
    with pytest.raises(ValueError, match="qubit count"):
        build_vqc_circuit(ansatz=bad_circuit)

    # 4. Reject invalid types
    with pytest.raises(TypeError):
        build_vqc_circuit(p_enc=123)
    with pytest.raises(TypeError):
        build_vqc_circuit(p_var="invalid")


def test_composite_vqc_circuit_statevector_smoke_test():
    """
    Numerical smoke test: evaluates Statevector on bound composite circuit.
    Verifies state validity, unity norm, and purely real amplitudes in R^64.
    """
    p_enc, p_var = create_parameter_vectors()
    vqc = build_vqc_circuit(p_enc, p_var)

    # Bind arbitrary valid physiological angles and variational parameters
    x_test = np.array([0.5, 1.2, 2.1, 0.8, 1.9, 2.7], dtype=np.float64)
    theta_test = np.full(12, 0.05, dtype=np.float64)

    param_binding = {**dict(zip(p_enc, x_test)), **dict(zip(p_var, theta_test))}
    bound_circuit = vqc.assign_parameters(param_binding)

    sv = Statevector(bound_circuit)
    assert sv.is_valid(), "Output statevector is invalid."
    assert len(sv) == 64, "Statevector dimension must be 2^6 = 64."
    assert np.isclose(np.linalg.norm(sv.data), 1.0, atol=1e-12), "Statevector norm must equal 1.0."
    # Purely real manifold invariant
    assert np.allclose(sv.data.imag, 0.0, atol=1e-12), "Statevector must have strictly real amplitudes."


# ============================================================================
# STEP 4 TESTS: Six-Qubit Average Pauli-Z Observable Invariants
# ============================================================================

def test_observable_structure_and_weights():
    """
    Verifies that build_ensemble_z_observable constructs a 6-qubit SparsePauliOp
    containing exactly six Z terms, each with coefficient 1/6 and no identity or
    other Pauli operators.
    """
    obs = build_ensemble_z_observable()

    assert isinstance(obs, SparsePauliOp)
    assert obs.num_qubits == NUM_QUBITS
    assert len(obs) == NUM_QUBITS

    # Verify each term has coefficient exactly 1/6
    expected_weight = 1.0 / NUM_QUBITS
    np.testing.assert_allclose(obs.coeffs.real, expected_weight, atol=1e-12)
    np.testing.assert_allclose(obs.coeffs.imag, 0.0, atol=1e-12)

    # In Qiskit, Pauli string index 0 is the rightmost character (qubit 0).
    # from_sparse_list explicitly maps term ('Z', [i], 1/6) to qubit i.
    pauli_labels = obs.paulis.to_labels()
    assert len(pauli_labels) == NUM_QUBITS

    for i in range(NUM_QUBITS):
        # In Qiskit string representation, qubit i corresponds to index -(i + 1)
        label = pauli_labels[i]
        assert label.count("Z") == 1, f"Term {i} must contain exactly one Z operator, got {label}"
        assert label.count("I") == NUM_QUBITS - 1, f"Term {i} must contain {NUM_QUBITS - 1} identities, got {label}"
        assert label[-(i + 1)] == "Z", f"Term {i} must have Z at qubit position {i}, got {label}"


def test_observable_hermiticity_and_eigenvalues():
    """
    Verifies that the ensemble Z observable is Hermitian with spectrum in [-1, +1].
    """
    obs = build_ensemble_z_observable()
    mat = obs.to_matrix()

    # 1. Hermiticity: M^\dagger = M
    assert np.allclose(mat, mat.conj().T, atol=1e-12), "Observable matrix must be Hermitian."

    # 2. Eigenvalue bounds
    evals = np.linalg.eigvalsh(mat)
    assert np.isclose(evals.min(), -1.0, atol=1e-12), f"Minimum eigenvalue must be -1.0, got {evals.min()}"
    assert np.isclose(evals.max(), 1.0, atol=1e-12), f"Maximum eigenvalue must be +1.0, got {evals.max()}"
    assert np.all(evals >= -1.0 - 1e-12) and np.all(evals <= 1.0 + 1e-12), (
        "All eigenvalues must lie strictly within [-1.0, +1.0]."
    )


def test_observable_computational_basis_expectations():
    """
    Verifies expected analytical eigenvalues on computational basis states:
    - |000000> -> +1.0
    - |111111> -> -1.0
    - Any state with three zeros and three ones -> 0.0
    """
    obs = build_ensemble_z_observable()

    # 1. All-zero state |000000>
    sv_0 = Statevector.from_label("000000")
    exp_0 = sv_0.expectation_value(obs)
    assert np.isclose(exp_0.real, 1.0, atol=1e-12)
    assert np.isclose(exp_0.imag, 0.0, atol=1e-12)

    # 2. All-one state |111111>
    sv_1 = Statevector.from_label("111111")
    exp_1 = sv_1.expectation_value(obs)
    assert np.isclose(exp_1.real, -1.0, atol=1e-12)
    assert np.isclose(exp_1.imag, 0.0, atol=1e-12)

    # 3. Balanced states with three 0s and three 1s
    balanced_labels = ["000111", "111000", "101010", "010101", "110001"]
    for label in balanced_labels:
        sv_bal = Statevector.from_label(label)
        exp_bal = sv_bal.expectation_value(obs)
        assert np.isclose(exp_bal.real, 0.0, atol=1e-12), (
            f"Expected expectation 0.0 for balanced state |{label}>, got {exp_bal.real}"
        )
        assert np.isclose(exp_bal.imag, 0.0, atol=1e-12)


def test_observable_qubit_count_validation():
    """
    Verifies that build_ensemble_z_observable rejects unsupported qubit counts.
    """
    with pytest.raises(ValueError, match="Approved VQC architecture requires 6 qubits"):
        build_ensemble_z_observable(num_qubits=5)

    with pytest.raises(ValueError, match="Approved VQC architecture requires 6 qubits"):
        build_ensemble_z_observable(num_qubits=7)

    with pytest.raises(ValueError, match="num_qubits must be a positive integer"):
        build_ensemble_z_observable(num_qubits=0)

    with pytest.raises(ValueError, match="num_qubits must be a positive integer"):
        build_ensemble_z_observable(num_qubits="six")


def test_exact_analytic_statevector_edge_case():
    """
    Verifies the exact analytical edge case:
    At x = [pi, pi, pi, pi, pi, pi] and theta = zeros(12):
    - Feature map rotates |000000> to |111111>.
    - Variational Ry rotations at theta=0 are identities.
    - Linear CNOT cascade flips qubits 1, 3, and 5:
      (0,1) flips q1 from 1->0
      (1,2) q1 is 0, q2 remains 1
      (2,3) q2 is 1, q3 flips 1->0
      (3,4) q3 is 0, q4 remains 1
      (4,5) q4 is 1, q5 flips 1->0
    - Resulting state has q0=1, q1=0, q2=1, q3=0, q4=1, q5=0 (three 1s, three 0s).
    - The ensemble Z expectation value E is analytically identical to 0.0.
    """
    p_enc, p_var = create_parameter_vectors()
    vqc = build_vqc_circuit(p_enc, p_var)
    obs = build_ensemble_z_observable()

    param_binding = {
        **{p_enc[i]: np.pi for i in range(NUM_QUBITS)},
        **{p_var[i]: 0.0 for i in range(NUM_VARIATIONAL_PARAMS)},
    }
    bound_circuit = vqc.assign_parameters(param_binding)

    sv = Statevector(bound_circuit)
    exp_val = sv.expectation_value(obs)

    assert np.isclose(exp_val.real, 0.0, atol=1e-12), (
        f"Analytical edge case expectation mismatch: expected 0.0, got {exp_val.real}"
    )
    assert np.isclose(exp_val.imag, 0.0, atol=1e-12)


# ============================================================================
# STEP 5 TESTS: PUB Parameter Alignment Helper Invariants
# ============================================================================

def test_format_pub_parameters_single_sample_shape_and_dtype():
    """
    Verifies that a 1D single sample (shape (6,)) is promoted to 2D (1, 18),
    with float64 dtype and C-contiguous memory layout.
    """
    x_single = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], dtype=np.float64)
    theta = np.zeros(12, dtype=np.float64)

    pub_params = format_pub_parameters(x_single, theta)

    assert isinstance(pub_params, np.ndarray)
    assert pub_params.shape == (1, TOTAL_CIRCUIT_PARAMS)
    assert pub_params.dtype == np.float64
    assert pub_params.flags.c_contiguous


def test_format_pub_parameters_batch_shape_and_dtype():
    """
    Verifies that a 2D batch of features (shape (N, 6)) produces shape (N, 18),
    with float64 dtype and C-contiguous memory layout.
    """
    n_samples = 15
    batch_x = np.random.uniform(0.0, np.pi, size=(n_samples, NUM_ENCODING_PARAMS))
    theta = np.random.uniform(-0.1, 0.1, size=NUM_VARIATIONAL_PARAMS)

    pub_params = format_pub_parameters(batch_x, theta)

    assert pub_params.shape == (n_samples, TOTAL_CIRCUIT_PARAMS)
    assert pub_params.dtype == np.float64
    assert pub_params.flags.c_contiguous


def test_format_pub_parameters_feature_and_weight_alignment():
    """
    Verifies exact column-wise alignment:
    - Columns 0..5 match input features x exactly for every sample.
    - Columns 6..17 match variational parameters theta exactly for every sample.
    """
    n_samples = 4
    batch_x = np.array([
        [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
        [2.0, 2.1, 2.2, 2.3, 2.4, 2.5],
        [3.0, 3.1, 3.2, 3.3, 3.4, 3.5],
        [4.0, 4.1, 4.2, 4.3, 4.4, 4.5],
    ], dtype=np.float64)
    theta = np.array([0.01 * (i + 1) for i in range(12)], dtype=np.float64)

    pub_params = format_pub_parameters(batch_x, theta)

    # Feature columns alignment check
    np.testing.assert_array_equal(pub_params[:, :NUM_ENCODING_PARAMS], batch_x)

    # Variational columns alignment check
    expected_theta_tile = np.tile(theta.reshape(1, -1), (n_samples, 1))
    np.testing.assert_array_equal(pub_params[:, NUM_ENCODING_PARAMS:], expected_theta_tile)


def test_format_pub_parameters_ordering_matches_circuit_parameters():
    """
    Verifies that the column indices of format_pub_parameters strictly match
    the parameter names in circuit.parameters.
    """
    vqc = build_vqc_circuit()
    circuit_param_names = [p.name for p in vqc.parameters]

    x_test = np.arange(NUM_ENCODING_PARAMS, dtype=np.float64)
    theta_test = np.arange(NUM_VARIATIONAL_PARAMS, dtype=np.float64) + 100.0

    pub_params = format_pub_parameters(x_test, theta_test)

    # Columns 0..5 correspond to p_enc[0..5]
    for i in range(NUM_ENCODING_PARAMS):
        assert circuit_param_names[i] == f"{ENCODING_PREFIX}[{i}]"
        assert pub_params[0, i] == x_test[i]

    # Columns 6..17 correspond to p_var[0..11]
    for j in range(NUM_VARIATIONAL_PARAMS):
        col_idx = NUM_ENCODING_PARAMS + j
        assert circuit_param_names[col_idx] == f"{VARIATIONAL_PREFIX}[{j}]"
        assert pub_params[0, col_idx] == theta_test[j]


def test_format_pub_parameters_invalid_dimensions():
    """
    Verifies that format_pub_parameters rejects incorrect feature or weight shapes.
    """
    valid_x = np.ones((3, 6))
    valid_theta = np.zeros(12)

    # 1. Invalid feature counts (5 features instead of 6)
    with pytest.raises(ValueError, match="feature dimension"):
        format_pub_parameters(np.ones((3, 5)), valid_theta)
    with pytest.raises(ValueError, match="1D batch_x must have shape"):
        format_pub_parameters(np.ones(7), valid_theta)

    # 2. Invalid weight counts (10 weights instead of 12)
    with pytest.raises(ValueError, match="theta must have shape"):
        format_pub_parameters(valid_x, np.zeros(10))
    with pytest.raises(ValueError, match="2D theta must have shape"):
        format_pub_parameters(valid_x, np.zeros((2, 12)))

    # 3. 3D arrays
    with pytest.raises(ValueError, match="batch_x must be 1D or 2D"):
        format_pub_parameters(np.ones((2, 3, 6)), valid_theta)
    with pytest.raises(ValueError, match="theta must be 1D or 2D"):
        format_pub_parameters(valid_x, np.zeros((1, 2, 6)))


def test_format_pub_parameters_nan_and_inf_rejection():
    """
    Verifies that format_pub_parameters rejects NaN, +Inf, and -Inf in both
    features and variational weights.
    """
    valid_x = np.ones((2, 6))
    valid_theta = np.zeros(12)

    # 1. NaN in features
    bad_x_nan = valid_x.copy()
    bad_x_nan[0, 2] = np.nan
    with pytest.raises(ValueError, match="batch_x contains NaN or infinite values"):
        format_pub_parameters(bad_x_nan, valid_theta)

    # 2. Inf in features
    bad_x_inf = valid_x.copy()
    bad_x_inf[1, 0] = np.inf
    with pytest.raises(ValueError, match="batch_x contains NaN or infinite values"):
        format_pub_parameters(bad_x_inf, valid_theta)

    # 3. NaN in weights
    bad_theta_nan = valid_theta.copy()
    bad_theta_nan[5] = np.nan
    with pytest.raises(ValueError, match="theta contains NaN or infinite values"):
        format_pub_parameters(valid_x, bad_theta_nan)

    # 4. Inf in weights
    bad_theta_inf = valid_theta.copy()
    bad_theta_inf[11] = -np.inf
    with pytest.raises(ValueError, match="theta contains NaN or infinite values"):
        format_pub_parameters(valid_x, bad_theta_inf)


def test_format_pub_parameters_empty_batch_rejection():
    """
    Verifies that format_pub_parameters rejects empty feature batches or empty weights.
    """
    valid_theta = np.zeros(12)

    # Empty 2D features
    with pytest.raises(ValueError, match="batch_x must not be empty"):
        format_pub_parameters(np.empty((0, 6)), valid_theta)

    # Empty 1D features
    with pytest.raises(ValueError, match="batch_x must not be empty"):
        format_pub_parameters(np.array([]), valid_theta)

    # Empty weights
    with pytest.raises(ValueError, match="theta must not be empty"):
        format_pub_parameters(np.ones((2, 6)), np.array([]))


def test_format_pub_parameters_no_mutation_of_caller_inputs():
    """
    Verifies that caller inputs are not mutated in-place by format_pub_parameters.
    """
    x_orig = np.array([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]], dtype=np.float64)
    theta_orig = np.array([0.1 * i for i in range(12)], dtype=np.float64)

    x_copy = x_orig.copy()
    theta_copy = theta_orig.copy()

    pub_params = format_pub_parameters(x_orig, theta_orig)

    # Modify output array to test isolation
    pub_params[0, 0] = 999.0
    pub_params[0, 6] = 888.0

    np.testing.assert_array_equal(x_orig, x_copy)
    np.testing.assert_array_equal(theta_orig, theta_copy)


def test_format_pub_parameters_qiskit_pub_integration():
    """
    End-to-end integration test: passes formatted parameters into Qiskit 2.5.2
    StatevectorEstimator PUB and validates evaluation.
    """
    vqc = build_vqc_circuit()
    obs = build_ensemble_z_observable()
    estimator = StatevectorEstimator()

    batch_x = np.full((3, 6), np.pi / 2.0)
    theta = np.zeros(12)

    pub_params = format_pub_parameters(batch_x, theta)
    pub = (vqc, obs, pub_params)

    job = estimator.run([pub])
    result = job.result()
    evs = result[0].data.evs

    assert isinstance(evs, np.ndarray)
    assert evs.shape == (3,)
    # At x = pi/2 and theta = 0, state is equal superposition, expectation value is 0.0
    np.testing.assert_allclose(evs, 0.0, atol=1e-12)


# ============================================================================
# STEP 6 TESTS: Expectation-to-Probability Readout Mapping Invariants
# ============================================================================

def test_expectation_to_probability_exact_mappings():
    """
    Verifies the canonical affine transformation p = (E + 1) / 2 for benchmark expectations:
    - E = -1.0 -> p = 0.00
    - E = -0.5 -> p = 0.25
    - E =  0.0 -> p = 0.50
    - E = +0.5 -> p = 0.75
    - E = +1.0 -> p = 1.00
    """
    assert np.isclose(expectation_to_probability(-1.0), 0.00, atol=1e-12)
    assert np.isclose(expectation_to_probability(-0.5), 0.25, atol=1e-12)
    assert np.isclose(expectation_to_probability(0.0), 0.50, atol=1e-12)
    assert np.isclose(expectation_to_probability(0.5), 0.75, atol=1e-12)
    assert np.isclose(expectation_to_probability(1.0), 1.00, atol=1e-12)


def test_expectation_to_probability_scalar_and_array_shapes():
    """
    Verifies that expectation_to_probability preserves caller rank and shape:
    - Scalar float returns Python float
    - Scalar int returns Python float
    - 0D array returns Python float
    - 1D array returns 1D float64 array of identical shape
    - 2D array returns 2D float64 array of identical shape
    """
    # 1. Scalar float
    p_float = expectation_to_probability(0.0)
    assert isinstance(p_float, float)
    assert np.isclose(p_float, 0.5)

    # 2. Scalar int
    p_int = expectation_to_probability(1)
    assert isinstance(p_int, float)
    assert np.isclose(p_int, 1.0)

    # 3. 0D array
    p_0d = expectation_to_probability(np.array(-1.0))
    assert isinstance(p_0d, float)
    assert np.isclose(p_0d, 0.0)

    # 4. 1D array
    arr_1d = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])
    p_1d = expectation_to_probability(arr_1d)
    assert isinstance(p_1d, np.ndarray)
    assert p_1d.shape == (5,)
    assert p_1d.dtype == np.float64
    np.testing.assert_allclose(p_1d, [0.0, 0.25, 0.5, 0.75, 1.0], atol=1e-12)

    # 5. 2D array
    arr_2d = np.array([[-1.0, 0.0], [0.5, 1.0]])
    p_2d = expectation_to_probability(arr_2d)
    assert isinstance(p_2d, np.ndarray)
    assert p_2d.shape == (2, 2)
    assert p_2d.dtype == np.float64
    np.testing.assert_allclose(p_2d, [[0.0, 0.5], [0.75, 1.0]], atol=1e-12)


def test_expectation_to_probability_tolerance_boundary_clipping():
    """
    Verifies that slight floating point noise within tolerance is safely clipped:
    - 1.0 + 1e-7 -> clipped to 1.0 -> p = 1.0
    - -1.0 - 1e-7 -> clipped to -1.0 -> p = 0.0
    """
    tol = 1e-6
    p_upper = expectation_to_probability(1.0 + 1e-7, tolerance=tol)
    assert isinstance(p_upper, float)
    assert np.isclose(p_upper, 1.0, atol=1e-12)

    p_lower = expectation_to_probability(-1.0 - 1e-7, tolerance=tol)
    assert isinstance(p_lower, float)
    assert np.isclose(p_lower, 0.0, atol=1e-12)


def test_expectation_to_probability_out_of_range_rejection():
    """
    Verifies that expectation values beyond [-1 - tol, +1 + tol] raise ValueError.
    """
    # Exceeds upper bound
    with pytest.raises(ValueError, match="Expectation values must lie within"):
        expectation_to_probability(1.05)

    with pytest.raises(ValueError, match="Expectation values must lie within"):
        expectation_to_probability(2.0)

    # Exceeds lower bound
    with pytest.raises(ValueError, match="Expectation values must lie within"):
        expectation_to_probability(-1.05)

    with pytest.raises(ValueError, match="Expectation values must lie within"):
        expectation_to_probability(-3.0)

    # Array containing out-of-range value
    with pytest.raises(ValueError, match="Expectation values must lie within"):
        expectation_to_probability(np.array([0.0, 1.5, -0.2]))


def test_expectation_to_probability_nan_and_inf_rejection():
    """
    Verifies that NaN, +Inf, and -Inf values raise ValueError.
    """
    with pytest.raises(ValueError, match="contains NaN or infinite values"):
        expectation_to_probability(np.nan)

    with pytest.raises(ValueError, match="contains NaN or infinite values"):
        expectation_to_probability(np.inf)

    with pytest.raises(ValueError, match="contains NaN or infinite values"):
        expectation_to_probability(-np.inf)

    with pytest.raises(ValueError, match="contains NaN or infinite values"):
        expectation_to_probability(np.array([0.1, np.nan, 0.5]))


def test_expectation_to_probability_empty_array_rejection():
    """
    Verifies that empty arrays raise ValueError.
    """
    with pytest.raises(ValueError, match="array must not be empty"):
        expectation_to_probability(np.array([]))


def test_expectation_to_probability_decision_rule_consistency():
    """
    Verifies the team-approved binary decision boundary:
    - p < 0.5 -> Class 0 (Normal beat, N)
    - p >= 0.5 -> Class 1 (Ventricular Ectopic Beat, VEB / V)
    """
    # Negative expectations -> Normal sinus beats
    assert expectation_to_probability(-0.01) < 0.5
    assert expectation_to_probability(-0.99) < 0.5

    # Positive or zero expectations -> VEB
    assert expectation_to_probability(0.00) >= 0.5
    assert expectation_to_probability(0.01) >= 0.5
    assert expectation_to_probability(0.99) >= 0.5


def test_vqc_circuit_bundle_assembly():
    """
    Verifies complete end-to-end VQCCircuitBundle assembly across all 6 milestone steps:
    1. Parameter vectors
    2. Feature map
    3. Variational ansatz
    4. Composite circuit
    5. Observable
    """
    p_enc, p_var = create_parameter_vectors()
    qc_enc = build_feature_map(p_enc)
    ansatz = build_ansatz(p_var)
    vqc = build_vqc_circuit(qc_enc=qc_enc, ansatz=ansatz)
    obs = build_ensemble_z_observable()

    bundle = VQCCircuitBundle(
        circuit=vqc,
        feature_map=qc_enc,
        ansatz=ansatz,
        encoding_params=p_enc,
        variational_params=p_var,
        observable=obs,
    )

    assert bundle.circuit.num_qubits == NUM_QUBITS
    assert bundle.circuit.num_parameters == TOTAL_CIRCUIT_PARAMS
    assert bundle.feature_map.depth() == 1
    assert bundle.ansatz.depth() == 7
    assert bundle.circuit.depth() == 8
    assert bundle.observable.num_qubits == NUM_QUBITS
    assert len(bundle.observable) == NUM_QUBITS
