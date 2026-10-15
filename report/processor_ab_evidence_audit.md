# NEXUS-OPS — Processor A/B Evidence Audit Report
## Independent Verification & Technical Audit of Processor A/B Benchmarks

**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Event / Competition:** IBM Quantum Qiskit Fall Fest 2026 (Phase 1)  
**Role:** Independent Quantum Hardware Architecture Auditor  
**Date:** 13 October 2026  
**Audited Artifacts:**
- [`processors/processor_A.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_A.json)
- [`processors/processor_B.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_B.json)
- [`processors/processor_A_branching.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_A_branching.json)
- [`processors/processor_B_cyclic.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_B_cyclic.json)
- [`processors/processor_a.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_a.py)
- [`processors/processor_b.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_b.py)
- [`results/processor_ab_transpilation.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/processor_ab_transpilation.json)
- [`report/processor_ab_topology_research.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/processor_ab_topology_research.md)
- [`report/processor_ab_experiment_design.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/processor_ab_experiment_design.md)
- [`tests/test_processor_ab.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests/test_processor_ab.py)

**Audit Deliverables:**
- [`report/processor_ab_evidence_audit.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/processor_ab_evidence_audit.md)
- [`results/processor_ab_evidence_audit.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/processor_ab_evidence_audit.json)

---

## 1. Executive Audit Summary & Verdict

```text
================================================================================
AUDIT VERDICT: CONDITIONAL PASS
================================================================================
Summary:
1. SPECIFICATIONS & TOPOLOGY: VERIFIED. Processor A (5Q linear chain) and 
   Processor B (9Q heavy-hex sparse tree) strictly match the official 
   Updated Challenge Kit (Oct 12, 2026).
2. TRANSPILATION BENCHMARKS: FULLY REPRODUCED. The approved 6-qubit VQC compiles 
   onto Processor B with depth 15, 5 CX gates, and exactly 0 SWAPs, 
   empirically confirming the architectural foresight of Decision D3.
3. CAPACITY ENFORCEMENT: VERIFIED. Processor A correctly rejects the 6-qubit 
   circuit with CircuitTooWideForTarget, adhering to Challenge Kit Section 3.1.
4. SIMULATION QUALIFICATIONS IDENTIFIED:
   - Aer EstimatorV2 does not simulate readout error channels (operator evaluation).
   - In the initial benchmark run, the uncompiled 6Q circuit was simulated, 
     omitting 1Q depolarizing error on native basis gates.
   - The claim of "high noise tolerance" based on a single sample comparison 
     is statistically invalid and must be formally retracted/corrected.
================================================================================
```

---

## 2. Audit of Specifications vs. Exploratory Alternatives

### 2.1 Official Specification Compliance (Updated Challenge Kit, Oct 12, 2026)
- **Processor A (`processors/processor_A.json`):**
  - Physical Qubits: **5**
  - Coupling Map: 1D linear chain `0–1–2–3–4` (8 directed edges: `[[0,1],[1,0],[1,2],[2,1],[2,3],[3,2],[3,4],[4,3]]`).
  - Basis Gates: `['rz', 'sx', 'x', 'cx']`.
  - Noise Model: $p_{1q} = 0.001$, $p_{2q} = 0.005$, $p_{ro} = 0.01$.
  - **Verdict:** **100% COMPLIANT** with `Updated_Challenge_Kit.pdf` Section 3.1 & 3.4.

- **Processor B (`processors/processor_B.json`):**
  - Physical Qubits: **9**
  - Coupling Map: Heavy-hex-inspired sparse tree (16 directed edges: `0–1, 1–2, 2–3, 2–4, 4–5, 5–6, 4–7, 7–8`).
  - Basis Gates: `['rz', 'sx', 'x', 'cx']`.
  - Noise Model: $p_{1q} = 0.001$, $p_{2q} = 0.005$, $p_{ro} = 0.01$.
  - **Verdict:** **100% COMPLIANT** with `Updated_Challenge_Kit.pdf` Section 3.2 & 3.4.

### 2.2 Exploratory Alternatives Status
- `processors/processor_A_branching.json` (5-qubit T-branching tree) and `processors/processor_B_cyclic.json` (9-qubit 12-edge cyclic mesh) derive from the pre-release organizer approval document (`processor_ab_benchmark.pdf`, Oct 11).
- **Audit Mandate:** Both files are verified as valuable exploratory comparators that illustrate routing penalties, but they **must not** be described as official Phase 1 benchmark targets in the final submission.

---

## 3. Processor A Capacity Rejection & 5-Qubit Reference Circuit

### 3.1 Verification of Capacity Constraint
When `transpile_for_processor_a()` is invoked with the approved 6-qubit VQC (`src/vqc_circuit.py`), the function immediately detects `circuit.num_qubits > 5` and returns:
- `success: False`
- `capacity_exceeded: True`
- `error_type: "CircuitTooWideForTarget"`
- `message`: Directly references Challenge Kit Section 3.1 (*"For a problem requiring more than 5 logical qubits, do not delete variables merely to force the full problem into A. Treat A as a capacity/routing reference and perform the full-size execution on Processor B where permitted."*).
- **Verdict:** **VERIFIED**. Prevents arbitrary deletion of clinical ECG features.

### 3.2 5-Qubit Reference Circuit Qualification
The 5-qubit linear VQC reference circuit evaluated in the report:
- Logical Qubits: 5 (5 $R_y$ feature gates, 10 variational parameters, 4 linear CX gates).
- **Audit Mandate:** Must be strictly documented as a **team-selected synthetic comparator** used solely to evaluate Processor A's routing dynamics. It is **not** an approved clinical classifier for PS-Q1.

---

## 4. Independent Reproduction of Processor B Transpilation

### 4.1 Transpilation Parameters
- Circuit: Approved 6-qubit VQC (`build_vqc_circuit`)
- Coupling Map: Processor B Canonical (`build_processor_b_coupling_map()`)
- Basis Gates: `['rz', 'sx', 'x', 'cx']`
- Optimization Level: `1`
- Seed Transpiler: `42`

### 4.2 Reproduced Resource Metrics
| Metric | Reported Value | Reproduced Audit Value | Discrepancy |
| :--- | :---: | :---: | :---: |
| **Physical Qubits** | 9 | 9 | None |
| **Logical Qubits** | 6 | 6 | None |
| **Transpiled Depth** | **15** | **15** | None |
| **Total Operations** | **65** | **65** | None |
| **Single-Qubit Gates** | 60 (36 `rz`, 24 `sx`) | 60 (36 `rz`, 24 `sx`) | None |
| **Two-Qubit Gates (`cx`)** | **5** | **5** | None |
| **SWAP Count** | **0** | **0** | None |
| **Routing Overhead ($\Delta N_{\text{CX}}$)** | **0** | **0** | None |
| **Physical Layout Mapping** | `[0, 1, 2, 4, 5, 6]` | `[0, 1, 2, 4, 5, 6]` | None |
| **Physical Ancillae** | `[3, 7, 8]` | `[3, 7, 8]` | None |

**Architectural Assessment:**
The reproduction confirmed that the compiled circuit matches the logical circuit's 5 CX gates with zero routing overhead. This independently validates that Architectural Decision D3 (`entanglement="linear"`) completely eliminates SWAP routing bottlenecks on Processor B.

---

## 5. Deep Technical Audit of Noisy Aer Simulation

### 5.1 Critical Audit Findings on `EstimatorV2` Execution

#### Finding 1: Readout Error Omission in `EstimatorV2` (Issue SIM-01)
Source inspection of Qiskit Aer 0.17.2 (`qiskit_aer.primitives.EstimatorV2._run_pub`) reveals that `EstimatorV2` evaluates expectation values by calling `circuit.save_expectation_value(Pauli(pauli))`. 
- **Mechanism:** Operator expectation values are calculated directly via statevector/density-matrix contraction ($\text{Tr}(\rho O)$).
- **Consequence:** Because the circuit contains no measurement instructions, `ReadoutError` channels in the `NoiseModel` are **never executed**.
- **Correction:** The report must clearly disclose that the reported noisy simulation reflects **unitary gate depolarizing errors only**, and does not include classical measurement bit-flip noise.

#### Finding 2: Uncompiled Logical Circuit vs. Transpiled Physical Circuit (Issue SIM-02)
In the initial benchmark run (`results/processor_ab_transpilation.json`), `simulate_processor_b` was passed the uncompiled logical circuit `qc_logical` (6 qubits, containing 18 `ry` gates and 5 `cx` gates).
- **Mechanism:** The `NoiseModel` registered 1Q depolarizing error only on native gates `['x', 'sx']`.
- **Consequence:** 1Q depolarizing errors were **not applied** to the `ry` gates in `qc_logical`. Only the 5 `cx` gates experienced error channels.
- **Physical Transpiled Execution:**
  When the circuit is first transpiled to the native basis `{rz, sx, x, cx}` on the 9-qubit coupling map, and evaluated against the re-indexed 9-qubit physical observable:
  $$O_{\text{phys}} = \frac{1}{6}(Z_0 + Z_1 + Z_2 + Z_4 + Z_5 + Z_6)$$
  all 24 `sx` gates correctly undergo 1Q depolarizing errors.

#### Finding 3: Seeding in `EstimatorV2` (Issue SIM-03)
In Aer's `EstimatorV2`, the Gaussian finite-shot sampler draws random perturbations using:
```python
rng = np.random.default_rng(self.options.run_options.get("seed_simulator"))
```
In `simulate_processor_b()`, `seed_simulator` was passed under `backend_options`, causing `run_options.get("seed_simulator")` to evaluate to `None`. As a result, repeated calls produced slightly different sample noise values. Passing `seed_simulator` under `run_options` restores bit-exact determinism.

### 5.2 Comparative Numerical Execution Across Regimes

| Simulation Regime | Input Circuit | Observable | Seeding | Expectation Value | Shift vs. Ideal |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Ideal Statevector** | Logical (6Q) | Logical 6Q $\bar{Z}$ | N/A | **0.240036** | 0.000000 |
| **Reported Initial Noisy** | Logical (6Q) | Logical 6Q $\bar{Z}$ | Unseeded Sampler | **0.234710** | -0.005327 |
| **Deterministic Seeded Logical** | Logical (6Q) | Logical 6Q $\bar{Z}$ | `run_options` Seed 42 | **0.242904** | +0.002868 |
| **Deterministic Seeded Transpiled** | Transpiled (9Q) | Physical 9Q $O_{\text{phys}}$ | `run_options` Seed 42 | **0.241681** | +0.001645 |

*Note:* All values remain well within the finite-shot sampling error window ($\sigma = 1/\sqrt{4096} = 0.015625$).

---

## 6. Scientific Retraction & Correction of Noise Resilience Claims

In `report/processor_ab_topology_research.md` (Section 7), the following claim was made:
> *"The noise shift $|\Delta E| \approx 0.0053$ is well within the 1-sigma shot noise window ($\sigma = 0.0156$), demonstrating high noise tolerance on this topology."*

### Scientific Correction:
This statement is **statistically invalid and must be corrected**:
1. **Conflating Sampling Error with Hardware Resilience:** The theoretical standard error $\sigma = 1/\sqrt{N_{\text{shots}}} = 0.015625$ measures statistical variance arising from finite quantum measurement sampling. It does **not** quantify hardware error resilience.
2. **Single-Point Evaluation Fallacy:** Observing a small shift $|\Delta E|$ at a single arbitrary parameter vector ($\boldsymbol{\theta} = \mathbf{0}$) on a single sample cannot support a generalized claim of classifier noise resilience. The small shift could be caused by shot-noise cancellation or low sensitivity of the observable at that specific point in Hilbert space.
3. **Proper Protocol for Noise Resilience:** True noise resilience can only be demonstrated by evaluating the full 200-beat training set and 100-beat test set, and comparing clinical classification metrics (macro F1, sensitivity, specificity, Brier loss) between ideal and noisy execution.

---

## 7. Numerical Consistency Verification

All values in `results/processor_ab_transpilation.json` were cross-checked against the audit findings:
- Uncompiled Depth (8) and Ops (18 `ry`, 5 `cx`): **MATCH**
- Processor A 6Q `CircuitTooWideForTarget`: **MATCH**
- Processor A 5Q Line Depth (14), CX (4), SWAPs (0): **MATCH**
- Processor A 5Q Tree Depth (21), CX (7), SWAPs (1): **MATCH**
- Processor B 6Q Depth (15), CX (5), SWAPs (0): **MATCH**
- Simulator Shots (4096), Precision ($0.015625$): **MATCH**

---

## 8. Test Suite Status

- **Processor A/B Test Suite (`tests/test_processor_ab.py`):** **10/10 passed in 3.29s**
- **Full Project Test Suite (`pytest`):** **94/94 passed in 5.15s** (100% passing rate across all 8 test modules; zero regressions).

---

## 9. Required Report Corrections & Action Items

Before incorporating this work into the final Phase 1 submission report:
1. **Update `report/processor_ab_topology_research.md` Section 7:** Replace the "high noise tolerance" claim with the rigorous explanation that single-point shifts reflect finite sampling variance and that full cohort evaluation is required.
2. **Update `processors/processor_b.py` `simulate_processor_b()`:**
   - Ensure `seed_simulator` is passed in `run_options` to guarantee deterministic sampling.
   - Add support for automatically transpiling the circuit and mapping the observable to the physical layout before simulation.
3. **Retain Exploratory Labels:** Ensure `processor_A_branching.json` and `processor_B_cyclic.json` are explicitly introduced as exploratory study architectures.

---

## 10. Technical Lead Handover & Next Milestone Recommendation

### Handover Verdict: **CONDITIONAL PASS**
The Processor A and Processor B topology research, configuration models, and transpilation benchmarks are technically sound, reproducible, and ready for official submission once the reporting qualifications noted above are applied.

### Recommended Next Milestone:
Proceed immediately to **Milestone 5F.3, Step 2: Pre-Training Baseline Diagnostics & Forward-Pass Prototyping**.

**Justification:**
With Processor B's 9-qubit hardware mapping proven to incur **0 SWAPs and 0 routing overhead**, the technical lead can proceed with training optimization knowing that the mathematical VQC will compile cleanly onto the primary execution target. Evaluation of classifier noise degradation will be formally conducted during Step 4 using full cohort validation.
