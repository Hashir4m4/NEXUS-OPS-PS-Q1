# NEXUS-OPS — VQC Model Selection Protocol & Parameter Freeze
**Project:** IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Classifier  
**Milestone:** Phase 5 — Quantum Machine Learning  
**Status:** FROZEN & SEALED PRIOR TO HELD-OUT COHORT EVALUATION  
**Timestamp:** 2026-10-13T11:45:00Z  

---

## 1. Governance & Strict Quarantine Invariant

To guarantee absolute scientific integrity and prevent test-set leakage:
1. **Quarantine Enforcement:** Records 200 and 208 (`data/processed/features_test.csv`, $N=100$) have **NEVER** been inspected, fitted, transformed, or evaluated during any phase of feature selection, hyperparameter tuning, optimizer exploration, or candidate ranking.
2. **Strict Cross-Validation Evidence:** Model selection is conducted **exclusively** on the Leave-One-Record-Out (LORO) cross-validation experiments spanning Patient Records 106 and 119 ($N=200$, 10 distinct optimization runs across 5 random seeds per fold).
3. **Pre-Commitment Rule:** The mathematical selection criterion and the winning candidate checkpoint are irrevocably frozen in this document **prior** to running any inference on the held-out test cohort.

---

## 2. Selection Objective & Decision Rule

### 2.1 Multi-Criteria Mathematical Objective
A biomedical classifier deployed across unseen patient cohorts must simultaneously exhibit:
- **Low Calibration Error / Loss:** Low validation Mean Squared Error ($\text{MSE}_{\text{val}}$).
- **High Discriminative Utility:** High validation F1-score ($\text{F1}_{\text{val}}$).
- **Clinical Fairness / Parity:** Low disparity between sensitivity (true positive rate on Ventricular Ectopic Beats) and specificity (true negative rate on Normal beats).

We define the pre-committed **Balanced Validation Composite Score**:
$$\text{Score} = 0.4 \cdot (1 - \text{MSE}_{\text{val}}) + 0.4 \cdot \text{F1}_{\text{val}} + 0.2 \cdot (1 - |\text{Sensitivity}_{\text{val}} - \text{Specificity}_{\text{val}}|)$$

The optimal candidate $\theta^*$ is selected by maximizing $\text{Score}$. Ties are broken by lowest $\text{MSE}_{\text{val}}$.

---

## 3. Candidate Evaluation & Complete Ranking

All 10 LORO training runs ($2 \text{ folds} \times 5 \text{ seeds}$, 50 COBYLA iterations each) evaluated on the cross-validation partition:

| Rank | Candidate Run ID | Train Record | Val Record | Seed | Composite Score | Val F1 | Val MSE | Val Sens | Val Spec | Val Acc | Val ROC-AUC | Train MSE |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **`fold_1_seed_303`** | **106** | **119** | **303** | **0.9592** | **1.0000** | **0.1020** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0.0841** |
| 2 | `fold_1_seed_42` | 106 | 119 | 42 | 0.9520 | 1.0000 | 0.1201 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0776 |
| 3 | `fold_1_seed_101` | 106 | 119 | 101 | 0.9413 | 1.0000 | 0.1467 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0801 |
| 4 | `fold_2_seed_101` | 119 | 106 | 101 | 0.7469 | 0.7342 | 0.1569 | 0.5800 | 1.0000 | 0.7900 | 0.9740 | 0.0638 |
| 5 | `fold_1_seed_404` | 106 | 119 | 404 | 0.7072 | 0.7692 | 0.2012 | 1.0000 | 0.4000 | 0.7000 | 1.0000 | 0.0746 |
| 6 | `fold_2_seed_42` | 119 | 106 | 42 | 0.7010 | 0.6667 | 0.1642 | 0.5000 | 1.0000 | 0.7500 | 0.9696 | 0.0644 |
| 7 | `fold_2_seed_404` | 119 | 106 | 404 | 0.6968 | 0.6667 | 0.1747 | 0.5000 | 1.0000 | 0.7500 | 0.9656 | 0.0827 |
| 8 | `fold_2_seed_303` | 119 | 106 | 303 | 0.6938 | 0.6667 | 0.1821 | 0.5000 | 1.0000 | 0.7500 | 0.9600 | 0.0889 |
| 9 | `fold_2_seed_202` | 119 | 106 | 202 | 0.6695 | 0.6301 | 0.1863 | 0.4600 | 1.0000 | 0.7300 | 0.9712 | 0.0691 |
| 10 | `fold_1_seed_202` | 106 | 119 | 202 | 0.5989 | 0.6803 | 0.2130 | 1.0000 | 0.0600 | 0.5300 | 1.0000 | 0.0852 |

---

## 4. Winning Model Selection & Frozen Parameters

The winning model is **`fold_1_seed_303`** with a composite validation score of **0.9592**.

### 4.1 Checkpoint Identification
- **Run Identifier:** `fold_1_seed_303`
- **Source Fold:** Fold 1 (Training: Record 106, Validation: Record 119)
- **Random Seed:** `303`
- **Optimizer Steps / Evaluations:** 32 trust-region iterations / 50 function evaluations
- **Training MSE:** 0.0841
- **Validation MSE:** 0.1020
- **Validation F1:** 1.0000
- **Validation Sensitivity:** 1.0000 (50/50 VEBs correctly identified)
- **Validation Specificity:** 1.0000 (50/50 Normal beats correctly identified)
- **Validation ROC-AUC:** 1.0000

### 4.2 Frozen Variational Parameter Vector ($\theta^* \in \mathbb{R}^{12}$)
The exact 12-dimensional parameter vector for the `RealAmplitudes(reps=1)` ansatz is frozen as follows:

```json
[
  0.48888847284211656,
  -1.2636229184088255,
  -0.49618531730782184,
  -0.9822884876903525,
  -0.8177933416414555,
  -0.7963986558464293,
  -0.3341059768227328,
  -0.3669351575495604,
  -0.8660987972603893,
  -1.034837255605418,
  0.5613811143193971,
  0.4214387999586761
]
```

---

## 5. Formal Protocol Sign-Off

- **Scientific Integrity Invariant:** Up to this moment, `data/processed/features_test.csv` has remained completely untouched and quarantined.
- **Next Stage Authorized:** Stage 6 — Evaluation of the frozen winning checkpoint `fold_1_seed_303` on the quarantined held-out test cohort (Records 200 and 208) using the leak-free training scaler fit on Records 106 & 119.
