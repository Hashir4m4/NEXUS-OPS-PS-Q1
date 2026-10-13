# Milestone 5B.1: VQC Team Review Summary & Architecture Briefing

**Project:** Project Q — IBM Quantum Qiskit Fall Fest 2026  
**Challenge:** PS-Q1 — Biomedical Signal Classifier  
**Team:** NEXUS-OPS  
**Stage:** Milestone 5B.1 — Team Review Package & Scientific Alignment  
**Document Purpose:** Compact Architectural Briefing for Full Team Deliberation & Approval  
**Current Governance Status:** **PROPOSED — NOT YET TEAM-APPROVED**  
**Project Owner Position:** Individual Review Recorded (D5, D6, D9 Endorsed)  
**Date:** October 12, 2026  

---

## 1. Executive Briefing & Context

This document summarizes the proposed **Variational Quantum Classifier (VQC)** architecture for classifying electrocardiogram (ECG) beat segments as Normal (`N`, $y = 0$) or Ventricular Ectopic Beat (`V`, $y = 1$) across the standardized MIT-BIH cohort (300 total segments).

### Key Governance Principle:
* The project owner has individually reviewed the proposed architecture and endorsed three specific choices (**D5: $L=1$**, **D6: positive expectation = VEB**, and **D9: MSE loss**).
* **These individual selections do not constitute formal team approval.** All ten decisions strictly retain `"status": "PROPOSED_NOT_TEAM_APPROVED"` in [`results/vqc_architecture_decisions.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/vqc_architecture_decisions.json).
* In accordance with hackathon rules, **no quantum circuit code or classifier training loops have been implemented**. Formal implementation (Milestone 5C) will commence only upon team sign-off.

---

## 2. Proposed Architecture Decision Matrix (D1–D10)

| Decision ID | Dimension | Proposed Choice | Project Owner Position | Formal Team Status | Summary Rationale |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **D1** | Qubit Count | 6 Qubits | APPROVE | **PENDING** | Direct $1:1$ mapping for all 6 features (`pre_rr`, `post_rr`, `qrs_rms`, `qrs_duration`, `p2p_amplitude`, `spectral_ratio`). State space is $2^6 = 64$. |
| **D2** | Feature Encoding | First-order $R_y$ angle | APPROVE | **PENDING** | Depth $O(1)$, zero 2-qubit gates, real amplitudes in $[0, \pi]$. Aligns with existing scaling pipeline. |
| **D3** | Ansatz | RealAmplitudes | APPROVE | **PENDING** | Parameterized $R_y(\theta)$ gates with fixed entanglers. Restricts state to real amplitudes ($\mathbb{R}^{64}$), halving parameter count. |
| **D4** | Entanglement | Linear nearest-neighbor | APPROVE | **PENDING** | Exactly $n-1 = 5$ CNOT gates. Matches linear superconducting hardware topology without SWAP overhead. |
| **D5** | Repetitions ($L$) | $L = 1$ Layer | **APPROVE (Primary)** | **PENDING** | Yields exactly 12 trainable parameters. Shallow depth minimizes barren plateaus. ($L=2$ reserved for ablation). |
| **D6** | Measurement | Average of 6 Pauli-Z | **APPROVE (Polarity)** | **PENDING** | $E = \frac{1}{6}\sum \langle Z_i \rangle$. Local observable avoids barren plateaus. Polarity: $E \to +1 \iff \text{VEB}$, $E \to -1 \iff \text{Normal}$. |
| **D7** | Optimizer | COBYLA | APPROVE | **PENDING** | Derivative-free simplex search. Fast in statevector simulation. Iterations capped at 150. |
| **D8** | Initialization | $\mathcal{U}[-0.1, 0.1]$ | APPROVE | **PENDING** | Starts ansatz near identity $W(\mathbf{0}) = I$. Guarantees non-vanishing initial gradients across 5 seeds. |
| **D9** | Loss Function | MSE / Brier score | **APPROVE (MSE)** | **PENDING** | $\mathcal{L} = \frac{1}{N}\sum (\hat{p}_i - y_i)^2$. Smooth, bounded in $[0, 1]$, and stable with COBYLA without adaptive bias terms. |
| **D10**| Simulation | Statevector train + 1024-shot eval | APPROVE | **PENDING** | Statevector simulation for deterministic training; 1,024 shots for finite-sampling robustness on frozen parameters. |

---

## 3. The Three Individually Reviewed Decisions: Deep Dive

### 3.1 Decision D5: Ansatz Repetitions ($L = 1$)
* **Selection:** $L = 1$ is approved as the primary baseline.
* **Architecture Impact:** Total trainable parameters $P = n \times (L + 1) = 6 \times (1 + 1) = 12$.
* **Rationale:** A single repetition layer provides the simplest possible entangled ansatz. It avoids barren plateau flattening and minimizes the non-convex ruggedness of the optimization landscape.
* **Ablation Contingency:** If the training LORO validation demonstrates underfitting relative to classical Logistic Regression, an ablation using $L = 2$ ($18$ parameters, $10$ CNOTs) is pre-authorized for investigation.

### 3.2 Decision D6: Measurement Polarity & Label Alignment
* **Selection:** Output polarity mapping: positive expectation ($E \to +1$) corresponds to class 1 (VEB); negative expectation ($E \to -1$) corresponds to class 0 (Normal).
* **Mathematical Formula:**
  $$p(\text{VEB} | \mathbf{x}, \boldsymbol{\theta}) = \frac{E(\mathbf{x}, \boldsymbol{\theta}) + 1}{2} \in [0, 1]$$
* **Dataset Label Convention:**
  * Label $y = 0 \iff \text{Normal Sinus Beat ('N')}$
  * Label $y = 1 \iff \text{Ventricular Ectopic Beat ('V')}$
* **Zero-Angle Theoretical Reference vs. Actual ECG Encoding:**
  * The mathematical property that $E = +1.0$ ($p = 1.0$) applies strictly to the unrotated ground state where both the feature encoding angles and variational parameters are identically zero ($\mathbf{x} = \mathbf{0}, \boldsymbol{\theta} = \mathbf{0}$).
  * This does **NOT** imply that actual encoded ECG samples produce $E = +1.0$ at initialization. For real biomedical samples, the six continuous features $\mathbf{x} \in [0, \pi]^6$ introduce non-zero rotations $R_y(x_i)$, and the initialized ansatz angles $\boldsymbol{\theta}_0 \sim \mathcal{U}[-0.1, 0.1]$ introduce additional rotations and linear entanglement.
  * **Team Verification Requirement:** Initial model predictions and polarity alignment must be evaluated across the actual training cohort using the true six scaled input features and initialized variational parameters. The team must confirm that training drives Normal beats toward negative expectation values ($E < 0 \implies p < 0.5$) and VEB beats toward positive expectation values ($E > 0 \implies p > 0.5$) without introducing ad-hoc classical bias terms or architecture modifications.

### 3.3 Decision D9: Loss Function Selection (MSE / Brier Score)
* **Selection:** Mean Squared Error (Brier score) without adaptive bias terms.
* **Mathematical Formula:**
  $$\mathcal{L}_{\text{MSE}}(\boldsymbol{\theta}) = \frac{1}{N} \sum_{i=1}^N \left( p(\text{VEB} | \mathbf{x}_i, \boldsymbol{\theta}) - y_i \right)^2 = \frac{1}{4N} \sum_{i=1}^N \left( E(\mathbf{x}_i, \boldsymbol{\theta}) - (2y_i - 1) \right)^2$$
* **Rationale:** MSE connects algebraically to Pauli expectation values $[-1, +1]$, maps to a smooth quadratic surface, and directly evaluates probability calibration.

---

## 4. Mathematical Model & Expressivity Clarification

```
  |0⟩ --- [ Ry(x0) ] --- [ Ry(θ0) ] ---●--- [ Ry(θ6)  ] --- [ Z0 ] ---
  |0⟩ --- [ Ry(x1) ] --- [ Ry(θ1) ] ---X--- [ Ry(θ7)  ] --- [ Z1 ] ---
  |0⟩ --- [ Ry(x2) ] --- [ Ry(θ2) ] ---●--- [ Ry(θ8)  ] --- [ Z2 ] ---  ===> E = (1/6) Σ ⟨Zi⟩
  |0⟩ --- [ Ry(x3) ] --- [ Ry(θ3) ] ---X--- [ Ry(θ9)  ] --- [ Z3 ] ---       p = (E + 1) / 2
  |0⟩ --- [ Ry(x4) ] --- [ Ry(θ4) ] ---●--- [ Ry(θ10) ] --- [ Z4 ] ---
  |0⟩ --- [ Ry(x5) ] --- [ Ry(θ5) ] ---X--- [ Ry(θ11) ] --- [ Z5 ] ---
```

### Clarification on Logistic Regression Equivalence:
> [!IMPORTANT]
> **$R_y$ angle encoding does NOT make the VQC equivalent to Logistic Regression.**  
> While the feature encoding uses independent single-qubit rotations, the subsequent CNOT entangling gates create an entangled multi-qubit state in a 64-dimensional Hilbert space. The expectation value $E(\mathbf{x}, \boldsymbol{\theta})$ contains non-linear trigonometric cross-terms ($\cos(x_j/2)\sin(x_k/2)$). The resulting decision boundary is non-linear and operates in quantum Hilbert space, not a classical linear hyperplane.

---

## 5. Technical Corrections & Scientific Rigor

### 5.1 Categorization of Quantum Resource Claims
To eliminate confusion between theoretical designs and experimental measurements:
1. **Tier 1 (Theoretical Architecture Expectation):** Formula-derived expectations ($n=6$, $P=12$, $5$ CNOTs, untranspiled depth $8$).
2. **Tier 2 (Constructed Circuit Metrics):** Values measured from the Qiskit circuit object (`qc.depth()`, `qc.count_ops()`) — *requires constructing the circuit in Milestone 5C*.
3. **Tier 3 (Transpiled Hardware Metrics):** Values resulting from transpilation to a physical processor basis gate set (`['ecr', 'rz', 'sx', 'x']`) — *depends on hardware coupling topology and optimization level*.
*Current Status:* No circuit has been constructed yet. All figures are currently Tier 1 expectations.

### 5.2 Optimizer Accounting: Iterations vs. Evaluations
* In COBYLA, **iterations and objective-function evaluations are different quantities**. An iteration may perform multiple function calls during simplex adjustments.
* **Logging Requirement:** The training loop must log both quantities independently:
  `iteration_count`, `objective_evaluation_count`, `best_objective_value`, `termination_reason`, `runtime_seconds`, and `convergence_status`. Max iterations is capped at 150.

### 5.3 Finite-Shot Sampling Uncertainty
* For $S = 1024$ shots, measuring $E = \frac{1}{6}\sum_{i=0}^5 \langle Z_i \rangle$:
  * Standard error of expectation: $\operatorname{SE}(E) \le \frac{1}{\sqrt{1024}} = \frac{1}{32} \approx 0.03125$.
  * Standard error of mapped probability: $\operatorname{SE}(p) = \frac{1}{2}\operatorname{SE}(E) \le \frac{1}{64} \approx 0.015625$ ($\approx 1.56\%$).
* **Scientific Note:** This is a **theoretical worst-case upper bound**, NOT an experimentally observed measurement.

### 5.4 Cautious Physiological Context (Record 208)
* *Wording Correction:* Some normal-labelled beats in Record 208 exhibited relatively rapid RR intervals ($0.48\text{--}0.56\text{ s}$), which may contribute to classification difficulty when compared against training set ectopic intervals.
* Sinus tachycardia is an **unconfirmed clinical hypothesis**, not an established medical diagnosis.

---

## 6. Comprehensive Scientific Limitations

1. **Small Dataset & Cohort Scarcity:** Exactly four MIT-BIH records (two train, two test).
2. **Within-Record Beat Correlation:** Consecutive beats from the same subject share anatomical axis and noise morphology.
3. **Inter-Patient Generalization Uncertainty:** Subject 208 normal beats with rapid RR intervals overlap with training ectopic intervals.
4. **Retrospective Post-RR Lookahead Latency:** Feature 2 introduces a $0.42\text{--}1.48\text{ s}$ delay; the system is strictly an offline annotator.
5. **Heuristic QRS Duration Estimation:** Estimated from baseline crossings, carrying heuristic variance.
6. **Finite-Shot Sampling Uncertainty:** Theoretical bound $\operatorname{SE}(p) \le 1.56\%$ at 1,024 shots can induce label flips near $p \approx 0.5$.
7. **Optimizer Sensitivity & Local Minima:** COBYLA is a derivative-free heuristic; performance depends on initialization.
8. **No Clinical Validity or Diagnostic Safety Claims:** Academic prototype only; **not clinically deployable**.
9. **Historical Test-Set Selection Bias:** Acknowledged and preserved from Milestone 4.1 disclosure.

---

## 7. Experimental Protocol & Execution Plan

* **Seeds:** 5 fixed random seeds: `[42, 101, 202, 303, 404]`.
* **Training LORO Validation:**
  * Fold 1: Train on Record 106 ($n=100$) $\to$ Validate on Record 119 ($n=100$) (5 runs).
  * Fold 2: Train on Record 119 ($n=100$) $\to$ Validate on Record 106 ($n=100$) (5 runs).
  * **Total LORO Runs:** $5 \times 2 = \mathbf{10\text{ runs}}$.
* **Full Training Fits:** 5 seed runs on Records 106 + 119 ($n=200$) (**5 runs**).
* **Test Set Quarantine:** Records 200 and 208 evaluated **strictly once post-hoc** as an observational benchmark.

---

## 8. Action Required from the NEXUS-OPS Team

To transition from Milestone 5B.1 to Milestone 5C (Implementation), the NEXUS-OPS team must formally confirm:

1. [ ] **Consensus on D1–D10:** Confirm full team agreement with the proposed 10 architecture choices.
2. [ ] **Endorsement of Project Owner Selections:** Formally approve D5 ($L=1$), D6 (positive polarity = VEB), and D9 (MSE loss).
3. [ ] **Status Transition:** Authorize updating `"status"` in [`results/vqc_architecture_decisions.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/vqc_architecture_decisions.json) from `PROPOSED_NOT_TEAM_APPROVED` to `TEAM_APPROVED`.
4. [ ] **Greenlight for Milestone 5C:** Authorize construction of the quantum circuit modules in `src/vqc_circuit.py`.
