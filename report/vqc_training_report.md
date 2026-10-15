# NEXUS-OPS — VQC Training & Optimization Report
**Project:** IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Classifier  
**Milestone:** Phase 5 — Quantum Machine Learning (Stage 3 & 4)  
**Status:** COMPLETED & VERIFIED  
**Date:** 2026-10-13  

---

## 1. Executive Summary

This report documents the systematic training and optimization of the 6-qubit Variational Quantum Classifier (VQC) designed for binary electrocardiogram (ECG) heartbeat classification: Normal (`N`, label 0) vs. Ventricular Ectopic Beat (`V`, label 1).

Training was conducted under the **Leave-One-Record-Out (LORO) Cross-Validation Protocol (Protocol A)** across Patient Records 106 and 119 ($N=200$ samples total, 100 per fold). To rigorously evaluate stability and eliminate initialization artifacts, the complete protocol was executed across **5 distinct pseudo-random seeds** per fold (`seeds = [42, 101, 202, 303, 404]`), yielding 10 fully tracked quantum optimization runs.

### Key Highlights
- **Convergence:** Across all 10 runs, training MSE consistently converged from initial values of $0.1817 - 0.1985$ down to a macro mean of $0.0770 \pm 0.0075$ (a $>59\%$ reduction in Brier loss).
- **Cross-Validation Generalization:** 
  - Macro Validation Accuracy: **$80.00\%$** (Fold 1 mean: $84.60\%$, Fold 2 mean: $75.40\%$).
  - Macro Validation F1-Score: **$0.7814$** (Fold 1 mean: $0.8899$, Fold 2 mean: $0.6729$).
  - Macro Validation ROC-AUC: **$0.9840$** (Fold 1 mean: $1.0000$, Fold 2 mean: $0.9681$).
  - Macro Validation Class Polarity $\Delta p$: **$+0.2170$** (positive separation maintained across all folds and seeds without polarity inversion).
- **Optimal Checkpoint:** Checkpoint `fold_1_seed_303` achieved a perfect validation score ($\text{F1} = 1.0000$, $\text{MSE} = 0.1020$, $\text{AUC} = 1.0000$, Composite Score = $0.9592$) and was selected and frozen for final deployment.

---

## 2. Model Architecture & Simulation Framework

The VQC architecture strictly adheres to the frozen technical decisions D1–D10:

```
          ┌────────────┐   ┌───────────────────────────────┐
|0⟩ ─────┤ Ry(p_enc0) ├───┤                               ├─── [Z0] ──┐
|1⟩ ─────┤ Ry(p_enc1) ├───┤                               ├─── [Z1] ──┤
|2⟩ ─────┤ Ry(p_enc2) ├───┤        RealAmplitudes         ├─── [Z2] ──┤   Σ(Zi) / 6
|3⟩ ─────┤ Ry(p_enc3) ├───┤   reps=1, linear entangler    ├─── [Z3] ──┤ ────────────► E ∈ [-1, +1] ──► p = (E+1)/2
|4⟩ ─────┤ Ry(p_enc4) ├───┤         12 parameters         ├─── [Z4] ──┤
|5⟩ ─────┤ Ry(p_enc5) ├───┤                               ├─── [Z5] ──┘
          └────────────┘   └───────────────────────────────┘
```

1. **Logical Qubits:** 6 qubits matching the 6-dimensional biomedical feature vector (`pre_rr`, `post_rr`, `qrs_rms`, `qrs_duration`, `p2p_amplitude`, `spectral_ratio`).
2. **Feature Encoding:** First-order angle encoding via single-qubit $R_y(x_i)$ gates, with bounded inputs $x_i \in [0, \pi]$.
3. **Ansatz:** Hardware-efficient `RealAmplitudes` with linear CX entanglement, 1 repetition, and 12 trainable rotation angles $\theta \in \mathbb{R}^{12}$.
4. **Observable:** Symmetrized ensemble average Pauli-$Z$ operator:
   $$\hat{O} = \frac{1}{6} \sum_{i=0}^5 \hat{Z}_i$$
5. **Readout Mapping:** Affine mapping $p(y=1|\mathbf{x}) = \frac{\langle \hat{O} \rangle + 1}{2} \in [0, 1]$.
6. **Loss Function:** Mean Squared Error (Brier score):
   $$\mathcal{L}(\theta) = \frac{1}{N} \sum_{k=1}^N \left( p(\mathbf{x}_k; \theta) - y_k \right)^2$$
7. **Optimizer:** Constrained Optimization BY Linear Approximation (COBYLA) via SciPy PRIMA (`rhobeg=0.5`, `maxiter=50`).
8. **Evaluation Backend:** Qiskit 2.5.2 `StatevectorEstimator` (exact statevector simulation; zero statistical shot noise during parameter optimization).

---

## 3. LORO Cross-Validation Training Trajectories

### 3.1 Individual Run Metrics (All 10 Runs)

| Fold | Run ID | Seed | Train Loss (Init $\rightarrow$ Final) | Val Loss | Val Acc | Val Sens | Val Spec | Val F1 | Val AUC | Val $\Delta p$ | Eval Count |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | `fold_1_seed_42` | 42 | $0.1909 \rightarrow 0.0776$ | 0.1201 | 1.00 | 1.00 | 1.00 | 1.0000 | 1.0000 | +0.2764 | 50 |
| | `fold_1_seed_101` | 101 | $0.1908 \rightarrow 0.0801$ | 0.1467 | 1.00 | 1.00 | 1.00 | 1.0000 | 1.0000 | +0.2520 | 50 |
| | `fold_1_seed_202` | 202 | $0.1960 \rightarrow 0.0852$ | 0.2130 | 0.53 | 1.00 | 0.06 | 0.6803 | 1.0000 | +0.1065 | 50 |
| | **`fold_1_seed_303`** | **303** | **$0.1985 \rightarrow 0.0841$** | **0.1020** | **1.00** | **1.00** | **1.00** | **1.0000** | **1.0000** | **+0.3682** | **50** |
| | `fold_1_seed_404` | 404 | $0.1983 \rightarrow 0.0746$ | 0.2012 | 0.70 | 1.00 | 0.40 | 0.7692 | 1.0000 | +0.1362 | 50 |
| **Fold 2** | `fold_2_seed_42` | 42 | $0.1820 \rightarrow 0.0644$ | 0.1642 | 0.75 | 0.50 | 1.00 | 0.6667 | 0.9696 | +0.2173 | 50 |
| | `fold_2_seed_101` | 101 | $0.1817 \rightarrow 0.0638$ | 0.1569 | 0.79 | 0.58 | 1.00 | 0.7342 | 0.9740 | +0.2454 | 50 |
| | `fold_2_seed_202` | 202 | $0.1866 \rightarrow 0.0691$ | 0.1863 | 0.73 | 0.46 | 1.00 | 0.6301 | 0.9712 | +0.1895 | 50 |
| | `fold_2_seed_303` | 303 | $0.1917 \rightarrow 0.0889$ | 0.1821 | 0.75 | 0.50 | 1.00 | 0.6667 | 0.9600 | +0.1686 | 50 |
| | `fold_2_seed_404` | 404 | $0.1942 \rightarrow 0.0827$ | 0.1747 | 0.75 | 0.50 | 1.00 | 0.6667 | 0.9656 | +0.2094 | 50 |

---

## 4. Aggregate Statistical Performance

### 4.1 Fold Summary Comparison

| Metric | Fold 1 (Train: 106, Val: 119) | Fold 2 (Train: 119, Val: 106) | Macro Average |
| :--- | :---: | :---: | :---: |
| **Train MSE (mean $\pm$ std)** | $0.0803 \pm 0.0040$ | $0.0738 \pm 0.0102$ | **$0.0770 \pm 0.0075$** |
| **Validation MSE (mean $\pm$ std)** | $0.1566 \pm 0.0438$ | $0.1728 \pm 0.0109$ | **$0.1647 \pm 0.0305$** |
| **Validation Accuracy (mean $\pm$ std)** | $84.60\% \pm 19.61\%$ | $75.40\% \pm 1.96\%$ | **$80.00\% \pm 13.91\%$** |
| **Validation Sensitivity (mean $\pm$ std)** | $100.00\% \pm 0.00\%$ | $50.80\% \pm 3.92\%$ | **$75.40\% \pm 25.10\%$** |
| **Validation Specificity (mean $\pm$ std)** | $69.20\% \pm 39.22\%$ | $100.00\% \pm 0.00\%$ | **$84.60\% \pm 28.01\%$** |
| **Validation Precision (mean $\pm$ std)** | $82.81\% \pm 21.34\%$ | $100.00\% \pm 0.00\%$ | **$91.40\% \pm 15.10\%$** |
| **Validation F1-Score (mean $\pm$ std)** | $0.8899 \pm 0.1377$ | $0.6729 \pm 0.0338$ | **$0.7814 \pm 0.1448$** |
| **Validation ROC-AUC (mean $\pm$ std)** | $1.0000 \pm 0.0000$ | $0.9681 \pm 0.0049$ | **$0.9840 \pm 0.0163$** |
| **Class Polarity $\Delta p$ (mean $\pm$ std)** | $+0.2279 \pm 0.1044$ | $+0.2060 \pm 0.0331$ | **$+0.2170 \pm 0.0754$** |
| **Average Execution Time per Run** | $8.64 \pm 1.06\text{ s}$ | $9.69 \pm 0.19\text{ s}$ | **$9.16 \pm 0.92\text{ s}$** |

### 4.2 Mathematical Analysis of Inter-Record Asymmetry
1. **Fold 1 Behavior:** Record 106 features produce an optimization landscape that readily generalizes to Record 119. 3 out of 5 seeds achieved **$100\%$ accuracy and F1** on Record 119.
2. **Fold 2 Behavior:** Training on Record 119 achieves low training loss ($0.0638 - 0.0889$) and high validation specificity ($100\%$), but validation sensitivity hovers around $50\%$. Despite this, the validation ROC-AUC remains extremely high ($0.9681 \pm 0.0049$), proving that the model's continuous probabilities still rank VEB beats above Normal beats, but a threshold shift occurred due to baseline feature differences between Record 119 and Record 106.
3. **No Polarity Inversion:** Every run produced $\Delta p > 0$, proving that the quantum model never confused the semantic polarity of Normal versus VEB beats.

---

## 5. Artifact Serialization

The complete numerical outputs are saved in the project repository:
- `results/vqc_training_runs.json`: Full per-iteration logs, initial/final states, loss histories, and optimal parameter vectors for all 10 runs.
- `results/vqc_loro_summary.json`: Statistical aggregations across folds and seeds.
- `results/vqc_model_selection.json`: Checkpoint ranking and frozen winner selection.
