# Milestone 4: Classical Machine Learning Baseline Report
**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Status:** Completed & Programmatically Verified  
**Date:** October 12, 2026  
**Lead Discipline:** Biomedical Machine Learning & Experimental Evaluation  

---

## 1. Executive Summary

Milestone 4 establishes the **classical machine learning baseline** for the binary ECG classification task (Normal Sinus Beat `N` = 0 vs. Ventricular Ectopic Beat `V` = 1) across the standardized 300-segment cohort. Three frozen candidate models were evaluated:
1. **L2-Regularized Logistic Regression** (linear benchmark with closed-form coefficient interpretability)
2. **Support Vector Machine with RBF Kernel** (maximum-margin non-linear benchmark)
3. **Random Forest Classifier** (100-tree decision ensemble)

All models intake identical six-dimensional feature vectors scaled into the quantum-compatible domain $[0, \pi]$ using parameters fitted **exclusively on the training partition** (Records 106 & 119). 

### Key Empirical Findings:
* **Final Test Evaluation (Records 200 & 208, $n=100$):**  
  * **Logistic Regression:** Accuracy = **$92.0\%$**, Sensitivity = **$100.0\%$**, Specificity = **$84.0\%$**, F1-Score = **$92.6\%$**, ROC-AUC = **$0.996$** (Confusion matrix: $\text{TN}=42, \text{FP}=8, \text{FN}=0, \text{TP}=50$).
  * **SVM (RBF Kernel):** Accuracy = **$91.0\%$**, Sensitivity = **$100.0\%$**, Specificity = **$82.0\%$**, F1-Score = **$91.7\%$**, ROC-AUC = **$0.996$** (Confusion matrix: $\text{TN}=41, \text{FP}=9, \text{FN}=0, \text{TP}=50$).
  * **Random Forest:** Accuracy = **$77.0\%$**, Sensitivity = **$100.0\%$**, Specificity = **$54.0\%$**, F1-Score = **$81.3\%$**, ROC-AUC = **$0.986$** (Confusion matrix: $\text{TN}=27, \text{FP}=23, \text{FN}=0, \text{TP}=50$).
* **Zero False Negatives:** Across all three models, Sensitivity on VEB beats reached **$100.0\%$ ($0\text{ False Negatives}$)**. All errors on the test set were False Positives caused by baseline noise and morphological axis shifts in test subjects 200 and 208.
* **Leave-One-Record-Out (LORO) Validation:** Revealed pronounced inter-subject domain asymmetry between Fold 1 ($93\%\text{--}100\%$ accuracy) and Fold 2 ($60\%\text{--}75\%$ accuracy), proving that single-subject training cannot capture broader clinical variance.

---

## 2. Pre-Experiment Audit & Input Data Verification (Task 1)

Prior to model fitting, the pipeline audited feature consistency:
* **Feature Set:** Exactly six numerical dimensions: `pre_rr`, `post_rr`, `qrs_rms`, `qrs_duration`, `p2p_amplitude`, `spectral_ratio`.
* **Zero Missing / Infinite Inputs:** Verified $0\text{ NaN}$, $0\text{ Inf}$, and $0\text{ Null}$ values across all 300 rows.
* **Label Mapping:** Binary target $y \in \{0, 1\}$, where $0 = \text{Normal ('N')}$ and $1 = \text{VEB ('V')}$.
* **Partition Segregation:** Training features ($n=200$, Records 106 & 119) and testing features ($n=100$, Records 200 & 208) exhibit zero subject overlap.
* **Scaler Hygiene:** All preprocessing transformations were fitted strictly on training data (`features_train.csv`).

---

## 3. Candidate Models & Frozen Configurations (Task 2)

All model hyperparameters were frozen in [`src/classical_models.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/classical_models.py) prior to evaluation:

```python
# 1. Logistic Regression
LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=1000, random_state=42)

# 2. Support Vector Classifier (RBF Kernel)
SVC(C=1.0, kernel="rbf", gamma="scale", probability=True, random_state=42)

# 3. Random Forest Classifier
RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_split=4, random_state=42)
```

---

## 4. Patient-Level Leave-One-Record-Out (LORO) Validation (Task 3)

To examine inter-subject generalizability within the training set, Leave-One-Record-Out cross-validation was conducted across Records 106 and 119:

### LORO Validation Performance Table

| Evaluation Fold | Candidate Model | Accuracy | Sensitivity (VEB) | Specificity (Normal) | Precision | F1-Score | ROC-AUC | Confusion Matrix (TN, FP, FN, TP) |
|---|---|---|---|---|---|---|---|---|
| **Fold 1**<br>*(Train: 106 \| Val: 119)* | **Logistic Regression** | **$0.9700$** | **$1.0000$** | $0.9400$ | $0.9434$ | **$0.9709$** | $1.0000$ | $\text{TN}=47, \text{FP}=3, \text{FN}=0, \text{TP}=50$ |
| | **SVM (RBF Kernel)** | $0.9300$ | **$1.0000$** | $0.8600$ | $0.8772$ | $0.9346$ | $1.0000$ | $\text{TN}=43, \text{FP}=7, \text{FN}=0, \text{TP}=50$ |
| | **Random Forest** | **$1.0000$** | **$1.0000$** | **$1.0000$** | **$1.0000$** | **$1.0000$** | $1.0000$ | $\text{TN}=50, \text{FP}=0, \text{FN}=0, \text{TP}=50$ |
| **Fold 2**<br>*(Train: 119 \| Val: 106)* | **Logistic Regression** | $0.6400$ | $0.2800$ | **$1.0000$** | **$1.0000$** | $0.4375$ | **$1.0000$** | $\text{TN}=50, \text{FP}=0, \text{FN}=36, \text{TP}=14$ |
| | **SVM (RBF Kernel)** | $0.6000$ | $0.2000$ | **$1.0000$** | **$1.0000$** | $0.3333$ | **$1.0000$** | $\text{TN}=50, \text{FP}=0, \text{FN}=40, \text{TP}=10$ |
| | **Random Forest** | $0.7500$ | $0.5000$ | **$1.0000$** | **$1.0000$** | $0.6667$ | $0.9892$ | $\text{TN}=50, \text{FP}=0, \text{FN}=25, \text{TP}=25$ |
| **Mean LORO Score** | **Logistic Regression** | $0.8050$ | $0.6400$ | $0.9700$ | $0.9717$ | $0.7042$ | **$1.0000$** | — |
| | **SVM (RBF Kernel)** | $0.7650$ | $0.6000$ | $0.9300$ | $0.9386$ | $0.6340$ | **$1.0000$** | — |
| | **Random Forest** | **$0.8750$** | **$0.7500$** | **$1.0000$** | **$1.0000$** | **$0.8333$** | $0.9946$ | — |

### Scientific Analysis of Fold Asymmetry
* **Fold 1 Generalization:** Record 106 features multiform PVCs in a young patient (24 F). The high morphological variance in Record 106 spans a wide decision space; consequently, models trained on 106 generalize cleanly to the uniform PVCs of Record 119 ($93\%\text{--}100\%$ accuracy).
* **Fold 2 Domain Shift:** Record 119 features uniform PVCs in an older subject (51 F) on Pronestyl. Models trained on 119 learn a tightly calibrated decision boundary. When tested on Record 106's multiform PVCs, sensitivity drops sharply ($20\%\text{--}50\%$), even though ROC-AUC remains near $1.000$ (indicating correct sample ranking but a shifted decision threshold).
* **Takeaway:** Single-subject training yields high threshold sensitivity, confirming that training on both records ($n=200$) is necessary to form an adequate baseline boundary.

---

## 5. Final Held-Out Test Evaluation (Task 4)

Trained on the combined training cohort (Records 106 & 119, $n=200$) and evaluated once on independent test subjects (Records 200 & 208, $n=100$):

### Independent Test Set Performance Table

| Model | Test Accuracy | Sensitivity (VEB Recall) | Specificity (Normal Recall) | Precision | F1-Score | ROC-AUC | Confusion Matrix [TN, FP, FN, TP] |
|---|---|---|---|---|---|---|---|
| **Logistic Regression** | **$92.00\%$** | **$100.00\%$** | **$84.00\%$** | **$86.21\%$** | **$92.59\%$** | **$0.9960$** | $[42, 8, 0, 50]$ |
| **SVM (RBF Kernel)** | **$91.00\%$** | **$100.00\%$** | **$82.00\%$** | **$84.75\%$** | **$91.74\%$** | **$0.9960$** | $[41, 9, 0, 50]$ |
| **Random Forest** | **$77.00\%$** | **$100.00\%$** | **$54.00\%$** | **$68.49\%$** | **$81.30\%$** | **$0.9864$** | $[27, 23, 0, 50]$ |

```
                       TEST CONFUSION MATRICES
                       
   Logistic Regression           SVM (RBF Kernel)            Random Forest
       Pred: 0  Pred: 1             Pred: 0  Pred: 1            Pred: 0  Pred: 1
True 0: [ 42       8 ]      True 0: [ 41       9 ]     True 0: [ 27      23 ]
True 1: [  0      50 ]      True 1: [  0      50 ]     True 1: [  0      50 ]
Acc: 92.0% | Sens: 100%     Acc: 91.0% | Sens: 100%    Acc: 77.0% | Sens: 100%
```

---

## 6. Scientific Interpretation & Error Patterns (Task 5)

### Clinical Sensitivity vs. Specificity Profile
* **Zero False Negatives ($\text{FN}=0$):** In cardiac arrhythmia monitoring, false negatives (failing to detect ventricular ectopic beats) represent the highest clinical risk. All three models successfully captured $100\%$ of the VEBs in the test set ($50/50$).
* **False Positive Dynamics:** Errors on the test set were exclusively False Positives:
  * Logistic Regression misclassified $8$ Normal beats as VEB.
  * SVM misclassified $9$ Normal beats as VEB.
  * Random Forest misclassified $23$ Normal beats as VEB.
  * *Etiology:* Record 200 contains bursts of high-frequency noise and baseline artifacts (subject 219 on Digoxin/Quinidine). In addition, Record 208 exhibits a bigeminal rhythm where sinus beats are temporally coupled to PVCs, causing slight interval shortening that triggered conservative decision boundaries.

### Model Interpretability & Feature Weights

#### Logistic Regression Weights ($\beta_j$) and Odds Ratios ($\exp(\beta_j)$)
$$\text{logit}(P(V=1)) = 1.954 - 3.146 \cdot \theta_{\text{pre\_rr}} + 0.368 \cdot \theta_{\text{post\_rr}} - 0.585 \cdot \theta_{\text{qrs\_rms}} + 1.492 \cdot \theta_{\text{qrs\_dur}} + 0.413 \cdot \theta_{\text{p2p}} - 0.900 \cdot \theta_{\text{spec}}$$

| Feature | Learned Coefficient ($\beta$) | Odds Ratio $\exp(\beta)$ | Clinical Diagnostic Effect |
|---|---|---|---|
| **`pre_rr`** | **$-3.146$** | **$0.043$** | **Dominant negative predictor:** Premature arrival (shorter pre-RR) increases VEB log-odds. |
| **`qrs_duration`** | **$+1.492$** | **$4.446$** | **Strong positive predictor:** A wide QRS complex quadruples the odds of a ventricular ectopic event. |
| **`spectral_ratio`** | **$-0.900$** | **$0.407$** | **Negative predictor:** High-frequency energy concentration indicates normal His-Purkinje conduction. |
| **`p2p_amplitude`** | $+0.413$ | $1.512$ | Mild positive predictor (elevated dynamic voltage excursion). |
| **`post_rr`** | $+0.368$ | $1.445$ | Mild positive predictor (compensatory pause). |
| **`qrs_rms`** | $-0.585$ | $0.557$ | Suppressive regularizer against baseline drift. |

#### Random Forest Feature Importances (Gini Impurity)
* **`pre_rr`:** $44.7\%$
* **`qrs_duration`:** $29.7\%$
* **`spectral_ratio`:** $12.7\%$
* **`post_rr`:** $8.8\%$
* **`p2p_amplitude`:** $2.8\%$
* **`qrs_rms`:** $1.3\%$

The top three features (`pre_rr`, `qrs_duration`, `spectral_ratio`) account for **$87.1\%$ of the ensemble's splitting decisions**.

---

## 7. Comparative Figures & Diagnostics

Artifacts generated in [`figures/`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/figures):
1. **Confusion Matrices:** [`figures/classical_confusion_matrices.png`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/figures/classical_confusion_matrices.png) displays test confusion matrices side-by-side for Logistic Regression, SVM, and Random Forest.
2. **Model Comparison Bar Plot:** [`figures/classical_model_comparison.png`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/figures/classical_model_comparison.png) plots Accuracy, Sensitivity, Specificity, F1-Score, and ROC-AUC side-by-side.

---

## 8. Baseline Selection for Milestone 5 (VQC Development)

**Selected Classical Benchmark:** **L2-Regularized Logistic Regression**
* **Rationale:**
  1. Achieved the highest test accuracy ($92.0\%$) and highest F1-score ($92.6\%$).
  2. Maintained zero false negatives ($\text{Sensitivity} = 100\%$).
  3. Uses a linear hyperplane in $[0, \pi]^6$, providing the ideal direct classical counterpart to single-qubit angle encoding in a Variational Quantum Classifier (VQC). 
  4. Evaluating whether the VQC matches or outperforms Logistic Regression under ideal and noisy Aer simulations will determine whether non-linear Hilbert space entanglement yields representational advantage.

---

## 9. Limitations & Clinical Non-Readiness Statement

> [!CAUTION]
> **Regulatory & Clinical Disclaimer:**  
> This baseline is an engineering benchmark developed within an academic hackathon context. It is **not** an FDA-cleared diagnostic device and must not be used for patient care or medical triage. Limitations include:
> * Small sample size (four MIT-BIH recordings total).
> * Post-RR feature introduces an operational lookahead latency of $0.42\text{--}1.48\text{ s}$ (retrospective classification mode).
> * Single-lead MLII input without multi-lead spatial correlation.
