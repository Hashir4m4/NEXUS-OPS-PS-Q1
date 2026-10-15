# NEXUS-OPS — Phase 5 & Phase 6 Scientific Correction Log

**Project:** IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Classifier  
**Milestones:** Phase 5 (Quantum Machine Learning) & Phase 6 (Quantum Hardware Experiments)  
**Log Type:** Formal Audit & Scientific Correction Record  
**Date:** 2026-10-13  
**Status:** ALL CORRECTIONS APPLIED AND VERIFIED  

---

## 1. Overview

During the independent audit of Phase 5 and Phase 6, five primary technical and scientific issues were identified, investigated, and formally corrected. This log details each correction, its root cause, the remediation applied, and the verification evidence.

---

## 2. Correction 1: Readout Error Bypass in Qiskit Aer `EstimatorV2` & Dual-Path Remediation

### 2.1 Issue Identified
The previous Phase 6 noisy simulation report claimed to test combined gate depolarizing noise and readout error ($p_{ro} = 0.010$) using Qiskit Aer's `EstimatorV2`. 
Upon mathematical audit of `EstimatorV2` execution semantics in Qiskit Aer, it was discovered that `EstimatorV2` evaluates expectation values by computing operator snapshots directly from statevectors/density matrices without inserting measurement operations (`measure` gates). Consequently, classical readout bit-flip error matrices configured in `NoiseModel.add_all_qubit_readout_error` are **completely bypassed** and never applied during estimation.

### 2.2 Diagnostic Proof
To verify this behavior conclusively, an exaggerated diagnostic was constructed:
- Initial state: $|0\rangle$, observable: $Z$.
- Theoretical ideal expectation: $\langle Z \rangle = +1.0$.
- Extreme readout bit-flip error: $50\%$ symmetric flip rate ($P(0|1) = P(1|0) = 0.50$).
- Theoretical attenuated expectation under 50% readout error: $\langle Z \rangle_{\text{attenuated}} = 1.0 \times (1 - 2 \times 0.50) = 0.00$.
- **EstimatorV2 measured expectation:** $\mathbf{1.0000}$ (Readout error ignored).
- **AerSimulator measurement sampler expectation:** $\mathbf{0.0054} \approx 0.00$ (Readout error correctly applied).

### 2.3 Remediation Applied
1. Updated `src/noise_experiments.py` to implement a rigorous **dual-path evaluation architecture**:
   - **Path A (EstimatorV2):** Evaluates gate depolarizing noise ($p_{1q}=0.001, p_{2q}=0.005$) with explicit documentation that readout error is bypassed.
   - **Path B (AerSimulator Measurement Sampler):** Appends physical measurement gates to physical mapped qubits `[0, 1, 2, 4, 5, 6]`, runs on `AerSimulator` under the complete noise model (gate + readout noise), and computes the ensemble observable expectation from bitstring counts:
     $$\langle Z_i \rangle = \frac{N_0(i) - N_1(i)}{N_{\text{shots}}}, \quad \langle \hat{O} \rangle = \frac{1}{6}\sum_{i=0}^5 \langle Z_i \rangle$$
2. Added multi-seed statistical evaluation across seeds `42, 101, 202` for Path B.
3. Updated [`results/noisy_simulation_results.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/noisy_simulation_results.json) to serialize both paths and the diagnostic test.

### 2.4 Verification Evidence
- Path A metrics: Accuracy $74.0\%$, F1 $0.7937$, Sensitivity $100.0\%$, Specificity $48.0\%$, 2 flips ($2.0\%$).
- Path B metrics: Accuracy $77.0\%$, F1 $0.8130$, Sensitivity $100.0\%$, Specificity $54.0\%$, 1 flip ($1.0\%$).
- Path B multi-seed: Mean Accuracy $75.67\% \pm 1.25\%$, Mean F1 $0.8044 \pm 0.0080$, Sensitivity $100.0\% \pm 0.0\%$.

---

## 3. Correction 2: Single-Record Training Architecture Transparency & Generalization Boundary

### 3.1 Issue Identified
Prior summary text occasionally implied that the VQC had been trained on the full pooled training cohort ($N=200$, Records 106 and 119). In reality, the LORO protocol selected checkpoint `fold_1_seed_303`, which had been trained **exclusively on Record 106 ($N=100$)** and evaluated on Record 119 ($N=100$) for validation.

### 3.2 Impact Analysis
Because the model only saw beats from Record 106 during optimization, it learned decision boundaries specific to Record 106's electrophysiology. When evaluated on the held-out test cohort:
- Record 200 achieved $84.0\%$ accuracy and $68.0\%$ specificity.
- Record 208 exhibited a higher false-positive rate and lower specificity than Record 200 ($68.0\%$ accuracy, $36.0\%$ specificity). The difference indicates record-specific distribution shift; its physiological cause has not been established.

### 3.3 Remediation Applied
1. Explicitly updated all reports ([`report/vqc_evaluation_report.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/vqc_evaluation_report.md), [`report/PHASE5_FINAL_AUDIT.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE5_FINAL_AUDIT.md), [`report/PHASE5_PHASE6_COMPLETION_REPORT.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE5_PHASE6_COMPLETION_REPORT.md)) to state:
   - "Checkpoint `fold_1_seed_303` was trained exclusively on Record 106 ($N=100$) and validated on Record 119 ($N=100$)."
   - "No pooled refit on Records 106+119 was performed prior to test evaluation to maintain strict protocol isolation."
2. Added technical recommendation to perform a future pooled refit to expand morphological coverage.

---

## 4. Correction 3: Physical Hardware Execution Demarcation

### 4.1 Issue Identified
Draft documents referred to "hardware execution" and "physical hardware viability" without sufficiently clear demarcation between simulated transpilation and actual execution on physical quantum hardware.

### 4.2 Remediation Applied
1. Changed "Physical Hardware Viability" section headings to "Processor B Transpilation Compatibility & Architecture Feasibility".
2. Added unambiguous status declarations in all executive reports:
   - **Physical Hardware Execution Status:** `STRICTLY NOT PERFORMED`.
   - Explicitly clarified that all evaluations utilized Qiskit transpilation passes and Qiskit Aer noisy simulation; no API calls or execution jobs were submitted to IBM Quantum QPUs.

---

## 5. Correction 4: Scientific Language & Expressivity Calibration

### 5.1 Issues Identified
Preliminary text contained overreaching assertions regarding:
1. "Barren plateau elimination"
2. "Proof of quantum advantage / expressivity"
3. "Clinical readiness / patient safety guarantees"

### 5.2 Remediation Applied
All narrative files were reviewed and edited:
- **Barren plateaus:** Replaced claims of "barren plateau elimination" with the accurate finding that gradient variances remained stable due to shallow circuit depth ($L=1$, 6 qubits) and localized ensemble observable, rather than general asymptotic immunity.
- **Quantum advantage:** Clarified that classical models (Logistic Regression: $92.0\%$, SVM: $91.0\%$) outperform the 6-qubit VQC ($76.0\%$) on this low-dimensional feature space, and that the VQC's high sensitivity ($100.0\%$) reflects effective parameter convergence rather than quantum computational advantage.
- **Clinical claims:** Retracted claims of "clinical readiness" or "clinical safety". Contextualized the model as an exploratory research proof-of-concept on retrospective benchmark data, noting that specificity on Record 208 ($36\%-40\%$) precludes clinical deployment without significant further development.

---

## 6. Correction 5: Unit Test Suite Expansion

### 6.1 Issue Identified
The unit test suite did not contain a regression test validating the functional difference between `EstimatorV2` snapshot expectations and `AerSimulator` measurement-based expectation under readout noise.

### 6.2 Remediation Applied
Added `test_readout_error_diagnostic_distinguishes_estimator_and_sampler` to [`tests/test_hardware_experiments.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests/test_hardware_experiments.py):
- Constructs single-qubit circuit with $50\%$ readout error.
- Asserts that `EstimatorV2` yields $\langle Z \rangle \approx 1.0$ (bypassing readout noise).
- Asserts that `AerSimulator` with measurements yields $|\langle Z \rangle| \le 0.1$ (applying readout noise).
- This brought the total test count from 114 to 115 tests.

### 6.3 Verification Evidence
- Full test suite execution: **115 passed in 11.18s**.

---

## 7. Sign-Off

All corrections have been implemented, verified, and integrated into the project's permanent technical record.
