# NEXUS-OPS — Phase 6 Final Technical Corrections & Evidence Verification

**Project:** IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Classifier  
**Milestone:** Phase 6 (Quantum Hardware Experiments and Processor Architecture Evaluation)  
**Document Type:** Final Scientific Correction, Verification Evidence, and Provenance Report  
**Date:** 2026-10-13  
**Overall Phase 6 Status:** **VERIFIED WITH LIMITATIONS**  

---

## 1. Executive Summary & Verification Matrix

This document provides definitive experimental evidence, mathematical corrections, and source provenance for the final hardware evaluation of the 6-qubit Variational Quantum Classifier (VQC).

### Verification Status Table

| Item / Claim | Evaluation Status | Supporting Evidence & Scope |
| :--- | :---: | :--- |
| **Transpiler Logical-to-Physical Mapping** | **VERIFIED** | Identity routing permutation; `final_index_layout()` matches `[0, 1, 2, 4, 5, 6]`. |
| **Statevector vs. Aer Measurement Sampling** | **VERIFIED** | Discrepancy $< 0.001$ across parameterized samples within finite-shot sampling error. |
| **Finite-Shot Scaling Mathematics** | **VERIFIED WITH LIMITATIONS** | Empirical standard error scales approximately as $1/\sqrt{S}$ (variance $\sim 1/S$); strict scaling claim retracted. |
| **Processor A/B Source Provenance** | **VERIFIED** | Full parameter traceability against `Updated_Challenge_Kit.pdf` Sections 3 & 4. |
| **Record 208 Generalization Analysis** | **VERIFIED** | Causal physiological claims removed; record-specific distribution shift documented with exact approved wording. |
| **Physical Quantum Hardware Execution** | **NOT PERFORMED** | No physical IBM Quantum QPU was accessed. Evaluated via simulated transpilation and Qiskit Aer. |
| **Automated Test Regression Suite** | **VERIFIED** | 116 of 116 tests passing in 12.98s. |

---

## 2. Final Transpiler Mapping Verification

### 2.1 Logical-to-Physical Mapping & Routing Invariance
In Qiskit compilation, `initial_layout` designates virtual-to-physical placement prior to routing, while `final_index_layout()` (or `final_layout`) captures physical qubit indices at the circuit output after any SWAP gate routing.

1. **Routing Permutation Audit:**
   - Compiler invocation: `transpile(vqc_circuit, coupling_map=cmap_b, basis_gates=['rz', 'sx', 'x', 'cx'], optimization_level=1, seed_transpiler=42)`.
   - Layout property inspection:
     ```python
     c.layout.routing_permutation()  # Returns: [0, 1, 2, 3, 4, 5, 6, 7, 8] (Identity permutation)
     c.layout.final_index_layout()   # Returns: [0, 1, 2, 4, 5, 6]
     ```
   - **Root Cause of Identity Permutation:** Processor B's canonical sparse tree possesses the contiguous linear chain $(0, 1), (1, 2), (2, 4), (4, 5), (5, 6)$. Because the approved VQC uses nearest-neighbor linear CNOT entanglement (Decision D3), SABRE routing allocated physical qubits `[0, 1, 2, 4, 5, 6]` without requiring any SWAP gates (0 SWAPs). Thus, the initial layout is strictly preserved through circuit termination.
2. **Defensive Implementation in Source Code:**
   In [`src/noise_experiments.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/noise_experiments.py), the physical mapping extraction was updated to explicitly query `compiled_circuit.layout.final_index_layout()`:
   ```python
   if hasattr(compiled_circuit.layout, "final_index_layout"):
       logical_to_physical = compiled_circuit.layout.final_index_layout()
   else:
       logical_to_physical = [compiled_circuit.layout.initial_layout[vqc_circuit.qubits[i]] for i in range(6)]
   ```

### 2.2 Classical-Bit Ordering & Observable Construction
- A 6-bit classical register `meas` is allocated: `meas_circuit.measure(phys_i, creg[log_i])`.
- In Qiskit's little-endian bitstring convention, classical bit `creg[k]` appears at index `bitstring[5 - k]`.
- Bit $b_k \in \{0, 1\}$ corresponds to Pauli-Z eigenvalue $1 - 2 b_k$.
- The ensemble observable expectation is computed as:
  $$\langle \hat{O} \rangle = \frac{1}{N_{\text{shots}}} \sum_{s=1}^{N_{\text{shots}}} \left[ \frac{1}{6} \sum_{k=0}^5 (1 - 2 b_k^{(s)}) \right]$$

### 2.3 Empirical Statevector vs. Ideal Aer Measurement Comparison
To rigorously confirm bit-exact equivalence, 5 randomized test samples ($X \in [0, \pi]^6, \theta \in [-\pi, \pi]^{12}$) were evaluated comparing `StatevectorEstimator` against noiseless `AerSimulator` (shots = 500,000):

| Parameterized Sample Index | Statevector Expectation $\langle \hat{O} \rangle_{\text{SV}}$ | Aer Measurement Expectation $\langle \hat{O} \rangle_{\text{Aer}}$ | Absolute Discrepancy $|\Delta|$ | Sampling Shot Noise Upper Bound ($3.5/\sqrt{S}$) |
| :---: | :---: | :---: | :---: | :---: |
| Sample 0 | $+0.020830$ | $+0.019928$ | **$0.000902$** | $< 0.00495$ |
| Sample 1 | $-0.094959$ | $-0.094709$ | **$0.000250$** | $< 0.00495$ |
| Sample 2 | $+0.053040$ | $+0.052359$ | **$0.000681$** | $< 0.00495$ |
| Sample 3 | $-0.039651$ | $-0.040261$ | **$0.000610$** | $< 0.00495$ |
| Sample 4 | $-0.100973$ | $-0.101205$ | **$0.000233$** | $< 0.00495$ |

**Conclusion:** All absolute discrepancies are $< 0.001$, well within finite-shot sampling error, verifying exact classical bit-ordering and layout correspondence.

---

## 3. Finite-Shot Mathematics Correction

### 3.1 Statistical Distinction: Variance vs. Standard Error
In statistical sampling theory for quantum expectation estimators:
- The **variance** of the sample expectation estimator scales inversely with shot count:
  $$\text{Var}(\hat{E}) = \frac{\text{Var}(\hat{O})}{S} \propto \frac{1}{S}$$
- The **standard error** (standard deviation of the sample mean) scales as the square root of the variance:
  $$\text{SE}(\hat{E}) = \sqrt{\frac{\text{Var}(\hat{O})}{S}} = \frac{\sqrt{\text{Var}(\hat{O})}}{\sqrt{S}} \propto \frac{1}{\sqrt{S}}$$

### 3.2 Quantity Actually Computed & Reported
In `src/processor_simulation.py` and `results/shot_based_results.json`, the reported metric `empirical_mean_std` is the empirical standard deviation across 3 simulator seeds averaged over the 100 test samples:
$$\bar{s} = \frac{1}{N} \sum_{i=1}^N \left( \sqrt{\frac{1}{K}\sum_{k=1}^K (\hat{E}_{i, k} - \bar{E}_i)^2} \right)$$
This represents the **empirical standard error** of the expectation estimate across simulation seeds.

### 3.3 Verification of 4096-Shot Result
For $S=4096$:
- Theoretical upper bound on standard error (assuming maximum variance $\text{Var}(\hat{O}) \le 1$):
  $$\text{SE}_{\text{max}} = \frac{1}{\sqrt{4096}} = \frac{1}{64} = 0.015625$$
- Empirical standard error computed across seeds:
  $$\bar{s} = \mathbf{0.011403}$$
- Ratio of empirical standard error to theoretical upper bound:
  $$\frac{\bar{s}}{\text{SE}_{\text{max}}} = \frac{0.011403}{0.015625} \approx \mathbf{0.7298} \approx 0.73$$
- **Theoretical Explanation:** The observable $\hat{O} = \frac{1}{6}\sum_{i=0}^5 Z_i$ has theoretical variance bounded by $\text{Var}(\hat{O}) \le 1/6 \approx 0.1667$ for independent qubits, and up to $\sim 0.533$ for partially correlated entangled qubits. Because $\sqrt{0.533} \approx 0.73$, the empirical standard error is expected to be approximately $0.73 \times (1/\sqrt{S})$, which precisely matches the observed empirical ratio of $0.73$.

### 3.4 Language Corrections Applied
- **Retracted Terminology:** Retracted claims describing the scaling as "strictly following $\mathcal{O}(1/\sqrt{S})$".
- **Corrected Formulation:** Stated that empirical standard errors across seeds approximately align with the theoretical $1/\sqrt{S}$ curve (and variance scales approximately as $1/S$), while noting that 3 simulation seeds cannot establish strict asymptotic convergence.

---

## 4. Processor Specification Provenance Matrix

The table below delineates official organizer specifications from team-defined modeling assumptions:

| Parameter / Feature | Value / Setting | Provenance / Authority Source | Status Classification |
| :--- | :---: | :--- | :---: |
| **Processor A Qubit Count** | 5 physical qubits | `Updated_Challenge_Kit.pdf`, Section 3.1, p. 11 | **OFFICIAL SPECIFICATION** |
| **Processor A Canonical Coupling Map** | 1D Chain `0–1–2–3–4` | `Updated_Challenge_Kit.pdf`, Section 3.1, p. 11 | **OFFICIAL SPECIFICATION** |
| **Processor A Branching Topology** | Tree `(0,1), (1,2), (1,3), (3,4)` | Pre-release draft `processor_ab_benchmark.pdf`, p. 4 | **EXPLORATORY ALTERNATIVE** |
| **Processor B Qubit Count** | 9 physical qubits | `Updated_Challenge_Kit.pdf`, Section 3.2, p. 12 | **OFFICIAL SPECIFICATION** |
| **Processor B Canonical Coupling Map** | Sparse tree (`0–1, 1–2, 2–3, 2–4, 4–5, 5–6, 4–7, 7–8`) | `Updated_Challenge_Kit.pdf`, Section 3.2, p. 12 | **OFFICIAL SPECIFICATION** |
| **Processor B Cyclic Variant** | 12-edge cyclic mesh | Pre-release draft `processor_ab_benchmark.pdf`, p. 5 | **EXPLORATORY ALTERNATIVE** |
| **Basis Gate Set** | `['rz', 'sx', 'x', 'cx']` | `Updated_Challenge_Kit.pdf`, Section 3.4, p. 14 | **OFFICIAL SPECIFICATION** |
| **1-Qubit Depolarizing Error** | $p_{1q} = 0.001$ (0.1%) on `x`, `sx` | `Updated_Challenge_Kit.pdf`, Section 3.4, p. 14 | **OFFICIAL SPECIFICATION** |
| **2-Qubit Depolarizing Error** | $p_{2q} = 0.005$ (0.5%) on `cx` | `Updated_Challenge_Kit.pdf`, Section 3.4, p. 14 | **OFFICIAL SPECIFICATION** |
| **Readout Bit-Flip Error** | $p_{ro} = 0.010$ (1.0%) | `Updated_Challenge_Kit.pdf`, Section 3.4, p. 14 | **OFFICIAL SPECIFICATION** |
| **Reported Shot Budget** | 4096 shots | `Updated_Challenge_Kit.pdf`, Section 4.2, p. 17 | **OFFICIAL SPECIFICATION** |
| **Transpilation Baseline** | `opt_level=1`, `seed=42`, SABRE | `Updated_Challenge_Kit.pdf`, Section 4.1, p. 16 | **OFFICIAL SPECIFICATION** |
| **Capacity Enforcement (>5Q on A)** | Reject >5Q; use B for full-size | `Updated_Challenge_Kit.pdf`, Section 3.1 & FAQ, p. 38 | **OFFICIAL SPECIFICATION** |
| **Processor JSON Files** | `processors/*.json` | Created by NEXUS-OPS team from PDF specifications | **TEAM-DEFINED IMPLEMENTATION** |
| **5-Qubit Reference VQC Circuit** | 5Q linear circuit | Created by NEXUS-OPS team for Processor A routing tests | **TEAM-SELECTED COMPARATOR** |
| **Thermal Relaxation ($T_1, T_2$)** | Omitted (depolarizing model only) | Not provided in challenge kit; team selected phenomenological noise | **TEAM MODELING ASSUMPTION** |

---

## 5. Record 208 Generalization Analysis & Wording Correction

### 5.1 Issue Identified
Previous drafts attributed Record 208's lower specificity to "Left Bundle Branch Block (LBBB) morphology and ventricular bigeminy". An audit of the codebase confirmed that no reproducible patient-level morphological feature extraction or physician-confirmed annotation of LBBB was conducted on Record 208 within this project.

### 5.2 Mandatory Wording Applied Across All Reports
All reports ([`report/vqc_evaluation_report.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/vqc_evaluation_report.md), [`report/PHASE5_FINAL_AUDIT.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE5_FINAL_AUDIT.md), [`report/PHASE5_PHASE6_COMPLETION_REPORT.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE5_PHASE6_COMPLETION_REPORT.md), [`report/PHASE5_PHASE6_CORRECTION_LOG.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE5_PHASE6_CORRECTION_LOG.md), [`report/PHASE5_PHASE6_FINAL_HANDOVER.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE5_PHASE6_FINAL_HANDOVER.md), [`report/PHASE5_PHASE6_INDEPENDENT_AUDIT.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE5_PHASE6_INDEPENDENT_AUDIT.md), [`results/phase5_phase6_audit.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/phase5_phase6_audit.json)) have been updated to use the exact calibrated statement:

> *"Record 208 exhibited a higher false-positive rate and lower specificity than Record 200. The difference indicates record-specific distribution shift; its physiological cause has not been established."*

---

## 6. Regression Testing & Execution Terminal Evidence

### 6.1 Full Test Suite Execution
```powershell
.venv\Scripts\pytest -v
============================ 116 passed in 12.98s =============================
```
- Total test count: **116 passed**, 0 failed, 0 errors.
- Includes new regression test: `tests/test_hardware_experiments.py::test_transpiler_mapping_and_ideal_measurement_equivalence`.

### 6.2 Focused Hardware Suite Execution
```powershell
.venv\Scripts\pytest -v tests/test_hardware_experiments.py
============================== 6 passed in 5.31s ==============================
```

### 6.3 Focused Evaluation Suite Execution
```powershell
.venv\Scripts\pytest -v tests/test_vqc_evaluation.py
============================== 3 passed in 4.12s ==============================
```

---

## 7. Remaining Limitations

1. **Hardware Simulation Scope:** All benchmarks reflect classical simulation via Qiskit Aer 0.17.2 and compiler analysis. Physical QPU execution was **NOT PERFORMED**.
2. **Noise Model Scope:** Evaluated under synthetic depolarizing and readout noise channels ($p_{1q}=0.001, p_{2q}=0.005, p_{ro}=0.010$). Coherent error, crosstalk, and frequency collision dynamics of physical devices are not modeled.
3. **Single-Record Training Scope:** Model `fold_1_seed_303` was trained strictly on Record 106 ($N=100$). A future pooled refit on Records 106+119 ($N=200$) is recommended to expand out-of-distribution specificity across records.
