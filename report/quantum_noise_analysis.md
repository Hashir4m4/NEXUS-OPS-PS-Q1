# NEXUS-OPS — Quantum Noise Simulation & Error Analysis Report
**Project:** IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Classifier
**Milestone:** Phase 6 — Quantum Hardware Experiments (Stage 8 & 10)
**Status:** COMPLETED, AUDITED & CALIBRATED
**Date:** 2026-10-13

---

## 1. Executive Summary

This report presents the full-cohort ($N=100$) quantum noise evaluation of the frozen 6-qubit Variational Quantum Classifier (VQC) checkpoint (`fold_1_seed_303`) compiled and simulated on **Processor B** under the official **Qiskit Fall Fest 2026 Challenge Synthetic Noise Model**.

This experiment directly addresses the technical qualification established in `results/processor_ab_evidence_audit.json`:
1. **Full Cohort Requirement:** Replaced single-sample comparisons with the full held-out test cohort (MIT-BIH Patient Records 200 and 208, $N=100$ heartbeats: 50 Normal, 50 VEB).
2. **Readout Error Application Audit:** Disclosed and proved that Qiskit Aer `EstimatorV2` evaluates operator expectations without measurement operations, bypassing `ReadoutError`. Implemented and verified a separate measurement-based sampling execution path using `AerSimulator` with physical measurements to genuinely apply both gate and readout noise.

### Key Empirical Findings
- **Readout Error Diagnostic Audit:** A controlled single-qubit $|0\rangle$ diagnostic with exaggerated $50\%$ readout error confirmed that `EstimatorV2` returns $\langle Z \rangle = 1.0$ (bypassing readout noise), while the measurement-based `AerSimulator` returns $\langle Z \rangle \approx 0.005$ (correctly attenuated by $1 - 2p$).
- **Path A — Gate-Depolarizing Noise Only (`EstimatorV2`, $S=4096$):**
  - Accuracy: $74.00\%$ ($\Delta = -2.00\%$ from ideal $76.00\%$)
  - F1-Score: $0.7937$ ($\Delta = -0.0128$ from ideal $0.8065$)
  - Sensitivity: $100.00\%$ (50/50 VEBs detected)
  - Prediction Flips: 2 out of 100 samples ($2.0\%$ flip rate)
- **Path B — Combined Gate + Readout Noise (`AerSimulator` Measurements, $S=4096$):**
  - Accuracy: $77.00\%$ ($\Delta = +1.00\%$ from ideal $76.00\%$)
  - F1-Score: $0.8130$ ($\Delta = +0.0065$ from ideal $0.8065$)
  - Sensitivity: $100.00\%$ (50/50 VEBs detected)
  - Specificity: $54.00\%$ (27/50 Normal detected)
  - ROC-AUC: $0.9984$ (preserved rank-ordering)
  - Prediction Flips: 1 out of 100 samples ($1.0\%$ flip rate)
- **Multi-Seed Stability:** Across 3 independent Aer RNG seeds (42, 101, 202), accuracy under full combined noise remained within $[74.0\%, 77.0\%]$ with mean F1-score of $0.8044 \pm 0.0080$ and $100.0\%$ sensitivity across all runs.

---

## 2. Noise Model Specification & Circuit Transpilation

### 2.1 Challenge Synthetic Noise Parameters
The synthetic noise model on Processor B implements three canonical error channels:
1. **Single-Qubit Depolarizing Error:** $p_{1q} = 0.001$ applied to all native single-qubit basis gates (`x`, `sx`).
   $$\mathcal{E}_{1q}(\rho) = (1 - p_{1q})\rho + \frac{p_{1q}}{3}\sum_{P \in \{X, Y, Z\}} P \rho P$$
2. **Two-Qubit Depolarizing Error:** $p_{2q} = 0.005$ applied to all two-qubit entangling gates (`cx`).
   $$\mathcal{E}_{2q}(\rho) = (1 - p_{2q})\rho + \frac{p_{2q}}{15}\sum_{P_1, P_2} (P_1 \otimes P_2) \rho (P_1 \otimes P_2)$$
3. **Readout Bit-Flip Error:** $p_{ro} = 0.010$ per measured physical qubit.
   $$\Lambda_{ro} = \begin{pmatrix} 0.99 & 0.01 \\ 0.01 & 0.99 \end{pmatrix}$$

### 2.2 Compilation to Native Physical Primitives
To guarantee that noise channels act on physical gates:
- Uncompiled $R_y(\theta)$ gates were synthesized into native basis gates: $36$ virtual $R_z$ frame shifts and $24$ physical $\sqrt{X}$ (`sx`) pulses.
- The 5 CX gates were mapped to physical edges on Processor B's sparse tree.
- Logical qubits $0..5$ were mapped to physical qubits $[0, 1, 2, 4, 5, 6]$.
- Transpiled depth: **15**. Total physical operations: **65**.

---

## 3. Readout Noise Diagnostic & Execution Paths

### 3.1 Controlled Diagnostic Verification
To test whether `ReadoutError` is applied, a single-qubit state $|0\rangle$ with an exaggerated $50\%$ readout error was tested:
- **Theoretical Attenuation:** $\langle Z \rangle_{\text{attenuated}} = \langle Z \rangle_{\text{ideal}} \cdot (1 - 2p) = 1.0 \cdot (1 - 1.0) = 0.0$.
- **`EstimatorV2` (without measurements):** $\langle Z \rangle = 1.0$ $\rightarrow$ **Readout error NOT applied**.
- **`AerSimulator` (with measurement operation):** $\langle Z \rangle = 0.0054$ $\rightarrow$ **Readout error APPLIED**.

### 3.2 Full-Cohort Performance Comparison ($N=100$)

| Evaluation Metric | Ideal Statevector (Exact) | Path A: Gate Noise Only (`EstimatorV2`, $S=4096$) | Path B: Full Combined Noise (`AerSimulator`, $S=4096$) |
| :--- | :---: | :---: | :---: |
| **Readout Error Applied?** | N/A | **NO (Bypassed)** | **YES (Simulated)** |
| **Accuracy** | $76.00\%$ | $74.00\%$ | **$77.00\%$** |
| **F1-Score** | $0.8065$ | $0.7937$ | **$0.8130$** |
| **Sensitivity (VEB Recall)** | $100.00\%$ | $100.00\%$ | **$100.00\%$** |
| **Specificity (Normal Recall)** | $52.00\%$ | $48.00\%$ | **$54.00\%$** |
| **Precision** | $67.57\%$ | $65.79\%$ | **$68.49\%$** |
| **ROC-AUC** | $0.9988$ | $0.9992$ | **$0.9984$** |
| **Brier Score / MSE Loss** | $0.1626$ | $0.1634$ | **$0.1644$** |
| **Class Polarity $\Delta p$** | $+0.2317$ | $+0.2286$ | **$+0.2246$** |
| **Expectation MAE vs Ideal** | $0.0000$ | $0.0130$ | **$0.0115$** |
| **Prediction Flip Rate** | $0.0\%$ | $2.0\%$ (2 samples) | **$1.0\%$ (1 sample)** |

---

## 4. Record-Stratified Noise Breakdown (Path B: Full Noise)

| Metric | Record 200 ($N=50$) | Record 208 ($N=50$) |
| :--- | :---: | :---: |
| **Ideal Accuracy** | $84.00\%$ (42/50) | $68.00\%$ (34/50) |
| **Full Noise Accuracy** | $84.00\%$ (42/50) | $70.00\%$ (35/50) |
| **Ideal F1-Score** | $0.8621$ | $0.7576$ |
| **Full Noise F1-Score** | $0.8621$ | $0.7692$ |
| **Sensitivity** | $100.00\%$ (25/25) | $100.00\%$ (25/25) |
| **Specificity** | $68.00\%$ (17/25) | $40.00\%$ (10/25) |
| **Classification Flips vs Ideal** | **0 flips** | **1 flip** (Index 41) |
| **Mean Probability MAE** | $0.0068$ | $0.0047$ |

---

## 5. Multi-Seed Simulation Verification (Path B: Full Noise)

Evaluated across three distinct simulation RNG seeds (`seeds = [42, 101, 202]`) at $S=4096$ shots:

| Simulator Seed | Accuracy | F1-Score | Sensitivity | Specificity | Precision | ROC-AUC | MSE Loss | Polarity $\Delta p$ | MAE vs Ideal $\langle \hat{O} \rangle$ |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Seed 42** | $77.00\%$ | $0.8130$ | $100.00\%$ | $54.00\%$ | $68.49\%$ | $0.9984$ | $0.1644$ | $+0.2246$ | $0.0115$ |
| **Seed 101** | $74.00\%$ | $0.7937$ | $100.00\%$ | $48.00\%$ | $65.79\%$ | $0.9992$ | $0.1643$ | $+0.2254$ | $0.0112$ |
| **Seed 202** | $76.00\%$ | $0.8065$ | $100.00\%$ | $52.00\%$ | $67.57\%$ | $0.9984$ | $0.1639$ | $+0.2258$ | $0.0119$ |
| **Mean $\pm$ Std** | **$75.67\% \pm 1.25\%$** | **$0.8044 \pm 0.0080$** | **$100.00\% \pm 0.00\%$** | **$51.33\% \pm 2.49\%$** | **$67.28\% \pm 1.12\%$** | **$0.9987 \pm 0.0004$** | **$0.1642 \pm 0.0002$** | **$+0.2253 \pm 0.0005$** | **$0.0115 \pm 0.0003$** |

### Factors Contributing to Stability Under the Synthetic Noise Model
1. **Low Two-Qubit Depth:** With only 5 CX gates, two-qubit depolarizing error accumulation is minimal ($\approx 2.47\%$ aggregate probability).
2. **Compact Depth:** Total depth of 15 limits idle gate accumulation.
3. **Ensemble Averaging:** Symmetrizing the observable across all 6 physical qubits ($\frac{1}{6}\sum Z_i$) buffers local bit-flip and phase-flip errors.

---

## 6. Scientific Disclosures & Benchmark Scope

> [!WARNING]
> **Research Engineering Disclaimer:**
> 1. All results reported herein were obtained using **Qiskit Aer 0.17.2 numerical simulation** on local CPU hardware. No physical cryogenic quantum hardware was accessed.
> 2. The challenge noise model is a **synthetic illustrative model** and does not capture physical drift, time-dependent $T_1/T_2$ relaxation, spectator qubit crosstalk, or non-Markovian noise.
> 3. These experiments are academic benchmarks on retrospective MIT-BIH records and do NOT imply clinical safety or readiness for diagnostic healthcare deployment.
