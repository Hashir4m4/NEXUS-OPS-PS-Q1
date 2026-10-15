# NEXUS-OPS — MILESTONE 5F.2 STEP 3 IMPLEMENTATION REVIEW
## Composite Parameterized VQC Circuit Builder (`build_vqc_circuit`)

**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Competition / Context:** IBM Quantum Qiskit Fall Fest 2026  
**Milestone:** 5F.2 — Core VQC Circuit Module (Step 3: Composite Circuit Assembly)  
**Date:** 13 October 2026  
**Status:** IMPLEMENTED & VERIFIED — PENDING TECHNICAL LEAD APPROVAL  
**Module:** `src/vqc_circuit.py`  
**Test Suite:** `tests/test_vqc_circuit.py`  

---

## 1. Executive Summary

Following technical lead authorization, **Step 3** has been implemented in [`src/vqc_circuit.py`](../src/vqc_circuit.py).

Step 3 introduces the composite circuit builder:
```python
def build_vqc_circuit(
    p_enc: Optional[Union[ParameterVector, QuantumCircuit]] = None,
    p_var: Optional[Union[ParameterVector, QuantumCircuit]] = None,
    qc_enc: Optional[QuantumCircuit] = None,
    ansatz: Optional[QuantumCircuit] = None,
    num_qubits: int = NUM_QUBITS,
) -> QuantumCircuit:
```

This function integrates the feature encoding map $U_\Phi(\mathbf{x})$ (Step 1) and the variational ansatz $W(\boldsymbol{\theta})$ (Step 2) into the unified 6-qubit parameterized circuit $U_{\text{VQC}}(\mathbf{x}, \boldsymbol{\theta})$ named `"VQC_Biomedical"`.

All structural, architectural, and mathematical invariants have been empirically verified:
- **Architecture:** Exactly 6 qubits ($q_0 \dots q_5$).
- **Parameter count:** Exactly 18 parameters (6 encoding `p_enc[0..5]` + 12 variational `p_var[0..11]`).
- **Composition order:** Feature map strictly precedes ansatz gates in `circuit.data`.
- **Parameter ordering:** `circuit.parameters` strictly sorts `p_enc[0..5]` first, followed by `p_var[0..11]`.
- **Gate counts:** Exactly 18 $R_y$ single-qubit gates and 5 $\text{CX}$ two-qubit gates (23 total gates).
- **Empirical untranspiled circuit depth:** Exactly **8**.
- **Statevector simulation smoke test:** Valid normalized statevector in $\mathbb{R}^{64}$ with identically zero imaginary amplitudes.
- **Unit test results:** 14 focused VQC circuit unit tests passed; 3 future stubs skipped; 62 full project tests passed (0 failures).

---

## 2. Mathematical Formulation & Composition Structure

The composite VQC circuit prepares the parameterized state $|\psi(\mathbf{x}, \boldsymbol{\theta})\rangle$ from the reference ground state $|0\rangle^{\otimes 6}$:

$$|\psi(\mathbf{x}, \boldsymbol{\theta})\rangle = U_{\text{VQC}}(\mathbf{x}, \boldsymbol{\theta}) |0\rangle^{\otimes 6} = \left[ W(\boldsymbol{\theta}) \cdot U_\Phi(\mathbf{x}) \right] |0\rangle^{\otimes 6}$$

### 2.1 Sequential Gate Breakdown

The composite circuit consists of four distinct operational stages executed sequentially:

1. **Feature Encoding Layer $U_\Phi(\mathbf{x})$ (Gates 0–5, Depth 1):**
   $$\bigotimes_{i=0}^5 R_y(x_i)$$
   Maps the 6 scaled physiological ECG features $x_i \in [0, \pi]$ onto qubits $q_0 \dots q_5$.

2. **Ansatz Rotation Layer 1 $R^{(1)}(\boldsymbol{\theta}_{0:6})$ (Gates 6–11, Depth +1 = 2):**
   $$\bigotimes_{i=0}^5 R_y(\theta_i)$$
   Applies initial parameter rotations on all 6 qubits using variational parameters $\theta_0 \dots \theta_5$.

3. **Linear Entanglement Cascade $U_{\text{ent}}$ (Gates 12–16, Depth +5 = 7):**
   $$\text{CX}_{(4,5)} \cdot \text{CX}_{(3,4)} \cdot \text{CX}_{(2,3)} \cdot \text{CX}_{(1,2)} \cdot \text{CX}_{(0,1)}$$
   Applies 5 nearest-neighbor CNOT gates sequentially across the 6 qubits.

4. **Ansatz Rotation Layer 2 $R^{(2)}(\boldsymbol{\theta}_{6:12})$ (Gates 17–22, Depth +1 = 8):**
   $$\bigotimes_{i=0}^5 R_y(\theta_{i+6})$$
   Applies final parameter rotations on all 6 qubits using variational parameters $\theta_6 \dots \theta_{11}$.

### 2.2 Preservation of Real Amplitudes

Every operation in the composite circuit belongs to real orthogonal groups $\mathrm{SO}(2)$ ($R_y$) or permutation matrices ($\text{CX}$). When applied to the real basis state $|000000\rangle$, the output statevector remains strictly constrained to the real manifold:

$$|\psi(\mathbf{x}, \boldsymbol{\theta})\rangle \in \mathbb{R}^{64} \subset \mathbb{C}^{64}, \quad \text{Im}\left[\langle k | \psi(\mathbf{x}, \boldsymbol{\theta})\rangle\right] = 0 \quad \forall k \in \{0, \dots, 63\}$$

---

## 3. Parameter Ordering & Prefix Hygiene Safeguards

In Qiskit, `QuantumCircuit.parameters` sorts `Parameter` objects alphabetically by name, regardless of circuit construction or compose order.

### 3.1 Verification of Prefix Hygiene

Because the prefix `"p_enc"` lexicographically precedes `"p_var"` (`'p_enc'` < `'p_var'`), the Qiskit parameter table is guaranteed to index parameters in deterministic execution order:

| Index in `circuit.parameters` | Parameter Name | Parameter Role | Source Vector |
| :---: | :---: | :---: | :---: |
| 0 | `p_enc[0]` | Feature 0 ($QRS\_duration$) | `p_enc` |
| 1 | `p_enc[1]` | Feature 1 ($P\_wave\_amplitude$) | `p_enc` |
| 2 | `p_enc[2]` | Feature 2 ($T\_wave\_amplitude$) | `p_enc` |
| 3 | `p_enc[3]` | Feature 3 ($ST\_segment\_level$) | `p_enc` |
| 4 | `p_enc[4]` | Feature 4 ($pre\_RR\_interval$) | `p_enc` |
| 5 | `p_enc[5]` | Feature 5 ($post\_RR\_interval$) | `p_enc` |
| 6 | `p_var[0]` | Ansatz Layer 1, Qubit 0 | `p_var` |
| 7 | `p_var[1]` | Ansatz Layer 1, Qubit 1 | `p_var` |
| 8 | `p_var[2]` | Ansatz Layer 1, Qubit 2 | `p_var` |
| 9 | `p_var[3]` | Ansatz Layer 1, Qubit 3 | `p_var` |
| 10 | `p_var[4]` | Ansatz Layer 1, Qubit 4 | `p_var` |
| 11 | `p_var[5]` | Ansatz Layer 1, Qubit 5 | `p_var` |
| 12 | `p_var[6]` | Ansatz Layer 2, Qubit 0 | `p_var` |
| 13 | `p_var[7]` | Ansatz Layer 2, Qubit 1 | `p_var` |
| 14 | `p_var[8]` | Ansatz Layer 2, Qubit 2 | `p_var` |
| 15 | `p_var[9]` | Ansatz Layer 2, Qubit 3 | `p_var` |
| 16 | `p_var[10]` | Ansatz Layer 2, Qubit 4 | `p_var` |
| 17 | `p_var[11]` | Ansatz Layer 2, Qubit 5 | `p_var` |

### 3.2 Runtime Verification Guard

Inside `build_vqc_circuit()`, an assertion verifies that `[p.name for p in vqc.parameters]` matches the exact sequence above. If any parameter naming hazard occurs, a `RuntimeError` is raised immediately before the circuit is returned.

---

## 4. Empirical Circuit Metrics & Depth Breakdown

### 4.1 Gate Counts

| Component Circuit | $R_y$ Gates | $\text{CX}$ Gates | Total Gates |
| :--- | :---: | :---: | :---: |
| Feature Map $U_\Phi(\mathbf{x})$ | 6 | 0 | 6 |
| Variational Ansatz $W(\boldsymbol{\theta})$ | 12 | 5 | 17 |
| **Composite VQC Circuit** | **18** | **5** | **23** |

### 4.2 Untranspiled Circuit Depth

The circuit depth measured directly via `vqc.depth()` is **8**:
- Stage 1 (Encoding): 6 parallel $R_y$ gates on qubits $0 \dots 5$ $\rightarrow$ depth = 1.
- Stage 2 (Ansatz $R^{(1)}$): 6 parallel $R_y$ gates on qubits $0 \dots 5$ $\rightarrow$ depth = 2.
- Stage 3 (Ansatz $U_{\text{ent}}$): 5 sequential CNOT gates on pairs $(0,1), (1,2), (2,3), (3,4), (4,5)$ $\rightarrow$ depth advances by 5 to 7.
- Stage 4 (Ansatz $R^{(2)}$): 6 parallel $R_y$ gates on qubits $0 \dots 5$ $\rightarrow$ depth advances by 1 to 8.

$$\text{Total Untranspiled Depth} = 1 + 1 + 5 + 1 = 8$$

---

## 5. Input Validation & Error Handling

To ensure robust pipeline integration, `build_vqc_circuit()` implements strict input validation:
1. **Invalid parameter vector length:** Rejects encoding vectors where `len(p_enc) != 6` and variational vectors where `len(p_var) != 12` with `ValueError`.
2. **Incompatible circuit dimensions:** Rejects feature map or ansatz circuits where `num_qubits != 6` with `ValueError`.
3. **Invalid parameter types:** Rejects unexpected argument types with `TypeError`.
4. **Flexible interface:** Accepts either `ParameterVector` objects, pre-constructed `QuantumCircuit` objects, or `None` (auto-constructed default vectors).

---

## 6. Test Suite Execution Results

### 6.1 Focused Circuit Tests (`tests/test_vqc_circuit.py`)

Execution command:
```bash
.venv\Scripts\pytest -v tests/test_vqc_circuit.py
```

Output:
```text
tests/test_vqc_circuit.py::test_parameter_vectors_creation_and_prefixes PASSED [  5%]
tests/test_vqc_circuit.py::test_parameter_vectors_element_names PASSED   [ 11%]
tests/test_vqc_circuit.py::test_feature_map_structure_and_gates PASSED   [ 17%]
tests/test_vqc_circuit.py::test_feature_map_statevector_separable_product_state PASSED [ 23%]
tests/test_vqc_circuit.py::test_ansatz_qubit_and_parameter_counts PASSED [ 29%]
tests/test_vqc_circuit.py::test_ansatz_gate_counts_and_measured_depth PASSED [ 35%]
tests/test_vqc_circuit.py::test_ansatz_linear_cnot_entanglement_cascade PASSED [ 41%]
tests/test_vqc_circuit.py::test_ansatz_parameters_match_p_var_instance PASSED [ 47%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_qubits_and_parameters PASSED [ 52%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_parameter_ordering PASSED [ 58%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_gate_counts_and_measured_depth PASSED [ 64%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_gate_execution_order PASSED [ 70%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_input_validation_and_errors PASSED [ 76%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_statevector_smoke_test PASSED [ 82%]
tests/test_vqc_circuit.py::test_observable_structure_and_weights SKIPPED [ 88%]
tests/test_vqc_circuit.py::test_exact_analytic_statevector_edge_case SKIPPED [ 94%]
tests/test_vqc_circuit.py::test_format_pub_parameters_helper SKIPPED     [100%]

======================== 14 passed, 3 skipped in 1.73s ========================
```

### 6.2 Full Project Regression Suite

Execution command:
```bash
.venv\Scripts\pytest -q
```

Output:
```text
62 passed, 3 skipped in 9.01s
```
Zero regressions across all existing classical baseline, feature extraction, and leak-free preprocessing modules.

---

## 7. Scope & Governance Compliance Checklist

| Scope / Governance Requirement | Status | Evidence |
| :--- | :---: | :--- |
| Implement Step 3 (`build_vqc_circuit`) only | **PASSED** | Steps 4, 5, 6 remain stubs with `NotImplementedError` |
| Feature map first, ansatz second | **PASSED** | Verified in `test_composite_vqc_circuit_gate_execution_order` |
| 6 qubits preserved | **PASSED** | `vqc.num_qubits == 6` |
| Exactly 18 parameters (`p_enc[0..5]`, `p_var[0..11]`) | **PASSED** | Verified in `test_composite_vqc_circuit_parameter_ordering` |
| Deterministic parameter ordering | **PASSED** | Enforced and asserted against Qiskit parameter table |
| Gate counts: 18 Ry, 5 CX (23 total) | **PASSED** | Asserted in module and unit tests |
| Actual depth measured (depth = 8) | **PASSED** | Empirically verified and documented |
| Numerical Statevector smoke test | **PASSED** | Real manifold, valid norm verified |
| Input validation and error handling | **PASSED** | Tested in `test_composite_vqc_circuit_input_validation_and_errors` |
| No modification to datasets or baselines | **PASSED** | Confirmed via `git status` |
| No commits or pushes performed | **PASSED** | Awaiting technical lead authorization |

---

## 8. Handover & Recommendation for Step 4

Step 3 is complete, fully tested, and ready for technical lead review.

Upon technical lead approval, **Step 4** will implement:
- `build_ensemble_z_observable(num_qubits)`: Constructs the ensemble average Pauli-Z observable $\bar{Z} = \frac{1}{6} \sum_{i=0}^5 Z_i$ using `SparsePauliOp.from_sparse_list` to eliminate string-endianness hazards.
- Exact analytical expectation test: $\langle \bar{Z} \rangle = 0$ for $x = \pi, \boldsymbol{\theta} = \mathbf{0}$.
