# NEXUS-OPS — MILESTONE 5F.2 STEP 2 IMPLEMENTATION REVIEW
## Variational Ansatz Builder (`build_ansatz`)

**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Competition / Context:** IBM Quantum Qiskit Fall Fest 2026  
**Milestone:** 5F.2 — Core VQC Circuit Module (Step 2: Variational Ansatz)  
**Date:** 13 October 2026  
**Status:** IMPLEMENTED & VERIFIED — PENDING TECHNICAL LEAD APPROVAL  
**Module:** `src/vqc_circuit.py`  
**Test Suite:** `tests/test_vqc_circuit.py`  

---

## 1. Executive Summary

In accordance with the Milestone 5F.2 execution plan approved by the technical lead, **Step 2** has been implemented in [`src/vqc_circuit.py`](../src/vqc_circuit.py).

Step 2 introduces `build_ansatz(...)`, constructing the team-approved `RealAmplitudes` variational ansatz using Qiskit 2.5.2's functional API `qiskit.circuit.library.real_amplitudes`.

All mathematical and structural invariants approved in Decision **D2** and the Milestone 5E architecture contract have been empirically verified:
- **Qubit count:** Exactly 6 qubits ($q_0 \dots q_5$).
- **Variational parameter count:** Exactly 12 parameters (`p_var[0]` to `p_var[11]`).
- **Gate counts:** Exactly 12 single-qubit $R_y$ rotation gates and 5 two-qubit $\text{CX}$ gates.
- **Entanglement topology:** Nearest-neighbor linear cascade: $(0,1), (1,2), (2,3), (3,4), (4,5)$.
- **Empirical untranspiled circuit depth:** Exactly **7**.
- **Test execution:** 8 focused VQC circuit unit tests passed; 4 future stubs skipped; 56 total project tests passed (0 failures).

---

## 2. Mathematical Specification

The variational ansatz $W(\boldsymbol{\theta})$ operates on the 6-qubit state $|\Phi(\mathbf{x})\rangle$ prepared by the feature map $U_\Phi(\mathbf{x})$.

### 2.1 Operator Factorization

For $n = 6$ qubits and $L = 1$ repetition (`reps=1`), the ansatz decomposes into three distinct layers:

$$W(\boldsymbol{\theta}) = R^{(2)}(\boldsymbol{\theta}_{6:12}) \cdot U_{\text{ent}} \cdot R^{(1)}(\boldsymbol{\theta}_{0:6})$$

1. **Initial Single-Qubit Rotation Layer $R^{(1)}$:**
   $$R^{(1)}(\boldsymbol{\theta}_{0:6}) = \bigotimes_{i=0}^5 R_y(\theta_i)$$
   Applies an independent parameterized $Y$-rotation to each qubit $i \in \{0, \dots, 5\}$.

2. **Linear Entanglement Layer $U_{\text{ent}}$:**
   $$U_{\text{ent}} = \prod_{i=0}^{4} \text{CX}_{(i,\, i+1)} = \text{CX}_{(4,5)} \cdot \text{CX}_{(3,4)} \cdot \text{CX}_{(2,3)} \cdot \text{CX}_{(1,2)} \cdot \text{CX}_{(0,1)}$$
   Applies a sequence of 5 nearest-neighbor controlled-NOT gates, generating bipartite and multi-qubit quantum correlations without incurring long-range connectivity overhead.

3. **Final Single-Qubit Rotation Layer $R^{(2)}$:**
   $$R^{(2)}(\boldsymbol{\theta}_{6:12}) = \bigotimes_{i=0}^5 R_y(\theta_{i+6})$$
   Applies a second independent parameterized $Y$-rotation to each qubit $i \in \{0, \dots, 5\}$.

### 2.2 Invariant Real Statevector Property

Because $R_y(\theta) \in \mathrm{SO}(2) \subset \mathbb{R}^{2 \times 2}$ and $\text{CX} \in \{0, 1\}^{4 \times 4} \subset \mathbb{R}^{4 \times 4}$, every gate in $W(\boldsymbol{\theta})$ has purely real matrix representations in the computational basis. Acting on the purely real state $|\Phi(\mathbf{x})\rangle$, the resulting output state vector $|\psi(\mathbf{x}, \boldsymbol{\theta})\rangle = W(\boldsymbol{\theta})|\Phi(\mathbf{x})\rangle$ remains strictly confined to the real sub-manifold $\mathbb{R}^{64} \subset \mathbb{C}^{64}$.

---

## 3. Implementation Details

### 3.1 Function Signature & Logic

```python
def build_ansatz(
    p_var: Optional[ParameterVector] = None,
    num_qubits: int = NUM_QUBITS,
    reps: int = 1,
    entanglement: str = "linear",
) -> QuantumCircuit:
    num_weights = num_qubits * (reps + 1)  # 6 * (1 + 1) = 12

    if p_var is None:
        _, p_var = create_parameter_vectors(num_features=num_qubits, num_weights=num_weights)
    elif len(p_var) != num_weights:
        raise ValueError(
            f"Variational vector length ({len(p_var)}) must equal expected parameter count ({num_weights})."
        )

    # Functional API call compliant with Qiskit 2.5.2
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
    assert ansatz.depth() == 7, f"Measured ansatz depth mismatch: expected 7, got {ansatz.depth()}"
    assert list(ansatz.parameters) == list(p_var), "Ansatz parameters must match p_var vector."

    return ansatz
```

### 3.2 Qiskit 2.5.2 Rust Accelerator Parameter Mechanics

During unit test validation of parameter binding, an important architectural characteristic of Qiskit 2.5.2 was identified and accommodated:
1. `QuantumCircuit.parameters` accesses the internal Rust parameter table (`ParameterView`).
2. Each query to `circuit.parameters` dynamically instantiates a Python wrapper object of type `qiskit._accelerate.circuit.ParameterVectorElement`.
3. Consequently, testing Python object pointer identity (`param is p_var[idx]`) fails across the Rust boundary, even for identical parameters on consecutive accesses (`qc.parameters[0] is qc.parameters[0]` is `False`).
4. Parameter verification is rigorously established via:
   - Vector equality: `list(ansatz.parameters) == list(p_var)` ($\text{True}$)
   - Element equality: `param == p_var[idx]` ($\text{True}$)
   - Element index: `param.index == idx` ($\text{True}$)
   - Element vector name: `param.vector.name == "p_var"` ($\text{True}$)

---

## 4. Empirical Circuit Inspection & Depth Analysis

### 4.1 Gate Counts

| Component | Operation | Quantity | Mathematical Role |
| :--- | :--- | :---: | :--- |
| Rotation Layer 1 | $R_y(\theta_0 \dots \theta_5)$ | 6 | Initial basis state rotations |
| Entanglement Layer | $\text{CX}_{(i, i+1)}$ | 5 | Nearest-neighbor linear entangling cascade |
| Rotation Layer 2 | $R_y(\theta_6 \dots \theta_{11})$ | 6 | Final basis state rotations |
| **Total Single-Qubit Gates** | $R_y$ | **12** | Continuous parameter search space $\mathbb{R}^{12}$ |
| **Total Two-Qubit Gates** | $\text{CX}$ | **5** | Low CNOT count minimizing two-qubit noise |
| **Total Circuit Gates** | All | **17** | Compact, NISQ-efficient execution |

### 4.2 Circuit Depth Decomposition

The untranspiled circuit depth was measured directly via `ansatz.depth()`. The measured result is **7**, derived as follows:

1. **Depth 1:** 6 parallel $R_y$ gates on qubits $q_0, q_1, q_2, q_3, q_4, q_5$.
2. **Depth 2:** $\text{CX}_{(0, 1)}$ (qubits 0 and 1 active).
3. **Depth 3:** $\text{CX}_{(1, 2)}$ (qubit 1 becomes free, interacts with qubit 2).
4. **Depth 4:** $\text{CX}_{(2, 3)}$ (qubit 2 becomes free, interacts with qubit 3).
5. **Depth 5:** $\text{CX}_{(3, 4)}$ (qubit 3 becomes free, interacts with qubit 4).
6. **Depth 6:** $\text{CX}_{(4, 5)}$ (qubit 4 becomes free, interacts with qubit 5).
7. **Depth 7:** 6 parallel $R_y$ gates on qubits $q_0, q_1, q_2, q_3, q_4, q_5$.

$$\text{Total Depth} = 1 + 5 + 1 = 7$$

---

## 5. Verification & Test Suite Execution

Focused VQC circuit test suite execution:
```bash
.venv\Scripts\pytest -v tests/test_vqc_circuit.py
```

Results:
```text
tests/test_vqc_circuit.py::test_parameter_vectors_creation_and_prefixes PASSED [  8%]
tests/test_vqc_circuit.py::test_parameter_vectors_element_names PASSED   [ 16%]
tests/test_vqc_circuit.py::test_feature_map_structure_and_gates PASSED   [ 25%]
tests/test_vqc_circuit.py::test_feature_map_statevector_separable_product_state PASSED [ 33%]
tests/test_vqc_circuit.py::test_ansatz_qubit_and_parameter_counts PASSED [ 41%]
tests/test_vqc_circuit.py::test_ansatz_gate_counts_and_measured_depth PASSED [ 50%]
tests/test_vqc_circuit.py::test_ansatz_linear_cnot_entanglement_cascade PASSED [ 58%]
tests/test_vqc_circuit.py::test_ansatz_parameters_match_p_var_instance PASSED [ 66%]
tests/test_vqc_circuit.py::test_composite_vqc_circuit_parameter_ordering SKIPPED [ 75%]
tests/test_vqc_circuit.py::test_observable_structure_and_weights SKIPPED [ 83%]
tests/test_vqc_circuit.py::test_exact_analytic_statevector_edge_case SKIPPED [ 91%]
tests/test_vqc_circuit.py::test_format_pub_parameters_helper SKIPPED     [100%]

======================== 8 passed, 4 skipped in 1.98s =========================
```

Full repository regression suite:
```bash
.venv\Scripts\pytest -q
```
```text
56 passed, 4 skipped in 6.86s
```

All 56 existing classical baseline, feature engineering, and leak-free preprocessing tests pass without regression.

---

## 6. Strict Scope & Safeguards Compliance

| Safeguard / Scope Requirement | Status | Evidence |
| :--- | :---: | :--- |
| Implement Step 2 (`build_ansatz`) only | **PASSED** | Only `build_ansatz` implemented; subsequent functions raise `NotImplementedError` |
| Functional `real_amplitudes` API used | **PASSED** | `qiskit.circuit.library.real_amplitudes` called; deprecated class avoided |
| 6 qubits, reps=1, linear entanglement | **PASSED** | Asserted by unit tests and circuit structure inspection |
| Exactly 12 parameters (`p_var[0..11]`) | **PASSED** | Parameter vector validated |
| 12 Ry gates, 5 CX gates | **PASSED** | `count_ops()` validated |
| Measured depth documented (depth = 7) | **PASSED** | Empirically verified and documented |
| Step 3+ tests remain skipped | **PASSED** | 4 future tests marked `@pytest.mark.skip` |
| No modifications to datasets or baselines | **PASSED** | Verified via `git status` |
| No commits or pushes performed | **PASSED** | Awaiting technical lead authorization |

---

## 7. Handover & Recommendation for Step 3

Step 2 is complete, fully tested, and ready for technical lead review.

Upon technical lead approval, **Step 3** will implement:
- `build_vqc_circuit(qc_enc, qc_ansatz)`: Composing the feature map and variational ansatz into the composite 6-qubit parameterized circuit $U_{\text{VQC}}(\mathbf{x}, \boldsymbol{\theta}) = W(\boldsymbol{\theta}) \cdot U_\Phi(\mathbf{x})$.
- Total gate counts: 18 $R_y$ gates, 5 $\text{CX}$ gates, depth = 8.
- Deterministic parameter ordering: $[p_{\text{enc}}[0..5], p_{\text{var}}[0..11]]$ verified against `circuit.parameters`.
