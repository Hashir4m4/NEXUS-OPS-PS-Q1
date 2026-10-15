# NEXUS-OPS — MILESTONE 5F.2 STEP 4 IMPLEMENTATION REVIEW
## Ensemble Average Pauli-Z Observable (`build_ensemble_z_observable`)

**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Competition / Context:** IBM Quantum Qiskit Fall Fest 2026  
**Milestone:** 5F.2 — Core VQC Circuit Module (Step 4: Observable Construction)  
**Date:** 13 October 2026  
**Status:** IMPLEMENTED & VERIFIED — PENDING TECHNICAL LEAD APPROVAL  
**Module:** `src/vqc_circuit.py`  
**Test Suite:** `tests/test_vqc_circuit.py`  

---

## 1. Executive Summary

In accordance with technical lead authorization for Milestone 5F.2, **Step 4** has been implemented in [`src/vqc_circuit.py`](../src/vqc_circuit.py).

Step 4 introduces the six-qubit ensemble average Pauli-Z observable builder:
```python
def build_ensemble_z_observable(
    num_qubits: int = NUM_QUBITS,
) -> SparsePauliOp:
```

This operator represents the primary readout observable $\bar{Z}$ approved in Decision **D4** of [`results/vqc_architecture_decisions.json`](../results/vqc_architecture_decisions.json).

Key structural and mathematical properties verified:
- **Operator type:** `qiskit.quantum_info.SparsePauliOp`.
- **Dimension:** Exactly 6 qubits ($2^6 = 64$ Hilbert space dimension).
- **Terms:** Exactly 6 single-qubit Pauli-$Z$ operators with no identities, $X$, or $Y$ terms.
- **Coefficients:** Uniformly $\frac{1}{6} \approx 0.16666667$, strictly real.
- **Endianness safety:** Constructed via `SparsePauliOp.from_sparse_list()` to prevent Pauli-string reversal errors.
- **Hermiticity:** $O^\dagger = O$ validated numerically ($M = M^\dagger$ with tolerance $10^{-12}$).
- **Spectral bounds:** Eigenvalues $\lambda \in [-1.0, +1.0]$.
- **Basis state expectations:**
  - $\langle 000000 | \bar{Z} | 000000 \rangle = +1.0$
  - $\langle 111111 | \bar{Z} | 111111 \rangle = -1.0$
  - Any balanced computational basis state (e.g., $|000111\rangle$, $|101010\rangle$) $\rightarrow 0.0$
- **Exact analytical edge case:** $\langle \bar{Z} \rangle_{\mathbf{x}=\pi, \boldsymbol{\theta}=\mathbf{0}} = 0.0$ verified on the full composite circuit $U_{\text{VQC}}$.
- **Test execution:** 19 focused VQC circuit unit tests passed; 2 future stubs skipped; 67 total project tests passed (0 failures).

---

## 2. Mathematical Definition & Spectral Analysis

### 2.1 Formal Operator Definition

The ensemble average Pauli-$Z$ observable $\bar{Z}$ is defined on the 6-qubit Hilbert space $\mathcal{H} = (\mathbb{C}^2)^{\otimes 6}$ as:

$$\bar{Z} = \frac{1}{6} \sum_{i=0}^5 Z_i$$

where $Z_i$ denotes the local Pauli-$Z$ operator acting non-trivially on qubit $i$ and trivially (identity $I$) on all other 5 qubits:

$$Z_i = I^{\otimes (5-i)} \otimes Z \otimes I^{\otimes i} \quad \text{(in physical qubit indexing)}$$

Explicitly expanded across the 6 qubits:
$$\bar{Z} = \frac{1}{6} \left( Z \otimes I \otimes I \otimes I \otimes I \otimes I + I \otimes Z \otimes I \otimes I \otimes I \otimes I + \dots + I \otimes I \otimes I \otimes I \otimes I \otimes Z \right)$$

### 2.2 Spectral Properties

Since Pauli-$Z$ has eigenvalues $\pm 1$:
$$Z |0\rangle = +1 |0\rangle, \quad Z |1\rangle = -1 |1\rangle$$

For any computational basis state $|\mathbf{s}\rangle = |s_5 s_4 s_3 s_2 s_1 s_0\rangle$ with bitstring $\mathbf{s} \in \{0, 1\}^6$:
$$\bar{Z} |\mathbf{s}\rangle = \left( \frac{1}{6} \sum_{i=0}^5 (-1)^{s_i} \right) |\mathbf{s}\rangle = \left( \frac{N_0(\mathbf{s}) - N_1(\mathbf{s})}{6} \right) |\mathbf{s}\rangle$$

where $N_0(\mathbf{s})$ is the number of zeros and $N_1(\mathbf{s})$ is the number of ones in the bitstring $\mathbf{s}$.

Because $N_0(\mathbf{s}) + N_1(\mathbf{s}) = 6$:
- Minimum eigenvalue: $\lambda_{\min} = \frac{0 - 6}{6} = -1.0$ (achieved uniquely by $|111111\rangle$).
- Maximum eigenvalue: $\lambda_{\max} = \frac{6 - 0}{6} = +1.0$ (achieved uniquely by $|000000\rangle$).
- Discrete spectrum: $\lambda \in \left\{ -1, -\frac{2}{3}, -\frac{1}{3}, 0, +\frac{1}{3}, +\frac{2}{3}, +1 \right\}$.
- Every eigenvalue is strictly real, confirming Hermiticity.

---

## 3. Implementation Details & Endianness Safeguards

### 3.1 Pauli String Endianness Hazard

In Qiskit, standard Pauli string representations follow right-to-left little-endian indexing:
- Character index $0$ (the rightmost character) corresponds to qubit $q_0$.
- Character index $5$ (the leftmost character) corresponds to qubit $q_5$.

If an operator were initialized using raw string labels (e.g. `"ZIIIII"`), a developer could mistakenly associate `"ZIIIII"` with qubit $q_0$ (the first character), whereas Qiskit assigns it to qubit $q_5$.

### 3.2 Endianness Elimination via `from_sparse_list`

To eliminate any ambiguity or potential endianness bug, `build_ensemble_z_observable()` employs Qiskit's programmatic `from_sparse_list` constructor:

```python
def build_ensemble_z_observable(
    num_qubits: int = NUM_QUBITS,
) -> SparsePauliOp:
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
```

Each tuple `("Z", [i], weight)` explicitly targets physical qubit index `i` without relying on string indexing conventions.

---

## 4. Empirical Validation & Edge Cases

### 4.1 Observable Structure & Coefficients

The resulting `SparsePauliOp` structure was verified directly:
```text
SparsePauliOp(['IIIIIZ', 'IIIIZI', 'IIIZII', 'IIZIII', 'IZIIII', 'ZIIIII'],
              coeffs=[0.16666667+0.j, 0.16666667+0.j, 0.16666667+0.j, 
                      0.16666667+0.j, 0.16666667+0.j, 0.16666667+0.j])
```
- `IIIIIZ`: $Z$ on qubit 0, weight $1/6$.
- `IIIIZI`: $Z$ on qubit 1, weight $1/6$.
- `IIIZII`: $Z$ on qubit 2, weight $1/6$.
- `IIZIII`: $Z$ on qubit 3, weight $1/6$.
- `IZIIII`: $Z$ on qubit 4, weight $1/6$.
- `ZIIIII`: $Z$ on qubit 5, weight $1/6$.

### 4.2 Computational Basis States Verification

Numerical expectation values computed via `Statevector.expectation_value(obs)`:
- $\langle 000000 | \bar{Z} | 000000 \rangle = +1.0000000000000000 + 0j$ (all 6 qubits are $+1$).
- $\langle 111111 | \bar{Z} | 111111 \rangle = -1.0000000000000000 + 0j$ (all 6 qubits are $-1$).
- $\langle 000111 | \bar{Z} | 000111 \rangle = 0.0000000000000000 + 0j$ (3 ones, 3 zeros).
- $\langle 101010 | \bar{Z} | 101010 \rangle = 0.0000000000000000 + 0j$ (3 ones, 3 zeros).

### 4.3 Composite Circuit Analytical Edge Case ($\mathbf{x}=\pi, \boldsymbol{\theta}=\mathbf{0}$)

When the full composite circuit $U_{\text{VQC}}$ is parameterized with $x_i = \pi$ for all 6 features and $\theta_j = 0$ for all 12 variational weights:
1. Feature map $U_\Phi(\pi)$ rotates ground state $|000000\rangle \rightarrow |111111\rangle$.
2. At $\boldsymbol{\theta} = \mathbf{0}$, the variational $R_y(0)$ rotations are identity operators, leaving the linear CNOT cascade:
   - $\text{CX}_{(0,1)}$: $q_0=1 \implies q_1$ flips from $1 \rightarrow 0$.
   - $\text{CX}_{(1,2)}$: $q_1=0 \implies q_2$ remains $1$.
   - $\text{CX}_{(2,3)}$: $q_2=1 \implies q_3$ flips from $1 \rightarrow 0$.
   - $\text{CX}_{(3,4)}$: $q_3=0 \implies q_4$ remains $1$.
   - $\text{CX}_{(4,5)}$: $q_4=1 \implies q_5$ flips from $1 \rightarrow 0$.
3. The resulting computational basis state has:
   $$q_0=1, \quad q_1=0, \quad q_2=1, \quad q_3=0, \quad q_4=1, \quad q_5=0$$
4. Qubits $\{q_0, q_2, q_4\}$ contribute $-1$ each; qubits $\{q_1, q_3, q_5\}$ contribute $+1$ each.
5. The sum of expectation values is $(-1 + 1 - 1 + 1 - 1 + 1) = 0$.
6. Measured expectation value: $\langle \bar{Z} \rangle = 0.0000000000000000 + 0j$ ($\text{matched to machine precision}$).

---

## 5. Test Suite Execution Results

### 5.1 Focused Circuit Tests (`tests/test_vqc_circuit.py`)

```bash
.venv\Scripts\pytest -v tests/test_vqc_circuit.py
```

Output:
```text
tests/test_vqc_circuit.py::test_parameter_vectors_creation_and_prefixes PASSED [  4%]
tests/test_vqc_circuit.py::test_parameter_vectors_element_names PASSED   [  9%]
tests/test_vqc_circuit.py::test_feature_map_structure_and_gates PASSED   [ 14%]
tests/test_vqc_circuit.py::test_feature_map_statevector_separable_product_state PASSED [ 19%]
tests/test_vqc_circuit.py::test_ansatz_qubit_and_parameter_counts PASSED [ 23%]
tests/test_vqc_circuit.py::test_ansatz_gate_counts_and_measured_depth PASSED [ 28%]
tests/test_vqc_circuit.py::test_ansatz_linear_cnot_entanglement_cascade PASSED [ 33%]
tests/test_vqc_circuit.py::test_ansatz_parameters_match_p_var_instance PASSED [ 38%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_qubits_and_parameters PASSED [ 42%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_parameter_ordering PASSED [ 47%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_gate_counts_and_measured_depth PASSED [ 52%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_gate_execution_order PASSED [ 57%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_input_validation_and_errors PASSED [ 61%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_statevector_smoke_test PASSED [ 66%]
tests/test_vqc_circuit.py::test_observable_structure_and_weights PASSED  [ 71%]
tests/test_vqc_circuit.py::test_observable_hermiticity_and_eigenvalues PASSED [ 76%]
tests/test_vqc_circuit.py::test_observable_computational_basis_expectations PASSED [ 80%]
tests/test_vqc_circuit.py::test_observable_qubit_count_validation PASSED [ 85%]
tests/test_vqc_circuit.py::test_exact_analytic_statevector_edge_case PASSED [ 90%]
tests/test_vqc_circuit.py::test_format_pub_parameters_helper SKIPPED     [ 95%]
tests/test_vqc_circuit.py::test_expectation_to_probability_mapping SKIPPED [100%]

======================== 19 passed, 2 skipped in 1.04s ========================
```

### 5.2 Full Project Regression Suite

```bash
.venv\Scripts\pytest -q
```

Output:
```text
67 passed, 2 skipped in 4.84s
```
Zero failures, zero regressions across classical baseline, feature extraction, and leak-free preprocessing modules.

---

## 6. Strict Scope & Governance Compliance Checklist

| Scope / Governance Requirement | Status | Evidence |
| :--- | :---: | :--- |
| Implement Step 4 (`build_ensemble_z_observable`) only | **PASSED** | Steps 5 & 6 remain stubs raising `NotImplementedError` |
| Exactly 6 Pauli terms | **PASSED** | `len(obs) == 6` |
| Each coefficient equals $1/6$ | **PASSED** | Verified in unit test |
| No identity or non-$Z$ Pauli terms | **PASSED** | Each term has exactly one $Z$ and 5 $I$ |
| Endianness-safe `from_sparse_list` API | **PASSED** | Directly tested on qubit indexing |
| Hermiticity validated | **PASSED** | $M = M^\dagger$ verified numerically |
| Spectrum bounded in $[-1, +1]$ | **PASSED** | Full eigenvalue spectrum analyzed |
| Basis state expectations ($+1, -1, 0$) | **PASSED** | Verified on computational basis states |
| Analytical edge case ($E=0$ at $x=\pi, \theta=0$) | **PASSED** | Evaluated on composite circuit |
| Qubit count validation | **PASSED** | Rejects non-6 qubit counts with clear error |
| No modifications to datasets or baselines | **PASSED** | Verified via `git status` |
| No git commits or pushes | **PASSED** | Awaiting technical lead authorization |

---

## 7. Handover & Recommendation for Step 5

Step 4 implementation is complete and thoroughly validated.

Upon technical lead approval, **Step 5** will implement:
- `format_pub_parameters(batch_x, theta)`: Vectorized PUB parameter alignment helper reshaping batch features $(N, 6)$ and variational parameters $(12,)$ into contiguous array $(N, 18)$ matching Qiskit's `circuit.parameters` layout.
