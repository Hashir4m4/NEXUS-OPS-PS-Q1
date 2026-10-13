"""
Core VQC Circuit Module
=======================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 5F.2)

Architecture (Frozen & Team-Approved):
--------------------------------------
- 6 Qubits (1:1 feature-to-qubit mapping)
- First-order RY angle encoding in [0, pi]
- RealAmplitudes ansatz with reps=1 and linear nearest-neighbor entanglement
- 12 Trainable variational parameters (initialized in U[-0.1, 0.1])
- Ensemble average of six local Pauli-Z observables (weight 1/6 each)
- Polarity: Positive expectation corresponds to VEB (class 1); p(VEB) = (E + 1) / 2
- Target execution: Qiskit 2.5.2 StatevectorEstimator (training) and Aer 0.17.2 EstimatorV2 (shots)

Module Safeguards:
------------------
1. Independent ParameterVectors with prefix hygiene ('p_enc' and 'p_var')
   to enforce deterministic alphabetical sorting in Qiskit circuit.parameters.
2. Runtime assertion verifying circuit.parameters matches [p_enc] + [p_var].
3. SparsePauliOp.from_sparse_list avoiding Pauli string endianness hazards.
4. Pure circuit definitions decoupled from optimizers, loss, or training loops.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from qiskit.circuit import Parameter, ParameterVector, QuantumCircuit
from qiskit.circuit.library import real_amplitudes
from qiskit.quantum_info import SparsePauliOp

# Physical and architectural constants
NUM_QUBITS: int = 6
NUM_ENCODING_PARAMS: int = 6
NUM_VARIATIONAL_PARAMS: int = 12
TOTAL_CIRCUIT_PARAMS: int = 18

ENCODING_PREFIX: str = "p_enc"
VARIATIONAL_PREFIX: str = "p_var"


@dataclass(frozen=True)
class VQCCircuitBundle:
    """
    Container holding the assembled composite VQC circuit, its component
    circuits, parameter vectors, and the global readout observable.
    """
    circuit: QuantumCircuit
    feature_map: QuantumCircuit
    ansatz: QuantumCircuit
    encoding_params: ParameterVector
    variational_params: ParameterVector
    observable: SparsePauliOp


# ============================================================================
# STEP 1: Parameter Vector Definitions & Feature Map Builder
# ============================================================================

def create_parameter_vectors(
    num_features: int = NUM_ENCODING_PARAMS,
    num_weights: int = NUM_VARIATIONAL_PARAMS,
) -> Tuple[ParameterVector, ParameterVector]:
    """
    Creates two independent ParameterVectors for feature encoding and variational weights.

    Prefix Hygiene Safeguard:
    -------------------------
    In Qiskit, circuit.parameters sorts Parameter objects alphabetically by name.
    We enforce prefixes 'p_enc' and 'p_var'. Because 'p_enc' < 'p_var' in ASCII,
    Qiskit's internal parameter list is mathematically guaranteed to place all
    encoding parameters at indices 0..5 and all variational parameters at indices 6..17.

    Parameters
    ----------
    num_features : int
        Number of continuous input features (default: 6).
    num_weights : int
        Number of variational trainable parameters (default: 12).

    Returns
    -------
    Tuple[ParameterVector, ParameterVector]
        (p_enc, p_var)
    """
    if ENCODING_PREFIX >= VARIATIONAL_PREFIX:
        raise ValueError(
            f"Alphabetical prefix violation: '{ENCODING_PREFIX}' must precede '{VARIATIONAL_PREFIX}' "
            "to guarantee deterministic parameter sorting in Qiskit."
        )

    p_enc = ParameterVector(ENCODING_PREFIX, length=num_features)
    p_var = ParameterVector(VARIATIONAL_PREFIX, length=num_weights)

    return p_enc, p_var


def build_feature_map(
    p_enc: Optional[ParameterVector] = None,
    num_qubits: int = NUM_QUBITS,
) -> QuantumCircuit:
    """
    Constructs the first-order RY feature encoding circuit U_Phi(x).

    Mathematical Operation:
    -----------------------
    U_Phi(x) = \\bigotimes_{i=0}^5 R_y(x_i)
    Maps each scaled physiological feature x_i in [0, pi] to qubit i:
    R_y(x_i)|0> = cos(x_i / 2)|0> + sin(x_i / 2)|1>

    Properties:
    -----------
    - Theoretical gate count: exactly 6 single-qubit Ry gates.
    - Two-qubit entangling gates: exactly 0 (separable product state).
    - Theoretical circuit depth: exactly 1.
    - Purely real probability amplitudes (amplitudes in R^64).

    Parameters
    ----------
    p_enc : Optional[ParameterVector]
        ParameterVector of length 6. If None, created automatically.
    num_qubits : int
        Number of qubits (default: 6).

    Returns
    -------
    QuantumCircuit
        Feature map circuit with 6 parameters and 6 Ry gates.
    """
    if p_enc is None:
        p_enc, _ = create_parameter_vectors(num_features=num_qubits)

    if len(p_enc) != num_qubits:
        raise ValueError(f"Feature vector length ({len(p_enc)}) must equal num_qubits ({num_qubits}).")

    qc_enc = QuantumCircuit(num_qubits, name="FeatureMap")
    for i in range(num_qubits):
        qc_enc.ry(p_enc[i], i)

    # Invariant assertions
    assert qc_enc.num_qubits == num_qubits, "Feature map qubit count mismatch."
    assert qc_enc.num_parameters == num_qubits, "Feature map parameter count mismatch."
    assert qc_enc.depth() == 1, "Feature map depth must be exactly 1."

    return qc_enc


# ============================================================================
# STEP 2: Variational Ansatz Builder (RealAmplitudes, reps=1, linear)
# ============================================================================

def build_ansatz(
    p_var: Optional[ParameterVector] = None,
    num_qubits: int = NUM_QUBITS,
    reps: int = 1,
    entanglement: str = "linear",
) -> QuantumCircuit:
    """
    Constructs the RealAmplitudes variational ansatz W(theta) using Qiskit's functional API.

    Mathematical Structure:
    -----------------------
    W(theta) = R^(2)(theta_6:12) . U_ent . R^(1)(theta_0:6)
    - R^(1): 6 Ry gates (theta_0 .. theta_5)
    - U_ent: 5 CX gates with nearest-neighbor linear topology: (0,1), (1,2), (2,3), (3,4), (4,5)
    - R^(2): 6 Ry gates (theta_6 .. theta_11)

    Measured Invariants (reps=1, num_qubits=6, entanglement='linear'):
    ------------------------------------------------------------------
    - Qubit count: 6
    - Parameter count: 6 * (1 + 1) = 12
    - Gate counts: 12 Ry gates, 5 CX gates
    - Measured untranspiled circuit depth: 7 (1 rot layer + 5 sequential CX gates + 1 rot layer)

    Parameters
    ----------
    p_var : Optional[ParameterVector]
        ParameterVector of length 12. If None, created automatically.
    num_qubits : int
        Number of qubits (default: 6).
    reps : int
        Number of entangling repetitions (default: 1).
    entanglement : str
        Entanglement topology (default: 'linear').

    Returns
    -------
    QuantumCircuit
        Variational ansatz circuit with 12 parameters, 12 Ry gates, 5 CX gates, and depth 7.
    """
    num_weights = num_qubits * (reps + 1)

    if p_var is None:
        _, p_var = create_parameter_vectors(num_features=num_qubits, num_weights=num_weights)
    elif len(p_var) != num_weights:
        raise ValueError(
            f"Variational vector length ({len(p_var)}) must equal expected parameter count ({num_weights})."
        )

    # Construct ansatz using Qiskit 2.5.2 functional API
    ansatz = real_amplitudes(
        num_qubits=num_qubits,
        entanglement=entanglement,
        reps=reps,
        parameter_prefix=VARIATIONAL_PREFIX,
        name="RealAmplitudes",
    )

    # Explicitly bind the approved p_var ParameterVector instance
    ansatz = ansatz.assign_parameters(dict(zip(ansatz.parameters, p_var)))

    # Invariant assertions
    assert ansatz.num_qubits == num_qubits, "Ansatz qubit count mismatch."
    assert ansatz.num_parameters == num_weights, "Ansatz parameter count mismatch."
    ops = dict(ansatz.count_ops())
    assert ops.get("ry", 0) == num_weights, f"Expected {num_weights} Ry gates, got {ops.get('ry', 0)}"
    assert ops.get("cx", 0) == num_qubits - 1, f"Expected {num_qubits - 1} CX gates, got {ops.get('cx', 0)}"
    # Measured depth invariant: 1 (rot1) + (num_qubits - 1) (linear CX cascade) + 1 (rot2) = 7
    assert ansatz.depth() == 7, f"Measured ansatz depth mismatch: expected 7, got {ansatz.depth()}"
    assert list(ansatz.parameters) == list(p_var), "Ansatz parameters must match p_var vector."

    return ansatz


# ============================================================================
# STEP 3: Composite Parameterized VQC Circuit Builder
# ============================================================================

def build_vqc_circuit(
    p_enc: Optional[Union[ParameterVector, QuantumCircuit]] = None,
    p_var: Optional[Union[ParameterVector, QuantumCircuit]] = None,
    qc_enc: Optional[QuantumCircuit] = None,
    ansatz: Optional[QuantumCircuit] = None,
    num_qubits: int = NUM_QUBITS,
) -> QuantumCircuit:
    """
    Constructs the composite parameterized VQC circuit U_VQC(x, theta).

    Mathematical Formulation:
    --------------------------
    U_VQC(x, theta) = W(theta) . U_Phi(x)
    Operating on the all-zero reference state |0>^6:
        |psi(x, theta)> = W(theta) U_Phi(x) |0>^6

    Composition Order:
    ------------------
    1. Feature encoding U_Phi(x) is applied first (Layer depth: 1, 6 Ry gates).
    2. Variational ansatz W(theta) is applied second (Layer depth: 7, 12 Ry + 5 CX gates).

    Parameter Sorting Safeguard:
    ----------------------------
    In Qiskit, circuit.parameters sorts Parameter instances alphabetically by name.
    Because ENCODING_PREFIX ('p_enc') alphabetically precedes VARIATIONAL_PREFIX ('p_var'),
    the parameters are deterministically ordered as:
        [p_enc[0], ..., p_enc[5], p_var[0], ..., p_var[11]]
    This runtime ordering is explicitly verified before returning.

    Measured Empirical Invariants:
    ------------------------------
    - Qubit count: exactly 6
    - Total parameters: exactly 18 (6 encoding + 12 variational)
    - Gate counts: 18 Ry single-qubit gates, 5 CX two-qubit gates (23 total gates)
    - Measured untranspiled circuit depth: exactly 8

    Parameters
    ----------
    p_enc : Optional[Union[ParameterVector, QuantumCircuit]]
        Encoding ParameterVector (length 6) or pre-built feature map circuit.
    p_var : Optional[Union[ParameterVector, QuantumCircuit]]
        Variational ParameterVector (length 12) or pre-built ansatz circuit.
    qc_enc : Optional[QuantumCircuit]
        Optional explicit feature map circuit.
    ansatz : Optional[QuantumCircuit]
        Optional explicit ansatz circuit.
    num_qubits : int
        Number of qubits (default: 6).

    Returns
    -------
    QuantumCircuit
        Composite parameterized circuit named 'VQC_Biomedical'.
    """
    # 1. Resolve feature encoding circuit
    if qc_enc is not None:
        if not isinstance(qc_enc, QuantumCircuit):
            raise TypeError(f"qc_enc must be a QuantumCircuit, got {type(qc_enc).__name__}.")
    elif isinstance(p_enc, QuantumCircuit):
        qc_enc = p_enc
        p_enc = None
    elif isinstance(p_enc, ParameterVector):
        if len(p_enc) != num_qubits:
            raise ValueError(
                f"Encoding parameter vector length ({len(p_enc)}) must match num_qubits ({num_qubits})."
            )
        qc_enc = build_feature_map(p_enc, num_qubits=num_qubits)
    elif p_enc is None:
        p_enc_default, _ = create_parameter_vectors(num_features=num_qubits)
        qc_enc = build_feature_map(p_enc_default, num_qubits=num_qubits)
    else:
        raise TypeError(
            f"Expected p_enc to be ParameterVector, QuantumCircuit, or None, got {type(p_enc).__name__}."
        )

    # 2. Resolve variational ansatz circuit
    expected_weights = num_qubits * 2  # reps=1 -> 12 parameters
    if ansatz is not None:
        if not isinstance(ansatz, QuantumCircuit):
            raise TypeError(f"ansatz must be a QuantumCircuit, got {type(ansatz).__name__}.")
    elif isinstance(p_var, QuantumCircuit):
        ansatz = p_var
        p_var = None
    elif isinstance(p_var, ParameterVector):
        if len(p_var) != expected_weights:
            raise ValueError(
                f"Variational parameter vector length ({len(p_var)}) must equal expected weights ({expected_weights})."
            )
        ansatz = build_ansatz(p_var, num_qubits=num_qubits)
    elif p_var is None:
        _, p_var_default = create_parameter_vectors(num_features=num_qubits, num_weights=expected_weights)
        ansatz = build_ansatz(p_var_default, num_qubits=num_qubits)
    else:
        raise TypeError(
            f"Expected p_var to be ParameterVector, QuantumCircuit, or None, got {type(p_var).__name__}."
        )

    # 3. Validate circuit compatibility
    if qc_enc.num_qubits != num_qubits:
        raise ValueError(
            f"Feature map qubit count ({qc_enc.num_qubits}) does not match expected num_qubits ({num_qubits})."
        )
    if ansatz.num_qubits != num_qubits:
        raise ValueError(
            f"Ansatz qubit count ({ansatz.num_qubits}) does not match expected num_qubits ({num_qubits})."
        )

    # 4. Compose circuits: feature map first, ansatz second
    vqc = QuantumCircuit(num_qubits, name="VQC_Biomedical")
    vqc.compose(qc_enc, inplace=True)
    vqc.compose(ansatz, inplace=True)

    # 5. Invariant assertions
    assert vqc.num_qubits == num_qubits, "Composite circuit qubit count mismatch."
    assert vqc.num_parameters == NUM_ENCODING_PARAMS + NUM_VARIATIONAL_PARAMS, (
        f"Composite circuit parameter count mismatch: expected {NUM_ENCODING_PARAMS + NUM_VARIATIONAL_PARAMS}, "
        f"got {vqc.num_parameters}."
    )

    # 6. Parameter ordering safeguard
    param_names = [p.name for p in vqc.parameters]
    expected_enc_names = [f"{ENCODING_PREFIX}[{i}]" for i in range(NUM_ENCODING_PARAMS)]
    expected_var_names = [f"{VARIATIONAL_PREFIX}[{i}]" for i in range(NUM_VARIATIONAL_PARAMS)]
    expected_names = expected_enc_names + expected_var_names

    if param_names != expected_names:
        raise RuntimeError(
            f"Parameter ordering violation in composite VQC circuit!\n"
            f"Expected ordering: {expected_names}\n"
            f"Actual ordering:   {param_names}"
        )

    # 7. Gate counts & depth invariants
    ops = dict(vqc.count_ops())
    expected_ry = qc_enc.count_ops().get("ry", 0) + ansatz.count_ops().get("ry", 0)
    expected_cx = qc_enc.count_ops().get("cx", 0) + ansatz.count_ops().get("cx", 0)
    assert ops.get("ry", 0) == expected_ry, f"Expected {expected_ry} Ry gates, got {ops.get('ry', 0)}"
    assert ops.get("cx", 0) == expected_cx, f"Expected {expected_cx} CX gates, got {ops.get('cx', 0)}"

    measured_depth = vqc.depth()
    assert measured_depth == 8, f"Measured composite circuit depth mismatch: expected 8, got {measured_depth}"

    return vqc


# ============================================================================
# STEP 4: Six-Qubit Average Pauli-Z Observable Builder
# ============================================================================

def build_ensemble_z_observable(
    num_qubits: int = NUM_QUBITS,
) -> SparsePauliOp:
    """
    Constructs the ensemble average Pauli-Z observable using SparsePauliOp.from_sparse_list.

    Mathematical Formulation:
    --------------------------
    O = (1 / num_qubits) * \\sum_{i=0}^{num_qubits - 1} Z_i

    Properties:
    -----------
    - Hermitian: O^\\dagger = O
    - Bounded spectrum: eigenvalues \\lambda \\in [-1, +1]
    - Computational basis extrema:
        <000000| O |000000> = +1.0
        <111111| O |111111> = -1.0
        <s| O |s> = 0.0 for any basis state with equal count of 0s and 1s
    - Endianness-safe: constructed via SparsePauliOp.from_sparse_list, explicitly
      binding ('Z', [i], 1.0 / num_qubits) to qubit index i.

    Parameters
    ----------
    num_qubits : int
        Number of qubits for the observable (default: 6).

    Returns
    -------
    SparsePauliOp
        Ensemble average Pauli-Z observable with 6 terms of weight 1/6.
    """
    if not isinstance(num_qubits, int) or num_qubits <= 0:
        raise ValueError(f"num_qubits must be a positive integer, got {num_qubits}.")
    if num_qubits != NUM_QUBITS:
        raise ValueError(
            f"Unsupported qubit count {num_qubits}. Approved VQC architecture requires {NUM_QUBITS} qubits."
        )

    weight = 1.0 / float(num_qubits)
    sparse_list = [("Z", [i], weight) for i in range(num_qubits)]
    observable = SparsePauliOp.from_sparse_list(sparse_list, num_qubits=num_qubits)

    # Invariant assertions
    assert observable.num_qubits == num_qubits, "Observable qubit count mismatch."
    assert len(observable) == num_qubits, f"Expected {num_qubits} Pauli terms, got {len(observable)}."
    assert np.allclose(observable.coeffs.real, weight), f"All coefficients must equal {weight}."
    assert np.allclose(observable.coeffs.imag, 0.0), "Observable coefficients must be purely real."

    return observable


# ============================================================================
# STEP 5: PUB Parameter Array Alignment Helper
# ============================================================================

def format_pub_parameters(
    batch_x: Union[np.ndarray, List[float], List[List[float]]],
    theta: Union[np.ndarray, List[float]],
    num_features: int = NUM_ENCODING_PARAMS,
    num_weights: int = NUM_VARIATIONAL_PARAMS,
) -> np.ndarray:
    """
    Aligns input ECG features and trainable variational weights into a contiguous 2D
    NumPy array formatted for Qiskit Primitive V2 Primitive Unified Blocs (PUBs).

    PUB Parameter Layout:
    ---------------------
    The composite circuit parameters are deterministically ordered as:
        [p_enc[0], ..., p_enc[5], p_var[0], ..., p_var[11]]
    This function packs batch features and weights into shape (N, 18):
        - Columns 0..5:  Encoding parameters p_enc[0..5] (sample features)
        - Columns 6..17: Variational parameters p_var[0..11] (tiled model weights)

    Shape Conventions:
    ------------------
    - batch_x:
        - 1D array of shape (6,) -> treated as a single sample (N=1)
        - 2D array of shape (N, 6) -> batch of N samples
    - theta:
        - 1D array of shape (12,) or 2D array of shape (1, 12)
    - Output:
        - Strictly 2D array of shape (N, 18)
        - dtype: np.float64, C-contiguous memory layout

    Validation Guarantees:
    ----------------------
    - Rejects non-finite values (NaN, +Inf, -Inf) with ValueError.
    - Rejects empty batches (N=0) with ValueError.
    - Rejects mismatched dimensions (num_features != 6 or num_weights != 12) with ValueError.
    - Rejects higher-dimensional arrays (ndim > 2) with ValueError.
    - Preserves input immutability: copies caller inputs and never mutates in-place.

    Parameters
    ----------
    batch_x : Union[np.ndarray, List[float], List[List[float]]]
        Continuous feature input: shape (6,) or (N, 6).
    theta : Union[np.ndarray, List[float]]
        Trainable variational weights: shape (12,) or (1, 12).
    num_features : int
        Expected number of encoding features (default: 6).
    num_weights : int
        Expected number of variational parameters (default: 12).

    Returns
    -------
    np.ndarray
        Contiguous 2D array of shape (N, 18) with dtype np.float64.
    """
    # 1. Convert to numpy arrays without mutating caller inputs
    try:
        X_arr = np.asarray(batch_x, dtype=np.float64)
    except (ValueError, TypeError) as err:
        raise TypeError(f"Could not convert batch_x to float64 array: {err}") from err

    try:
        theta_arr = np.asarray(theta, dtype=np.float64)
    except (ValueError, TypeError) as err:
        raise TypeError(f"Could not convert theta to float64 array: {err}") from err

    # 2. Check for empty inputs
    if X_arr.size == 0:
        raise ValueError("batch_x must not be empty (at least 1 sample required).")
    if theta_arr.size == 0:
        raise ValueError("theta must not be empty (trainable weights required).")

    # 3. Check for non-finite values (NaN, Inf)
    if not np.all(np.isfinite(X_arr)):
        raise ValueError("batch_x contains NaN or infinite values; all features must be finite real numbers.")
    if not np.all(np.isfinite(theta_arr)):
        raise ValueError("theta contains NaN or infinite values; all variational weights must be finite real numbers.")

    # 4. Validate and reshape batch_x
    if X_arr.ndim == 1:
        if X_arr.shape[0] != num_features:
            raise ValueError(
                f"1D batch_x must have shape ({num_features},), got shape {X_arr.shape}."
            )
        X_mat = X_arr.reshape(1, num_features)
    elif X_arr.ndim == 2:
        if X_arr.shape[1] != num_features:
            raise ValueError(
                f"2D batch_x feature dimension must be {num_features}, got {X_arr.shape[1]} (shape {X_arr.shape})."
            )
        if X_arr.shape[0] == 0:
            raise ValueError("2D batch_x must contain at least 1 sample row.")
        X_mat = X_arr
    else:
        raise ValueError(
            f"batch_x must be 1D or 2D, got {X_arr.ndim}D array with shape {X_arr.shape}."
        )

    # 5. Validate and reshape theta
    if theta_arr.ndim == 1:
        if theta_arr.shape[0] != num_weights:
            raise ValueError(
                f"1D theta must have shape ({num_weights},), got shape {theta_arr.shape}."
            )
        theta_row = theta_arr.reshape(1, num_weights)
    elif theta_arr.ndim == 2:
        if theta_arr.shape != (1, num_weights):
            raise ValueError(
                f"2D theta must have shape (1, {num_weights}), got shape {theta_arr.shape}."
            )
        theta_row = theta_arr
    else:
        raise ValueError(
            f"theta must be 1D or 2D, got {theta_arr.ndim}D array with shape {theta_arr.shape}."
        )

    # 6. Assemble into contiguous 2D array of shape (N, num_features + num_weights)
    n_samples = X_mat.shape[0]
    theta_tile = np.tile(theta_row, (n_samples, 1))
    packed = np.ascontiguousarray(np.hstack([X_mat, theta_tile]), dtype=np.float64)

    # 7. Invariant assertions
    total_params = num_features + num_weights
    assert packed.shape == (n_samples, total_params), f"Packed parameter shape mismatch: {packed.shape}"
    assert packed.dtype == np.float64, f"Packed dtype mismatch: {packed.dtype}"
    assert packed.flags.c_contiguous, "Packed array must be C-contiguous."

    return packed


# ============================================================================
# STEP 6: Expectation-to-Probability Readout Mapping
# ============================================================================

def expectation_to_probability(
    expectation_values: Union[float, int, np.ndarray, List[float]],
    tolerance: float = 1e-6,
) -> Union[float, np.ndarray]:
    """
    Maps continuous expectation values E in [-1, +1] to binary-class probabilities
    p(VEB) in [0, 1] using the approved linear affine transformation.

    Approved Mathematical Mapping:
    -------------------------------
    p(VEB) = (E + 1) / 2

    Decision Boundary & Polarity Convention:
    ----------------------------------------
    - E = -1.0 -> p = 0.00 (Pure Normal sinus beat)
    - E = -0.5 -> p = 0.25
    - E =  0.0 -> p = 0.50 (Decision boundary threshold)
    - E = +0.5 -> p = 0.75
    - E = +1.0 -> p = 1.00 (Pure Ventricular Ectopic Beat)

    Decision Rule:
    - p < 0.5  -> Class 0 (Normal beat, N)
    - p >= 0.5 -> Class 1 (Ventricular Ectopic Beat, VEB / V)

    Numerical Safeguards:
    ---------------------
    - Rejects non-finite inputs (NaN, +Inf, -Inf) with ValueError.
    - Validates that expectation values lie within [-1 - tol, +1 + tol].
      Values outside this range raise ValueError.
    - Numerical tolerance (default 1e-6) accommodates finite-precision floating-point
      inaccuracies (e.g. 1.0000000000000002). Within the tolerance interval, values
      are safely clipped to [-1.0, +1.0] before mapping, guaranteeing p in [0.0, 1.0].
    - Preserves input rank:
        - Scalar inputs (float, int, 0D array) return a Python float.
        - Array inputs (1D, 2D, or list) return an ndarray with matching shape and float64 dtype.

    Parameters
    ----------
    expectation_values : Union[float, int, np.ndarray, List[float]]
        Raw quantum expectation value(s) in [-1, +1].
    tolerance : float
        Numerical slack for floating-point boundary imprecision (default: 1e-6).

    Returns
    -------
    Union[float, np.ndarray]
        Mapped probability value(s) strictly bounded in [0.0, 1.0].
    """
    # 1. Determine whether input is scalar
    is_scalar = np.isscalar(expectation_values) or (
        isinstance(expectation_values, np.ndarray) and expectation_values.ndim == 0
    )

    # 2. Convert to float64 array for robust vectorized checks
    try:
        arr = np.asarray(expectation_values, dtype=np.float64)
    except (ValueError, TypeError) as err:
        raise TypeError(f"Could not convert expectation_values to float64: {err}") from err

    # 3. Check for empty inputs
    if arr.size == 0:
        raise ValueError("expectation_values array must not be empty.")

    # 4. Check for non-finite values (NaN, Inf)
    if not np.all(np.isfinite(arr)):
        raise ValueError("expectation_values contains NaN or infinite values; all inputs must be finite real numbers.")

    # 5. Range validation with numerical tolerance
    if np.any(arr < -1.0 - tolerance) or np.any(arr > 1.0 + tolerance):
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        raise ValueError(
            f"Expectation values must lie within [-1.0, +1.0] (tolerance={tolerance}), "
            f"got out-of-range values: min={min_val}, max={max_val}."
        )

    # 6. Clip slightly out-of-bounds values within tolerance to [-1.0, 1.0]
    clipped = np.clip(arr, -1.0, 1.0)

    # 7. Linear affine mapping: p = (E + 1) / 2
    probabilities = (clipped + 1.0) / 2.0

    # 8. Post-condition invariant assertion
    assert np.all(probabilities >= 0.0) and np.all(probabilities <= 1.0), (
        "Output probabilities must strictly lie in [0.0, 1.0]."
    )

    if is_scalar:
        return float(probabilities)
    return probabilities
