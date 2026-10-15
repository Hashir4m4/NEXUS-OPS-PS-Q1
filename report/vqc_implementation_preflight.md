# Milestone 5F.1: VQC Circuit Implementation Preflight Report

**Project:** Project Q — IBM Quantum Qiskit Fall Fest 2026  
**Challenge:** PS-Q1 — Biomedical Signal Classifier  
**Team:** NEXUS-OPS  
**Stage:** Milestone 5F.1 Implementation Preflight  
**Document Purpose:** Environment Inspection, API Signature Verification, Parameter Ordering Safeguards, and Test Specifications for `src/vqc_circuit.py`  
**Latest Git Governance Commit:** `ccf6f27` (`docs(governance): record team approval of VQC architecture decisions D1-D10 (Milestone 5E)`)  
**Submission Deadline:** 14 October 2026  
**Date:** October 13, 2026  

---

## 1. Executive Summary & Repository Health Check

This preflight technical audit prepares the development environment for the team-owned implementation of [`src/vqc_circuit.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/vqc_circuit.py).

### Repository Status
* **Git Head Commit:** `ccf6f270f419c6c32fba88703a0852a50744cb5c` (`ccf6f27`)
* **Tracking Branch:** `main` tracking `origin/main` (up to date)
* **Working Tree:** Clean prior to this report creation
* **All 10 Architectural Decisions (D1–D10):** Confirmed `TEAM_APPROVED` in [`results/vqc_architecture_decisions.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/vqc_architecture_decisions.json)
* **Existing Test Suite:** **48 / 48 tests passing** (5.02s)

> [!IMPORTANT]
> **Implementation Boundary Notice:**  
> In accordance with hackathon rules, this preflight task does **not** implement the circuit, forward pass, loss, optimizer, or training loop. It provides API signatures, parameter sorting warnings, and testing scaffolds for the technical lead.

---

## 2. Installed Qiskit 2.5.2 & Aer 0.17.2 API Signatures

The active environment was inspected via Python's `inspect` module:
* **Python Version:** 3.13.7
* **Qiskit Version:** 2.5.2
* **Qiskit Aer Version:** 0.17.2

### Verified Class & Method Signatures

```python
# 1. QuantumCircuit
class QuantumCircuit:
    def __init__(
        self,
        *regs: Register | int | Sequence[Bit],
        name: str | None = None,
        global_phase: ParameterValueType = 0,
        metadata: dict | None = None,
        inputs: Iterable[expr.Var] = (),
        captures: Iterable[expr.Var | expr.Stretch] = (),
        declarations: Mapping[expr.Var, expr.Expr] | Iterable[tuple[expr.Var, expr.Expr]] = ()
    )

# 2. ParameterVector
class ParameterVector:
    def __init__(self, name: str, length: int)

# 3. real_amplitudes (Preferred functional API in Qiskit 2.1+)
def real_amplitudes(
    num_qubits: int,
    entanglement: BlockEntanglement | Iterable[BlockEntanglement] | Callable[[int], BlockEntanglement | Iterable[BlockEntanglement]] = 'reverse_linear',
    reps: int = 3,
    skip_unentangled_qubits: bool = False,
    skip_final_rotation_layer: bool = False,
    parameter_prefix: str = 'θ',
    insert_barriers: bool = False,
    name: str = 'RealAmplitudes'
) -> QuantumCircuit

# 4. SparsePauliOp.from_sparse_list
@classmethod
def from_sparse_list(
    cls,
    obj: Iterable[tuple[str, list[int], complex]],
    num_qubits: int,
    do_checks: bool = True,
    dtype: type | None = None
) -> SparsePauliOp

# 5. StatevectorEstimator (Qiskit Primitives V2)
class StatevectorEstimator:
    def __init__(
        self,
        *,
        default_precision: float = 0.0,
        seed: np.random.Generator | int | None = None
    )
    def run(
        self,
        pubs: Iterable[EstimatorPubLike],
        *,
        precision: float | None = None
    ) -> PrimitiveJob[PrimitiveResult[PubResult]]

# 6. EstimatorV2 (Qiskit Aer 0.17.2)
class EstimatorV2:
    def __init__(self, *, options: dict | None = None)
    def run(
        self,
        pubs: Iterable[EstimatorPubLike],
        *,
        precision: float | None = None
    ) -> PrimitiveJob[PrimitiveResult[PubResult]]
```

---

## 3. Recommended Qiskit 2.5.2 Usage Patterns

### 3.1 Qubits & Parameter Vectors
```python
from qiskit.circuit import QuantumCircuit, ParameterVector

# 6 qubits for 1:1 mapping of 6 biomedical features
NUM_QUBITS = 6

# Feature parameters (6 dimensions)
# CRITICAL: Prefix 'p_enc' guarantees alphabetical sort before 'p_var'
p_enc = ParameterVector("p_enc", 6)

# Variational trainable parameters (12 dimensions for L=1)
p_var = ParameterVector("p_var", 12)
```

### 3.2 Feature Map Construction ($U_\Phi(\mathbf{x})$)
```python
def build_feature_map(p_enc: ParameterVector) -> QuantumCircuit:
    qc_enc = QuantumCircuit(NUM_QUBITS, name="FeatureMap")
    for i in range(NUM_QUBITS):
        qc_enc.ry(p_enc[i], i)
    return qc_enc
```

### 3.3 Variational Ansatz Construction ($W(\boldsymbol{\theta})$)
```python
from qiskit.circuit.library import real_amplitudes

def build_ansatz(p_var: ParameterVector) -> QuantumCircuit:
    # Use real_amplitudes functional API with reps=1, linear entanglement
    # and explicit parameter_prefix matching p_var
    ansatz = real_amplitudes(
        num_qubits=NUM_QUBITS,
        entanglement="linear",
        reps=1,
        parameter_prefix="p_var",
        name="RealAmplitudes",
    )
    return ansatz
```

### 3.4 Composite VQC Circuit Assembly
```python
def build_vqc_circuit(qc_enc: QuantumCircuit, ansatz: QuantumCircuit) -> QuantumCircuit:
    vqc = QuantumCircuit(NUM_QUBITS, name="VQC_Biomedical")
    vqc.compose(qc_enc, inplace=True)
    vqc.compose(ansatz, inplace=True)
    return vqc
```

### 3.5 Average Six-Qubit Pauli-Z Observable
```python
from qiskit.quantum_info import SparsePauliOp

def build_ensemble_z_observable(num_qubits: int = NUM_QUBITS) -> SparsePauliOp:
    # Construct 6 local Z operators, each with coefficient 1/6
    # from_sparse_list explicitly maps term ('Z', [i], 1/6) to qubit i
    sparse_list = [("Z", [i], 1.0 / num_qubits) for i in range(num_qubits)]
    return SparsePauliOp.from_sparse_list(sparse_list, num_qubits=num_qubits)
```

### 3.6 Expectation Evaluation via Primitive V2 PUBs
```python
from qiskit.primitives import StatevectorEstimator

estimator = StatevectorEstimator()

# PUB format: (circuit, observable, parameter_values)
# For batch evaluation: parameter_values is shape (N, 18)
pub = (vqc_circuit, observable, batch_params)
job = estimator.run([pub])
result = job.result()
expectations = result[0].data.evs  # Returns np.ndarray of shape (N,) bounded in [-1, +1]
```

---

## 4. Parameter Ordering Hazards & Recommended Safeguards

> [!CAUTION]
> **CRITICAL ARCHITECTURAL PITFALL:**  
> In Qiskit, `circuit.parameters` is a `ParameterView` that sorts parameters **alphabetically by name**, **NOT** by circuit insertion order!

### 4.1 Empirical Demonstration of the Hazard
If a developer creates:
* `enc_params = ParameterVector('x', 6)`
* `var_params = ParameterVector('theta', 12)`

When composed into `vqc = qc_enc.compose(ansatz)`:
* ASCII `'t'` precedes `'x'` (`'theta'` < `'x'`).
* `list(vqc.parameters)` is sorted as:
  `['theta[0]', ..., 'theta[11]', 'x[0]', ..., 'x[5]']`
* When passing `batch_params = np.hstack([batch_x, batch_theta])` into `StatevectorEstimator.run([(vqc, obs, batch_params)])`:
  * Qiskit maps the first 6 columns of `batch_x` to `theta[0]...theta[5]`.
  * Qiskit maps the first 6 columns of `batch_theta` to `theta[6]...theta[11]`.
  * Qiskit maps the last 6 columns of `batch_theta` to `x[0]...x[5]`.
* **Consequence:** The model silently swaps inputs and weights without raising an exception!

### 4.2 Enforced Implementation Safeguards

To prevent this hazard from occurring in `src/vqc_circuit.py`:

1. **Prefix Enforcement:**
   Name the parameter vectors using prefixes whose alphabetical order matches physical circuit execution order:
   * Encoding parameters: `ParameterVector("p_enc", 6)`
   * Variational parameters: `ParameterVector("p_var", 12)`
   *(Since `'p_enc'` alphabetically precedes `'p_var'`, `circuit.parameters` is mathematically guaranteed to list encoding parameters $0\dots5$ first, followed by variational parameters $0\dots11$).*

2. **Structural Assertion Invariant:**
   Inside `build_vqc_circuit()`, enforce an assertion check before returning:
   ```python
   expected_order = list(p_enc) + list(p_var)
   actual_order = list(vqc.parameters)
   if actual_order != expected_order:
       raise RuntimeError(
           f"Parameter ordering mismatch in VQC circuit!\n"
           f"Expected: {[p.name for p in expected_order]}\n"
           f"Actual:   {[p.name for p in actual_order]}"
       )
   ```

3. **Explicit Vector Alignment Helper:**
   Provide a utility in `src/vqc_circuit.py`:
   ```python
   def format_pub_parameters(batch_x: np.ndarray, theta: np.ndarray) -> np.ndarray:
       """
       Aligns batch features (N, 6) and variational parameters (12,)
       into a contiguous 2D array of shape (N, 18) matching circuit.parameters.
       """
       X_mat = np.asarray(batch_x, dtype=np.float64)
       if X_mat.ndim == 1:
           X_mat = X_mat.reshape(1, -1)
       n_samples = X_mat.shape[0]
       theta_row = np.asarray(theta, dtype=np.float64).reshape(1, -1)
       theta_tile = np.tile(theta_row, (n_samples, 1))
       return np.hstack([X_mat, theta_tile])
   ```

---

## 5. Observable Construction & Endianness Safeguards

### 5.1 Endianness Hazard
In Qiskit's Pauli string convention, qubit indices are **little-endian** (right-to-left):
* String `'IIIIIZ'` corresponds to Pauli-$Z$ on Qubit 0 ($q_0$).
* String `'ZIIIII'` corresponds to Pauli-$Z$ on Qubit 5 ($q_5$).

If an engineer constructs strings manually using string concatenation (e.g. `['Z' + 'I'*5, ...]`), they will invert the qubit assignments, associating Qubit 0's measurement with Qubit 5's feature!

### 5.2 Enforced Solution
Use `SparsePauliOp.from_sparse_list()`:
```python
sparse_list = [("Z", [i], 1.0 / 6.0) for i in range(6)]
obs = SparsePauliOp.from_sparse_list(sparse_list, num_qubits=6)
```
This method explicitly assigns term $i$ to qubit index `[i]`, completely eliminating string-indexing confusion.

### 5.3 Eigenstate Invariants
The observable must be verified against computational basis states:
* $\langle 000000 | \hat{O} | 000000 \rangle = +1.0$ (since $Z|0\rangle = +1|0\rangle$).
* $\langle 111111 | \hat{O} | 111111 \rangle = -1.0$ (since $Z|1\rangle = -1|1\rangle$).

---

## 6. Proposed Minimal Unit-Test Checklist (`tests/test_vqc_circuit.py`)

When the technical lead implements `tests/test_vqc_circuit.py`, the following 9 test cases should be included to verify the circuit independently without running training loops:

| # | Test Function Name | Tested Invariant / Verification Condition |
| :-: | :--- | :--- |
| **T1** | `test_circuit_qubit_and_parameter_counts` | Assert `circuit.num_qubits == 6`, `circuit.num_parameters == 18` (6 encoding + 12 variational). |
| **T2** | `test_parameter_ordering_integrity` | Assert `list(circuit.parameters) == list(p_enc) + list(p_var)` to guarantee alphabetical prefix hygiene. |
| **T3** | `test_untranspiled_gate_counts_and_depth` | Assert `count_ops()['ry'] == 18`, `count_ops()['cx'] == 5`, and untranspiled `depth() == 8`. |
| **T4** | `test_observable_structure_and_coefficients` | Assert `observable.num_qubits == 6`, term count == 6, and sum of coefficients == $1.0$. |
| **T5** | `test_observable_eigenstates_endianness` | Assert expectation on $|000000\rangle$ is $+1.0 \pm 10^{-12}$ and on $|111111\rangle$ is $-1.0 \pm 10^{-12}$. |
| **T6** | `test_exact_analytic_statevector_evaluation` | Set $\mathbf{x} = \boldsymbol{\pi}$ and $\boldsymbol{\theta} = \mathbf{0}$; verify state collapses to $|010101\rangle$ with analytic expectation $E = 0.0 \pm 10^{-12}$. |
| **T7** | `test_output_expectation_range_and_probabilities` | Evaluate random parameters across 100 samples; assert all $E \in [-1.0, +1.0]$ and $p = (E+1)/2 \in [0.0, 1.0]$. |
| **T8** | `test_pub_vectorized_batch_execution_equivalence` | Assert batch evaluation of shape $(N, 18)$ yields identical expectations ($< 10^{-12}$) to $N$ individual evaluations. |
| **T9** | `test_format_pub_parameters_helper` | Assert parameter formatting helper validates input dimensions and correctly stacks 2D arrays. |

---

## 7. Status & Non-Regression Invariants

- [x] **Circuit Implementation Deferred:** `src/vqc_circuit.py` has not yet been authored.
- [x] **Unrelated Artifacts Untouched:** MIT-BIH raw data, processed CSVs, classical models, and classical results are identical.
- [x] **Governance Intact:** All ten decisions (D1–D10) remain `TEAM_APPROVED`.
- [x] **Test Suite Passing:** All 48 existing tests pass in 5.02s.
- [x] **Git Cleanliness:** No commits or pushes made.

---

## 8. Single Recommended Next Action for the Technical Lead

> **Review `report/vqc_implementation_preflight.md` and authorize the authoring of `src/vqc_circuit.py` and `tests/test_vqc_circuit.py` following the verified Qiskit 2.5.2 APIs and parameter-ordering safeguards.**
