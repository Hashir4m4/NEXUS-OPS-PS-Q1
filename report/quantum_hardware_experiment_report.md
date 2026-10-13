# NEXUS-OPS — Quantum Hardware & Processor Architecture Experiment Report
**Project:** IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Classifier  
**Milestone:** Phase 6 — Quantum Hardware Experiments & Evaluation  
**Status:** COMPLETED, AUDITED & CALIBRATED  
**Date:** 2026-10-13  

---

## 1. Executive Summary

This report delivers the comprehensive synthesis of **Phase 6: Quantum Hardware Experiments and Processor Architecture Evaluation** for the NEXUS-OPS Q1 Biomedical Signal Classifier.

The objective was to evaluate the transpilation compatibility, topological mapping, finite sampling behavior, and synthetic noise response of the approved 6-qubit Variational Quantum Classifier (VQC) across the hardware architectures designated in the IBM Quantum Qiskit Fall Fest 2026 Challenge Kit:
- **Processor A:** 5-qubit superconducting processor (capacity reference & 1D line baseline).
- **Processor B:** 9-qubit superconducting processor (sparse heavy-hex execution target).

### Key Technical Achievements
1. **Capacity Enforcement & Reference Benchmarks:** Verified that the approved 6-qubit circuit correctly triggers capacity bounds on 5-qubit Processor A (`CircuitTooWideForTarget`). Benchmarked a 5-qubit reference circuit, showing that a linear topology achieves zero CX overhead while a branching tree incurs $+75\%$ CX routing penalty.
2. **Deterministic Zero-Overhead Transpilation on Processor B:** Transpiling the approved 6-qubit circuit onto Processor B produced **depth 15**, **5 CX gates**, **0 SWAP gates**, and **65 total operations** across all 5 random seeds and all 3 optimization levels (zero variance).
3. **Empirical Verification of Shot Noise Scaling:** Evaluated finite measurement sampling across shot counts $S \in [256, 512, 1024, 2048, 4096]$. Empirical standard error followed the theoretical $\mathcal{O}(1/\sqrt{S})$ limit ($0.0458 \rightarrow 0.0114$). Classification F1 score remained stable between $0.7938$ and $0.8108$.
4. **Full-Cohort Noise Evaluation & Readout Audit:** Evaluated the full held-out test cohort ($N=100$, Records 200 & 208). Proved via diagnostic audit that `EstimatorV2` bypasses `ReadoutError`. Implemented a measurement-based `AerSimulator` path applying both gate depolarizing noise and readout bit flips, achieving **$77.00\%$ Accuracy**, **$0.8130$ F1-Score**, and **$100.00\%$ Sensitivity** on the test cohort.
5. **Rigorous Scientific Governance:** Every transpilation and simulation was executed with full seed logging, parameter freezing, and zero data leakage. Compiler synthesis is explicitly distinguished from physical quantum cryogenic hardware execution.

---

## 2. Experimental Architecture Overview

```
                      ┌───────────────────────────────────────────────┐
                      │    NEXUS-OPS 6-Qubit Frozen Architecture      │
                      │  6 Logical Qubits, 12 Trainable Parameters    │
                      └──────────────────────┬────────────────────────┘
                                             │
                     ┌───────────────────────┴───────────────────────┐
                     ▼                                               ▼
         ┌───────────────────────┐                       ┌───────────────────────┐
         │      PROCESSOR A      │                       │      PROCESSOR B      │
         │   5 Physical Qubits   │                       │   9 Physical Qubits   │
         │   Linear Chain (0-4)  │                       │   Sparse Tree Graph   │
         └───────────┬───────────┘                       └───────────┬───────────┘
                     │                                               │
           Capacity Check: 6Q > 5Q                         SABRE Layout & Basis Synthesis
        [CircuitTooWideForTarget]                        Depth: 15, CX: 5, SWAP: 0
                     │                                               │
       Reference 5Q Baseline: Depth 16                     ┌─────────┴─────────┐
                                                           ▼                   ▼
                                                  Shot-Count Scaling    Noisy Simulation
                                                   S ∈ [256, 4096]       Challenge Noise
                                                  σ ~ 1/sqrt(S)          Full Noise: 77.0%
                                                  F1 ~ 0.80             Sens: 100.0%
```

---

## 3. Transpilation & Topology Analysis

### 3.1 Processor A Capacity & Reference Results
- **Approved 6Q Circuit:** Fails compilation with `CircuitTooWideForTarget` (`physical_qubits = 5 < logical_qubits = 6`). This is the intended behavior specified in the Challenge Kit (Section 3.1 & Section 12).
- **Reference 5Q Circuit:**
  - *Canonical Line ($0-1-2-3-4$):* Compiles to depth 16, 4 CX, 0 SWAP, 65 total operations. Routing overhead: **0 CX**.
  - *Branching Tree ($0-1, 1-2, 1-3, 3-4$):* Compiles to depth 23, 7 CX, 0 SWAP, 68 total operations. Routing overhead: **+3 CX (+75%)**.

### 3.2 Processor B Multi-Seed Transpilation Results
Evaluated on Approved 6Q VQC across seeds `[42, 101, 202, 303, 404]` and optimization levels `[1, 2, 3]`:

| Architecture Variant | Opt Level | Transpiled Depth | CX Gates | SWAP Gates | Total Operations | Routing CX Overhead |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Processor B (Canonical Tree)** | 1 | $15.0 \pm 0.0$ | $5.0 \pm 0.0$ | $0.0 \pm 0.0$ | $65.0 \pm 0.0$ | **0** |
| | 2 | $15.0 \pm 0.0$ | $5.0 \pm 0.0$ | $0.0 \pm 0.0$ | $65.0 \pm 0.0$ | **0** |
| | 3 | $15.0 \pm 0.0$ | $5.0 \pm 0.0$ | $0.0 \pm 0.0$ | $65.0 \pm 0.0$ | **0** |
| **Processor B (Cyclic Mesh)** | 1 | $15.0 \pm 0.0$ | $5.0 \pm 0.0$ | $0.0 \pm 0.0$ | $65.0 \pm 0.0$ | **0** |
| | 2 | $15.0 \pm 0.0$ | $5.0 \pm 0.0$ | $0.0 \pm 0.0$ | $65.0 \pm 0.0$ | **0** |
| | 3 | $15.0 \pm 0.0$ | $5.0 \pm 0.0$ | $0.0 \pm 0.0$ | $65.0 \pm 0.0$ | **0** |

**Conclusion:** The approved circuit is native-compatible with Processor B without requiring non-local CX routing or SWAP insertion.

---

## 4. Controlled Shot-Count Scaling & Finite Sampling Analysis

To model finite measurement sampling, the held-out cohort ($N=100$) was benchmarked across shot budgets $S \in [256, 512, 1024, 2048, 4096]$ across 3 simulation seeds:

| Shot Count ($S$) | Theoretical Upper Bound Precision ($1/\sqrt{S}$) | Empirical Mean Std Error Across Seeds ($\bar{s}$) | Test Accuracy (mean $\pm$ std) | Test F1 (mean) | Sensitivity (mean) | MAE vs Exact $\langle \hat{O} \rangle$ | Prediction Flip Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **256** | $0.0625$ | $0.0458$ | $74.67\% \pm 0.47\%$ | $0.7979$ | $100.00\%$ | $0.0515$ | $2.33\%$ |
| **512** | $0.0442$ | $0.0339$ | $76.67\% \pm 0.47\%$ | $0.8108$ | $100.00\%$ | $0.0345$ | $1.67\%$ |
| **1024** | $0.0312$ | $0.0238$ | $75.00\% \pm 2.45\%$ | $0.8003$ | $100.00\%$ | $0.0257$ | $1.00\%$ |
| **2048** | $0.0221$ | $0.0170$ | $76.00\% \pm 0.00\%$ | $0.8065$ | $100.00\%$ | $0.0190$ | $0.33\%$ |
| **4096** | $0.0156$ | $0.0114$ | $74.00\% \pm 1.41\%$ | $0.7938$ | $100.00\%$ | $0.0139$ | $1.00\%$ |
| **$\infty$ (Exact)** | $0.0000$ | $0.0000$ | **$76.00\%$** | **$0.8065$** | **$100.00\%$** | **$0.0000$** | **$0.00\%$** |

### Statistical Insights on Shot Scaling
1. **Empirical Scaling Behavior:** The empirical standard error of the expectation estimator across simulation seeds approximately scales with the theoretical $1/\sqrt{S}$ standard error curve (variance scales approximately as $1/S$). For $S=4096$, the empirical standard error is $\bar{s} \approx 0.01140$, compared to the theoretical upper bound of $1/\sqrt{4096} = 0.015625$ (ratio $\approx 0.73$, reflecting reduced observable variance $\text{Var}(\hat{O}) \le 1/6$ to $\sim 0.53$). Finite sampling does not establish strict asymptotic scaling.
2. **Operational Budget:** At $S=512$ shots, the model achieves $76.67\%$ accuracy and $100\%$ sensitivity with only $1.67\%$ prediction flip variance, demonstrating practical sampling stability without requiring high shot counts.
3. **Sensitivity Invariance:** At every shot level tested, Sensitivity remained **$100.00\%$** across the 50 test VEB samples.

---

## 5. Synthetic Noise Model Performance (Processor B)

Evaluated on the full held-out test cohort ($N=100$) under challenge noise ($p_{1q}=0.001$, $p_{2q}=0.005$, $p_{ro}=0.010$):

| Metric | Ideal (Statevector) | Path A: Gate Noise Only (`EstimatorV2`) | Path B: Full Combined Noise (`AerSimulator` Measurements) |
| :--- | :---: | :---: | :---: |
| **Readout Error Applied?** | N/A | **NO (Bypassed)** | **YES (Simulated)** |
| **Accuracy** | $76.00\%$ | $74.00\%$ | **$77.00\%$** |
| **F1-Score** | $0.8065$ | $0.7937$ | **$0.8130$** |
| **Sensitivity** | $100.00\%$ | $100.00\%$ | **$100.00\%$** |
| **Specificity** | $52.00\%$ | $48.00\%$ | **$54.00\%$** |
| **Precision** | $67.57\%$ | $65.79\%$ | **$68.49\%$** |
| **ROC-AUC** | $0.9988$ | $0.9992$ | **$0.9984$** |
| **MSE / Brier Loss** | $0.1626$ | $0.1634$ | **$0.1644$** |
| **Class Polarity $\Delta p$** | $+0.2317$ | $+0.2286$ | **$+0.2246$** |
| **Prediction Flip Rate** | $0.0\%$ | $2.0\%$ (2 samples) | **$1.0\%$ (1 sample)** |

### Patient-Specific Noise Stability (Path B: Full Noise)
- **Patient Record 200 ($N=50$):** Ideal Accuracy = $84.00\%$, Full Noise Accuracy = $84.00\%$ (0 flips).
- **Patient Record 208 ($N=50$):** Ideal Accuracy = $68.00\%$, Full Noise Accuracy = $70.00\%$ (1 flip).
- **Record 208 Distribution Shift:** Record 208 exhibited a higher false-positive rate and lower specificity than Record 200. The difference indicates record-specific distribution shift; its physiological cause has not been established.

---

## 6. Hardware Evaluation Conclusion

The 6-qubit Variational Quantum Classifier demonstrates technical transpilation and simulation compatibility with Processor B:
1. **Low Depth (15):** Within superconducting coherence times.
2. **Minimal Entanglement (5 CX):** Minimizes susceptibility to two-qubit gate errors.
3. **No SWAP Overhead:** Topology-matched linear layout prevents compilation bloat.
4. **Empirical Stability on Tested Benchmark:** Preserves $100\%$ VEB sensitivity on the test cohort under synthetic gate and readout noise.

---

## 7. Artifacts & Serialization

All results documented herein are backed by verified JSON artifacts:
- `results/transpilation_comparison.json`
- `results/noisy_simulation_results.json`
- `results/shot_based_results.json`
- `results/processor_ab_evidence_audit.json`

> **Scientific Disclosure:** All benchmarks represent compiler synthesis and high-performance Qiskit Aer noisy simulations on local hardware. No claims of physical cryogenic quantum hardware runs are made. Physical hardware execution status: **NOT PERFORMED**.
