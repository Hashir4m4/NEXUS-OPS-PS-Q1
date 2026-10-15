# NEXUS-OPS — MILESTONE 5F.2 STEP 5 IMPLEMENTATION REVIEW
## PUB Parameter Alignment Helper (`format_pub_parameters`)

**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Competition / Context:** IBM Quantum Qiskit Fall Fest 2026  
**Milestone:** 5F.2 — Core VQC Circuit Module (Step 5: PUB Parameter Alignment Helper)  
**Date:** 13 October 2026  
**Status:** IMPLEMENTED & VERIFIED — PENDING TECHNICAL LEAD APPROVAL  
**Module:** `src/vqc_circuit.py`  
**Test Suite:** `tests/test_vqc_circuit.py`  

---

## 1. Executive Summary

In accordance with technical lead authorization for Milestone 5F.2, **Step 5** has been implemented in [`src/vqc_circuit.py`](../src/vqc_circuit.py).

Step 5 introduces the vectorized Primitive Unified Bloc (PUB) parameter alignment helper:
```python
def format_pub_parameters(
    batch_x: Union[np.ndarray, List[float], List[List[float]]],
    theta: Union[np.ndarray, List[float]],
    num_features: int = NUM_ENCODING_PARAMS,
    num_weights: int = NUM_VARIATIONAL_PARAMS,
) -> np.ndarray:
```

This helper constructs the contiguous 2D parameter value array required by Qiskit Primitive V2 interfaces (`StatevectorEstimator` for ideal simulation and `EstimatorV2` for shot-based execution).

Key verified properties:
- **Exact Shape Layout:** Strictly $(N, 18)$ for $N \ge 1$ samples. Single sample 1D inputs $(6,)$ are promoted to $(1, 18)$.
- **Strict Parameter Ordering:** Columns $0 \dots 5$ match $p_{\text{enc}}[0 \dots 5]$ (features); columns $6 \dots 17$ match $p_{\text{var}}[0 \dots 11]$ (variational weights).
- **Memory & Dtype Specification:** Strictly `np.float64` with C-contiguous layout (`flags.c_contiguous == True`).
- **Input Immutability:** Never mutates caller-provided input arrays in-place.
- **Robust Input Validation:** Rejects NaN, $\pm\infty$, empty batches ($N=0$), mismatched feature dimensions ($\neq 6$), and mismatched weight lengths ($\neq 12$) with explicit `ValueError` or `TypeError`.
- **Primitive V2 PUB Integration:** Empirically verified end-to-end with both `StatevectorEstimator` and `qiskit_aer.primitives.EstimatorV2`.
- **Test Execution:** 28 focused unit tests passed; 1 future stub skipped; 76 full project tests passed (0 failures).

---

## 2. Mathematical Definition & PUB Parameter Layout

In Qiskit 2.5.2 Primitive V2, an Estimator PUB (Primitive Unified Bloc) has the standard tuple format:
$$\text{PUB} = (\text{circuit}, \text{observable}, \text{parameter\_values})$$

For the composite 6-qubit VQC circuit $U_{\text{VQC}}(\mathbf{x}, \boldsymbol{\theta})$:
- Total parameters = 18.
- The parameter ordering enforced by prefix hygiene is:
  $$\mathbf{P} = \left[ p_{\text{enc}}[0], \dots, p_{\text{enc}}[5], p_{\text{var}}[0], \dots, p_{\text{var}}[11] \right]$$

### 2.1 Parameter Matrix Structure

Given a batch of $N$ scaled ECG feature vectors $\mathbf{X} \in \mathbb{R}^{N \times 6}$ and a single variational weight vector $\boldsymbol{\theta} \in \mathbb{R}^{12}$, `format_pub_parameters` constructs:

$$\mathbf{\Theta}_{\text{PUB}} = \left[ \mathbf{X} \;\Big|\; \mathbf{1}_N \otimes \boldsymbol{\theta}^T \right] \in \mathbb{R}^{N \times 18}$$

$$\mathbf{\Theta}_{\text{PUB}} = \begin{bmatrix}
x_{0,0} & \dots & x_{0,5} & \theta_0 & \dots & \theta_{11} \\
x_{1,0} & \dots & x_{1,5} & \theta_0 & \dots & \theta_{11} \\
\vdots & \ddots & \vdots & \vdots & \ddots & \vdots \\
x_{N-1,0} & \dots & x_{N-1,5} & \theta_0 & \dots & \theta_{11}
\end{bmatrix}$$

### 2.2 Column-to-Parameter Correspondence

| Column Index | Parameter Name | Physical Source | Value in Row $k$ |
| :---: | :---: | :---: | :---: |
| 0 | `p_enc[0]` | Feature 0 ($QRS\_duration$) | $x_{k,0} \in [0, \pi]$ |
| 1 | `p_enc[1]` | Feature 1 ($P\_wave\_amplitude$) | $x_{k,1} \in [0, \pi]$ |
| 2 | `p_enc[2]` | Feature 2 ($T\_wave\_amplitude$) | $x_{k,2} \in [0, \pi]$ |
| 3 | `p_enc[3]` | Feature 3 ($ST\_segment\_level$) | $x_{k,3} \in [0, \pi]$ |
| 4 | `p_enc[4]` | Feature 4 ($pre\_RR\_interval$) | $x_{k,4} \in [0, \pi]$ |
| 5 | `p_enc[5]` | Feature 5 ($post\_RR\_interval$) | $x_{k,5} \in [0, \pi]$ |
| 6–17 | `p_var[0..11]` | Variational weights | $\theta_0 \dots \theta_{11} \in \mathbb{R}$ |

---

## 3. Implementation Details

```python
def format_pub_parameters(
    batch_x: Union[np.ndarray, List[float], List[List[float]]],
    theta: Union[np.ndarray, List[float]],
    num_features: int = NUM_ENCODING_PARAMS,
    num_weights: int = NUM_VARIATIONAL_PARAMS,
) -> np.ndarray:
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
```

---

## 4. Qiskit Primitive V2 Compatibility Evidence

Both primary execution engines were tested with the output of `format_pub_parameters`:

### 4.1 `qiskit.primitives.StatevectorEstimator` (Ideal Statevector)

```python
vqc = build_vqc_circuit()
obs = build_ensemble_z_observable()
estimator = StatevectorEstimator()

batch_x = np.full((3, 6), np.pi / 2.0)
theta = np.zeros(12)

pub_params = format_pub_parameters(batch_x, theta)  # Shape (3, 18)
pub = (vqc, obs, pub_params)

job = estimator.run([pub])
result = job.result()
evs = result[0].data.evs  # Returns shape (3,) with values [0.0, 0.0, 0.0]
```
- **PUB format accepted:** `(QuantumCircuit, SparsePauliOp, np.ndarray)`
- **Output shape:** `(3,)` matching batch size $N=3$.

### 4.2 `qiskit_aer.primitives.EstimatorV2` (Shot-Based Aer Simulator)

```python
from qiskit_aer.primitives import EstimatorV2
aer_est = EstimatorV2()
job = aer_est.run([(vqc, obs, pub_params)])
res = job.result()
# Shape (3,) returned successfully
```
- Completely compatible without any reshaping or parameter dictionary construction.

---

## 5. Test Suite Execution Results

### 5.1 Focused Circuit Tests (`tests/test_vqc_circuit.py`)

Execution command:
```bash
.venv\Scripts\pytest -v tests/test_vqc_circuit.py
```

Output:
```text
tests/test_vqc_circuit.py::test_parameter_vectors_creation_and_prefixes PASSED [  3%]
tests/test_vqc_circuit.py::test_parameter_vectors_element_names PASSED   [  6%]
tests/test_vqc_circuit.py::test_feature_map_structure_and_gates PASSED   [ 10%]
tests/test_vqc_circuit.py::test_feature_map_statevector_separable_product_state PASSED [ 13%]
tests/test_vqc_circuit.py::test_ansatz_qubit_and_parameter_counts PASSED [ 17%]
tests/test_vqc_circuit.py::test_ansatz_gate_counts_and_measured_depth PASSED [ 20%]
tests/test_vqc_circuit.py::test_ansatz_linear_cnot_entanglement_cascade PASSED [ 24%]
tests/test_vqc_circuit.py::test_ansatz_parameters_match_p_var_instance PASSED [ 27%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_qubits_and_parameters PASSED [ 31%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_parameter_ordering PASSED [ 34%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_gate_counts_and_measured_depth PASSED [ 37%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_gate_execution_order PASSED [ 41%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_input_validation_and_errors PASSED [ 44%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_statevector_smoke_test PASSED [ 48%]
tests/test_vqc_circuit.py::test_observable_structure_and_weights PASSED  [ 51%]
tests/test_vqc_circuit.py::test_observable_hermiticity_and_eigenvalues PASSED [ 55%]
tests/test_vqc_circuit.py::test_observable_computational_basis_expectations PASSED [ 58%]
tests/test_vqc_circuit.py::test_observable_qubit_count_validation PASSED [ 62%]
tests/test_vqc_circuit.py::test_exact_analytic_statevector_edge_case PASSED [ 65%]
tests/test_vqc_circuit.py::test_format_pub_parameters_single_sample_shape_and_dtype PASSED [ 68%]
tests/test_vqc_circuit.py::test_format_pub_parameters_batch_shape_and_dtype PASSED [ 72%]
tests/test_vqc_circuit.py::test_format_pub_parameters_feature_and_weight_alignment PASSED [ 75%]
tests/test_vqc_circuit.py::test_format_pub_parameters_ordering_matches_circuit_parameters PASSED [ 79%]
tests/test_vqc_circuit.py::test_format_pub_parameters_invalid_dimensions PASSED [ 82%]
tests/test_vqc_circuit.py::test_format_pub_parameters_nan_and_inf_rejection PASSED [ 86%]
tests/test_vqc_circuit.py::test_format_pub_parameters_empty_batch_rejection PASSED [ 89%]
tests/test_vqc_circuit.py::test_format_pub_parameters_no_mutation_of_caller_inputs PASSED [ 93%]
tests/test_vqc_circuit.py::test_format_pub_parameters_qiskit_pub_integration PASSED [ 96%]
tests/test_vqc_circuit.py::test_expectation_to_probability_mapping SKIPPED [100%]

======================== 28 passed, 1 skipped in 2.79s ========================
```

### 5.2 Full Project Regression Suite

Execution command:
```bash
.venv\Scripts\pytest -q
```

Output:
```text
76 passed, 1 skipped in 10.57s
```
Zero regressions across all classical baseline, leak-free preprocessing, feature engineering, and circuit modules.

---

## 6. Strict Scope & Governance Compliance Checklist

| Scope / Governance Requirement | Status | Evidence |
| :--- | :---: | :--- |
| Implement Step 5 (`format_pub_parameters`) only | **PASSED** | Step 6 remains stub with `NotImplementedError` |
| Exact parameter ordering matches `circuit.parameters` | **PASSED** | Verified in `test_format_pub_parameters_ordering_matches_circuit_parameters` |
| Output shape strictly $(N, 18)$ | **PASSED** | Verified for $N=1$ and $N > 1$ |
| Dtype strictly `np.float64`, C-contiguous | **PASSED** | Verified in dedicated unit tests |
| Robust validation (NaN, Inf, empty, dimension mismatch) | **PASSED** | 5 validation unit tests passing |
| Caller input immutability | **PASSED** | Verified in `test_format_pub_parameters_no_mutation_of_caller_inputs` |
| No modifications to datasets or baselines | **PASSED** | Confirmed via `git status` |
| No commits or pushes performed | **PASSED** | Awaiting technical lead authorization |

---

## 7. Handover & Recommendation for Step 6

Step 5 is complete, fully tested, and ready for technical lead review.

Upon technical lead approval, **Step 6** will implement:
- `expectation_to_probability(expectation_values)`: Linear readout mapping $p(\text{VEB}) = \frac{\langle \bar{Z} \rangle + 1}{2}$, mapping $[-1.0, +1.0] \rightarrow [0.0, 1.0]$ with clipping/numerical guardrails and comprehensive unit tests.
