# NEXUS-OPS — Phase 6 Final Evidence Reconciliation Report
## IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Signal Classifier

**Document Version:** 1.0  
**Audit Date:** 2026-10-13  
**Auditor:** Senior Quantum Machine Learning Research Auditor & Hardware Architecture Specialist  
**Project Workspace:** `c:\Data\Projects\NEXUS-OPS\NEXUS-OPS\PS-Q1-Biomedical-Classifier`  
**Milestone:** Phase 6 (Quantum Hardware Experiments & Processor Architecture Evaluation)  
**Overall Phase Status:** **`VERIFIED WITH LIMITATIONS`**

---

## 1. Executive Summary & Audit Mandate

This report represents the conclusive, definitive evidence reconciliation for **Phase 6: Quantum Hardware Experiments and Processor Architecture Evaluation** of the NEXUS-OPS Biomedical Signal Classifier project. Following the initial technical correction report ([`report/PHASE6_FINAL_TECHNICAL_CORRECTIONS.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE6_FINAL_TECHNICAL_CORRECTIONS.md)), an independent verification identified four critical evidence gaps that required rigorous mathematical derivation, empirical verification, and direct document provenance:

1. **Ensemble-Observable Variance & Covariance Claim:** The theoretical justification and empirical foundation of the ensemble observable $\hat{O} = \frac{1}{6}\sum_{i=0}^5 Z_i$ were investigated. The previous report's citation of a "0.533 measured covariance" figure was formally audited, found to be an inverted back-calculation rather than a measured covariance, and is hereby retracted and replaced with exact quantum state variance calculations.
2. **Statevector vs. Aer Sampler Test Reconciliation:** Discrepancies between shot counts reported in documentation (500,000 shots), executed in the unit test suite (50,000 shots in [`tests/test_hardware_experiments.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests/test_hardware_experiments.py)), and run during diagnostic investigations (100,000 and 200,000 shots) have been fully traced, benchmarked, and reconciled.
3. **Hardware Specification Provenance & Direct Quotations:** All processor specifications, coupling topologies, basis gates, synthetic noise rates, and capacity rules have been validated against the authoritative organizer reference ([`docs/challenge_materials/Updated_Challenge_Kit.pdf`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/docs/challenge_materials/Updated_Challenge_Kit.pdf)) with exact page numbers, sections, and verbatim quotations.
4. **Repository Integrity & Git Tracking Status:** Cleanliness of tracked git files and full classification of untracked files and backups have been established.

### Strict Governance & Boundaries Adhered To
- **Zero Redesign:** The approved 6-qubit VQC architecture (RY encoding, linear RealAmplitudes, 12 trainable parameters, average Pauli-Z observable) remains strictly frozen.
- **Zero Retraining:** The 10 training runs and frozen optimal checkpoint `fold_1_seed_303` ($\theta^*$) remain untouched.
- **Zero False Hardware Claims:** All quantum hardware experiments are strictly identified as simulated transpilation and Qiskit Aer 0.17.2 noise modeling. Physical quantum hardware execution is explicitly marked **`NOT PERFORMED`**.
- **Permitted Status Terminology:** Only the authorized statuses (`VERIFIED`, `VERIFIED WITH LIMITATIONS`, `PARTIAL`, `NOT VERIFIED`, `NOT PERFORMED`) are employed.

---

## 2. Task 1 — Rigorous Mathematical & Empirical Resolution of Observable Variance

### 2.1 Theoretical Operator Derivation
The team-approved classification observable for the 6-qubit Variational Quantum Classifier is the equal-weight ensemble Pauli-Z operator:
$$\hat{O} = \frac{1}{6} \sum_{j=0}^5 Z_j$$

To establish the quantum variance $\text{Var}_{\psi}(\hat{O}) = \langle \hat{O}^2 \rangle_{\psi} - \langle \hat{O} \rangle_{\psi}^2$, we expand the square of the operator:
$$\hat{O}^2 = \left( \frac{1}{6} \sum_{j=0}^5 Z_j \right)^2 = \frac{1}{36} \left( \sum_{j=0}^5 Z_j^2 + 2 \sum_{0 \le j < k \le 5} Z_j Z_k \right)$$

Because Pauli operators satisfy $Z_j^2 = I$ for all $j \in \{0, \dots, 5\}$:
$$\sum_{j=0}^5 Z_j^2 = 6 I$$
$$\hat{O}^2 = \frac{6}{36} I + \frac{2}{36} \sum_{0 \le j < k \le 5} Z_j Z_k = \frac{1}{6} I + \frac{1}{18} \sum_{0 \le j < k \le 5} Z_j Z_k$$

Taking the quantum expectation value with respect to a normalized pure state $|\psi\rangle$:
$$\langle \hat{O}^2 \rangle_{\psi} = \frac{1}{6} + \frac{1}{18} \sum_{0 \le j < k \le 5} \langle Z_j Z_k \rangle_{\psi}$$

Therefore, the exact state-dependent quantum variance is:
$$\text{Var}_{\psi}(\hat{O}) = \frac{1}{6} + \frac{1}{18} \sum_{0 \le j < k \le 5} \langle Z_j Z_k \rangle_{\psi} - \langle \hat{O} \rangle_{\psi}^2$$

Alternatively, in terms of individual single-qubit variances $\text{Var}_{\psi}(Z_j) = 1 - \langle Z_j \rangle_{\psi}^2$ and pairwise covariances $\text{Cov}_{\psi}(Z_j, Z_k) = \langle Z_j Z_k \rangle_{\psi} - \langle Z_j \rangle_{\psi} \langle Z_k \rangle_{\psi}$:
$$\text{Var}_{\psi}(\hat{O}) = \frac{1}{36} \sum_{j=0}^5 \text{Var}_{\psi}(Z_j) + \frac{2}{36} \sum_{0 \le j < k \le 5} \text{Cov}_{\psi}(Z_j, Z_k)$$

There are 15 distinct pairwise terms ($j < k$). Because eigenvalues of $Z_j$ are $\pm 1$, the operator norm satisfies $\|\hat{O}\| \le 1$, giving the strict analytical upper bound $\text{Var}_{\psi}(\hat{O}) \le 1$. If all qubits were completely uncorrelated with zero expectation, $\text{Var}(Z_j) = 1$ and $\text{Cov}(Z_j, Z_k) = 0$, yielding $\text{Var}(\hat{O}) = \frac{6}{36} = \frac{1}{6} \approx 0.1667$. Entangled or correlated states with positive longitudinal alignment produce higher variance, up to $\text{Var}(\hat{O}) = 1$ in macroscopic superposition states $\frac{1}{\sqrt{2}}(|000000\rangle + |111111\rangle)$.

### 2.2 Exact Quantum State Variance Across Held-Out Test Samples
To eliminate speculative assumptions, the exact quantum state variance was computed directly across all $N = 100$ held-out test samples ($X_{\text{test}} \in \mathbb{R}^{100 \times 6}$ from Records 200 and 208) using the frozen optimal parameter vector $\theta^* \in \mathbb{R}^{12}$ (`fold_1_seed_303`):

| Statistical Quantity | Analytical / Empirical Value | Notes |
|:---|:---:|:---|
| **Mean Quantum State Variance** $\overline{\text{Var}_{\psi}(\hat{O})}$ | **$0.334035$** | Direct statevector expectation of $\hat{O}^2 - \langle \hat{O} \rangle^2$ |
| **Standard Deviation of Variance** $\sigma(\text{Var}_{\psi}(\hat{O}))$ | $0.126820$ | Dispersion across 100 distinct patient test feature vectors |
| **Minimum State Variance** $\min_i \text{Var}_{\psi_i}(\hat{O})$ | $0.127490$ | Sample displaying high single-qubit alignment / lower entropy |
| **Maximum State Variance** $\max_i \text{Var}_{\psi_i}(\hat{O})$ | $0.623930$ | Sample with significant correlated superposition structure |
| **Mean State Standard Deviation** $\overline{\sqrt{\text{Var}_{\psi}(\hat{O})}}$ | **$0.567699$** | Single-shot standard deviation of $\hat{O}$ per quantum measurement |
| **Noiseless Theoretical SE at $S = 4096$** | **$0.008870$** | $\frac{\overline{\sqrt{\text{Var}_{\psi}}}}{\sqrt{4096}} = \frac{0.567699}{64}$ |
| **Upper Bound Standard Error at $S = 4096$** | $0.015625$ | Worst-case bound $\frac{1}{\sqrt{S}} = \frac{1}{64}$ (assuming maximum variance $\text{Var} = 1$) |

### 2.3 Deconstruction of `empirical_mean_std` in `processor_simulation.py`
In [`src/processor_simulation.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/processor_simulation.py) (lines 161–165), the finite-shot simulation computes `empirical_mean_std`:
```python
# Calculate empirical standard deviation across seeds for each sample, then average
all_evs_arr = np.array(all_evs)  # shape: (num_seeds, num_samples) = (3, 100)
sample_stds = np.std(all_evs_arr, axis=0)
empirical_sigma = float(np.mean(sample_stds))
```
- **What this represents:** For each sample $i \in \{1, \dots, 100\}$, the standard deviation of the measured expectation $\hat{E}_{i, k}$ across $K = 3$ simulation seeds (seeds 42, 101, 202) is computed. Then, the arithmetic mean of these 100 standard deviations is reported as `empirical_mean_std`. This is an **empirical standard error across simulation runs**, not a cross-sample standard deviation.
- **Measured Value at $S = 4096$:** $\bar{s} = \mathbf{0.011403298}$.
- **Comparison to Noiseless Expectation:**
  $$\bar{s} = 0.011403 > \text{SE}_{\text{noiseless}} = 0.008870$$
- **Root Cause of Discrepancy:**
  The simulation in `processor_simulation.py` executes using `build_processor_b_noise_model()` ($p_{1q} = 0.001$, $p_{2q} = 0.005$, $p_{\text{meas}} = 0.010$). Depolarizing errors and readout bit-flips perturb the measurement bitstrings non-trivially, injecting additional run-to-run stochastic variance beyond ideal multinomial shot sampling. Furthermore, estimating standard error using only $K = 3$ simulator seeds introduces small-sample statistical dispersion.

### 2.4 Formal Retraction of the "0.533" Covariance Claim
- **Origin of the Retracted Claim:**
  In the prior Phase 6 technical corrections report, the ratio between the measured empirical standard error $\bar{s} = 0.011403298$ and the conservative upper-bound standard error $\text{SE}_{\max} = \frac{1}{\sqrt{4096}} = 0.015625$ was computed:
  $$\frac{\bar{s}}{\text{SE}_{\max}} = \frac{0.011403298}{0.015625} = 0.729811$$
  Squaring this ratio gives:
  $$(0.729811)^2 = 0.532624 \approx \mathbf{0.533}$$
  In the previous text, this quantity was mistakenly termed a *"measured covariance of ~0.533"*.
- **Retraction Statement:**
  > **FORMAL RETRACTION:** The claim that $0.533$ represents a measured quantum covariance is factually incorrect and is hereby formally retracted. $0.533$ was an inverted back-calculation derived from the ratio of noisy 3-seed simulation dispersion to the worst-case variance bound ($(\bar{s} \times \sqrt{S})^2$). It is not a measured covariance.
- **Verified Replacement:**
  The true measured quantum state variance across all 100 test samples is $\overline{\text{Var}(\hat{O})} = \mathbf{0.334035}$, producing an ideal shot-noise standard error of $\mathbf{0.008870}$ at $S = 4096$. The empirical 3-seed noisy simulation dispersion of $0.011403$ reflects the combined influence of finite shot sampling, synthetic gate/readout noise, and small seed sample size ($K=3$).
- **Status:** **`VERIFIED WITH LIMITATIONS`**

---

## 3. Task 2 — Statevector vs. Aer Sampler Test Evidence Reconciliation

### 3.1 Traceability of Test Files, Functions, and Shot Budgets
During prior audits, a discrepancy was noted between documentation stating 500,000 shots and test assertions. The investigation confirms the distinct operational roles of each file:

1. **Continuous Integration Unit Test:**
   - **File:** [`tests/test_hardware_experiments.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests/test_hardware_experiments.py)
   - **Function:** `test_transpiler_mapping_and_ideal_measurement_equivalence`
   - **Shot Budget:** **$S = 50,000$ shots per sample**
   - **Execution Time:** $\approx 2.5$ seconds total for 5 samples.
   - **Pass Criterion:** Discrepancy $|\langle\hat{O}\rangle_{\text{exact}} - \langle\hat{O}\rangle_{\text{Aer}}| < 0.015$ (approximately $3.5 \times \text{SE}$).
   - **Purpose:** Regression prevention in automated test suites without incurring excessive CI execution latency.

2. **Standalone Precision Benchmark Script:**
   - **File:** `scratch/test_mapping.py`
   - **Function:** `main()`
   - **Shot Budget:** **$S = 500,000$ shots per sample**
   - **Execution Time:** $\approx 22$ seconds total for 5 samples.
   - **Pass Criterion:** Discrepancy $|\langle\hat{O}\rangle_{\text{exact}} - \langle\hat{O}\rangle_{\text{Aer}}| < 0.005$ (approximately $3.5 \times \text{SE}$).
   - **Purpose:** Rigorous verification of asymptotic statistical convergence and mathematical equivalence between `StatevectorEstimator` and bitstring sampling.

3. **Exploratory Diagnostic Runs:**
   - Earlier internal validation scripts tested $S = 100,000$ and $S = 200,000$ shots to empirically verify that discrepancies scale proportionally to $1/\sqrt{S}$.

### 3.2 Side-by-Side Numerical Evidence Table
Both tests evaluated the exact same 5 test feature vectors generated under `np.random.seed(42)` ($X \sim U(0, \pi)^{5 \times 6}$) and parameters $\theta \sim U(-\pi, \pi)^{12}$, using transpiler seed 42 on Processor B:

| Sample $i$ | Statevector Exact $\langle\hat{O}\rangle_{\text{exact}}$ | Aer $50\text{k}$ Shots $\langle\hat{O}\rangle_{50\text{k}}$ | Absolute Diff ($50\text{k}$) | Aer $500\text{k}$ Shots $\langle\hat{O}\rangle_{500\text{k}}$ | Absolute Diff ($500\text{k}$) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Sample 0** | $+0.020830$ | $+0.022420$ | $0.001590$ | $+0.019928$ | $0.000902$ |
| **Sample 1** | $-0.094959$ | $-0.093987$ | $0.000972$ | $-0.094709$ | $0.000250$ |
| **Sample 2** | $+0.053040$ | $+0.053233$ | $0.000193$ | $+0.052359$ | $0.000681$ |
| **Sample 3** | $-0.039651$ | $-0.038493$ | $0.001157$ | $-0.040261$ | $0.000610$ |
| **Sample 4** | $-0.100973$ | $-0.100180$ | $0.000793$ | $-0.101205$ | $0.000233$ |
| **Maximum** | — | — | **$0.001590$** | — | **$0.000902$** |
| **3-Sigma Bound** | — | — | $< 0.0076$ | — | $< 0.0024$ |

### 3.3 Transpiler Routing, Classical Bit Ordering, and Measurement Contract
The mathematical equivalence demonstrated above depends on the verified transpiler mapping and bitstring unpacking rules:
1. **Transpiled Physical Layout:**
   - Under `optimization_level=1`, `seed_transpiler=42`, and Processor B coupling map, `c.layout.routing_permutation()` is the identity permutation $[0, 1, 2, 3, 4, 5, 6, 7, 8]$.
   - `c.layout.final_index_layout()` is $[0, 1, 2, 4, 5, 6]$.
   - SWAP gate count is exactly **0**.
2. **Measurement Attachment:**
   - A 6-bit classical register `meas = ClassicalRegister(6, "meas")` is added.
   - For logical qubit $k \in \{0, \dots, 5\}$, physical qubit `final_index_layout()[k]` is measured into `meas[k]`:
     ```python
     for log_i, phys_i in enumerate(final_layout):
         meas_c.measure(phys_i, creg[log_i])
     ```
3. **Qiskit Little-Endian Bitstring Unpacking:**
   - Qiskit counts bitstrings from right to left: classical bit `creg[k]` appears at index `(5 - k)` in the Python bitstring:
     ```python
     bits = [int(bitstring[5 - k]) for k in range(6)]
     ```
4. **Eigenvalue Conversion:**
   - Each classical bit $b \in \{0, 1\}$ corresponds to Pauli-Z eigenvalue $(1 - 2b) \in \{+1, -1\}$.
   - Sample expectation value: $\hat{O}_{\text{sample}} = \frac{1}{6}\sum_{k=0}^5 (1 - 2 b_k)$.
- **Status:** **`VERIFIED`**

---

## 4. Task 3 — Processor Specification Provenance & Authority Audit

All hardware parameters utilized throughout Phase 6 were extracted directly from the authoritative challenge document:  
**`Updated_Challenge_Kit.pdf`** (located at `docs/challenge_materials/Updated_Challenge_Kit.pdf`).

### 4.1 Provenance and Classification Matrix

| Parameter / Requirement | Specification Value | Source Location in `Updated_Challenge_Kit.pdf` | Classification | Verbatim Citation from Challenge Document |
|:---|:---:|:---|:---:|:---|
| **Processor A Physical Qubits** | 5 physical qubits | Section 3.1, Page 3 | **OFFICIAL SPECIFICATION** | *"Processor A represents a 5-qubit architecture with nearest-neighbor linear connectivity:"* |
| **Processor A Coupling Topology** | Linear chain: `0 - 1 - 2 - 3 - 4` (bidirectional CX) | Section 3.1, Page 3 | **OFFICIAL SPECIFICATION** | *"Coupling map: 0 - 1 - 2 - 3 - 4 (bidirectional CX)"* |
| **Processor A Capacity Guidance** | Do not delete features; reference only | Section 3.1, Page 3 & Section 12, Page 15 | **OFFICIAL SPECIFICATION** | *"For a problem requiring more than 5 logical qubits, do not delete variables merely to force the full problem into A. Treat A as a capacity/routing reference and perform the full-size execution on Processor B where permitted."* |
| **Processor B Physical Qubits** | 9 physical qubits | Section 3.2, Page 3 | **OFFICIAL SPECIFICATION** | *"Processor B represents a 9-qubit heavy-hex-inspired sparse topology:"* |
| **Processor B Coupling Topology** | Heavy-hex sparse tree (8 bidirectional pairs) | Section 3.2, Page 3 | **OFFICIAL SPECIFICATION** | *"Coupling pairs: 0-1, 1-2, 2-3, 2-4, 4-5, 5-6, 4-7, 7-8 (bidirectional CX)"* |
| **Processor JSON Configuration Files** | Participant-created JSON files | Section 4.1 / Notes, Page 6 | **OFFICIAL SPECIFICATION** / **TEAM IMPLEMENTATION** | *"Note: processor_A.json and processor_B.json are participant-created files. Completed Processor A/B implementations are not supplied by the organizers."* |
| **Target Basis Gates** | `{rz, sx, x, cx}` | Section 3.4, Page 4 | **OFFICIAL SPECIFICATION** | *"Basis gates: rz, sx, x, cx"* |
| **1Q Depolarizing Error Rate** | $p_{1q} = 0.001$ | Section 3.4, Page 4 | **OFFICIAL SPECIFICATION** | *"1Q gate error: depolarizing p = 0.001 on single-qubit gates"* |
| **2Q Depolarizing Error Rate** | $p_{2q} = 0.005$ | Section 3.4, Page 4 | **OFFICIAL SPECIFICATION** | *"2Q gate error: depolarizing p = 0.005 on cx gates"* |
| **Measurement Readout Error** | $p_{\text{meas}} = 0.010$ (symmetric bit-flip) | Section 3.4, Page 4 | **OFFICIAL SPECIFICATION** | *"Readout error: symmetric bit-flip p = 0.01 on measurement"* |
| **Standard Shot Budget** | $S = 4096$ shots | Section 3.4, Page 4 | **OFFICIAL SPECIFICATION** | *"Shot budget: S = 4096 shots per circuit execution"* |
| **Transpiler Directives** | `optimization_level=1`, SABRE, seed 42 | Section 3.4, Page 4 | **OFFICIAL SPECIFICATION** | *"Transpiler settings: optimization_level=1, routing_method='sabre', seed_transpiler=42"* |
| **Processor A Branching Topology** | Tree: (0,1), (1,2), (1,3), (3,4) | `processor_ab_benchmark.pdf`, Page 4 | **EXPLORATORY ALTERNATIVE** | Pre-release exploration of branching versus linear connectivity |
| **Processor B Cyclic Topology** | 12-edge cyclic mesh | `processor_ab_benchmark.pdf`, Page 5 | **EXPLORATORY ALTERNATIVE** | Pre-release exploration of loop connectivity versus sparse tree |
| **5-Qubit Reference Circuit** | 5Q linear VQC benchmark | Created by NEXUS-OPS | **TEAM-SELECTED COMPARATOR** | Auxiliary benchmark constructed to quantify Processor A routing overhead |
| **Transpilation Metrics** | Depth: 24, CX: 5, Total: 47 | Generated by Qiskit Transpiler | **SIMULATED MEASUREMENT** | Measured output under Qiskit 2.5.2 compiling 6Q VQC to Processor B |

- **Status:** **`VERIFIED`**

---

## 5. Task 4 — Repository State & Git Tracking Audit

### 5.1 Verification of Tracked Files
An audit using `git status --short --untracked-files=all` confirms:
- **Modified Tracked Files:** **0**
- **Deleted Tracked Files:** **0**
- **Staged Changes:** **0**

### 5.2 Untracked Artifacts and Backups
All project outputs generated during Phases 1–6 reside in expected locations and are preserved:
- **Full Safety Backups:**
  - `backup_phase6_final_20261013/`: Preserves frozen snapshots of `report/`, `results/`, `src/`, and `tests/`.
  - `backup_phase6_final_20261013/results/phase6_final_verification_prev.json`: Snapshot of verification JSON prior to reconciliation updates.
- **Source Code Integrity:**
  - Approved circuit implementation in [`src/vqc_circuit.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/vqc_circuit.py) is unmodified.
  - Approved model training in [`src/vqc_training.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/vqc_training.py) is unmodified.
  - Frozen model selection in [`results/vqc_model_selection.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/vqc_model_selection.json) is unmodified.
- **Status:** **`VERIFIED`**

---

## 6. Comprehensive Phase 6 Milestone Verification Matrix

In accordance with strict auditor standards, each component of Phase 6 is assigned one of the five permitted status codes:

| Phase 6 Component | Status | Detailed Auditor Justification |
|:---|:---:|:---|
| **Transpilation Compatibility on Processor B** | **`VERIFIED`** | Transpiles to 9Q heavy-hex topology with 0 SWAPs, depth 24, 5 CX gates, 100% routing success. |
| **Processor A Capacity / Boundary Handling** | **`VERIFIED`** | Documented that 6Q problem cannot fit into 5Q Processor A without truncation, strictly adhering to Section 3.1 & Section 12 organizer instructions. |
| **Measurement Mapping & Aer Equivalence** | **`VERIFIED`** | Unit test ($S=50\text{k}$) and benchmark ($S=500\text{k}$) demonstrate exact agreement with `StatevectorEstimator` within shot noise bounds. |
| **Quantum State Variance Derivation** | **`VERIFIED`** | Derived $\text{Var}_{\psi}(\hat{O}) = \frac{1}{6} + \frac{1}{18}\sum \langle Z_j Z_k \rangle - \langle \hat{O} \rangle^2$; measured mean variance $0.334035$ across 100 test samples. |
| **Observable Covariance Claim Resolution** | **`VERIFIED WITH LIMITATIONS`** | Prior claim of "0.533 measured covariance" formally retracted as an inverted simulation back-calculation. True state variance documented. |
| **Finite-Shot Scaling Analysis** | **`VERIFIED WITH LIMITATIONS`** | Swept budgets $S \in [256, 4096]$ across 3 seeds. Confirmed approximate $1/\sqrt{S}$ dispersion trend; limited to 3 seeds and synthetic noise. |
| **Specification Provenance & Citations** | **`VERIFIED`** | Verified against `Updated_Challenge_Kit.pdf` with exact page numbers, sections, and verbatim quotations. |
| **Record 208 Generalization Characterization** | **`VERIFIED`** | Retracted speculative LBBB/bigeminy claims; objectively described as observed inter-record distribution shift. |
| **Physical Quantum Hardware Execution** | **`NOT PERFORMED`** | No physical IBM Quantum hardware jobs were executed. All experiments reflect transpilation analysis and Qiskit Aer simulation. |
| **Regression Test Suite Integrity** | **`VERIFIED`** | 116 passing tests across the entire repository in 12.98s with 0 failures and 0 warnings under `pytest.ini`. |

---

## 7. Remaining Limitations & Open Recommendations

1. **Synthetic vs. Realistic Noise Models:**
   The challenge-specified noise model includes 1Q depolarizing ($p=0.001$), 2Q depolarizing ($p=0.005$), and readout bit-flips ($p=0.010$). It omits thermal relaxation ($T_1$), dephasing ($T_2$), crosstalk, spectator qubit interactions, and coherent phase drifts. Real hardware behavior may exhibit asymmetric decay and time-dependent drift.
2. **Simulation Seed Count:**
   The finite-shot scaling sweep was performed with $K = 3$ simulator RNG seeds (42, 101, 202). While sufficient to illustrate stochastic dispersion, higher-order statistical scaling studies would benefit from $K \ge 20$ seeds to improve confidence intervals.
3. **Training Data Diversity:**
   The frozen model `fold_1_seed_303` was trained strictly on Record 106 ($N=100$) and evaluated on Records 200 and 208 ($N=100$). As noted in previous reports, pooled cross-record training (e.g., Records 106 + 119) is recommended for future research beyond Phase 6.

---

**Report Certification:**  
This document completes the Phase 6 Final Evidence Reconciliation. All evidence gaps are fully resolved, citations are verified against official challenge materials, and numerical results are mathematically verified and reproducible. Phase 6 is officially concluded as **`VERIFIED WITH LIMITATIONS`**.
