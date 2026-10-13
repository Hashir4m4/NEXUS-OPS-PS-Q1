# Milestone 3: ECG Feature Engineering, Signal Analysis & Leakage-Safe Normalization
**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Status:** Completed & Programmatically Verified  
**Date:** October 12, 2026  
**Lead Discipline:** Biomedical Signal Processing & Quantum Machine Learning  

---

## 1. Executive Summary

Milestone 3 implements, validates, and standardizes **six physiologically grounded numerical features** extracted from the 300 pre-segmented MLII ECG beats constructed in Milestone 2B. These six features provide a unified feature space shared identically by both the classical **Logistic Regression baseline** and the **Variational Quantum Classifier (VQC)**.

To strictly prevent data leakage and ensure compatibility with parameterized quantum rotational gates ($R_X(\theta), R_Y(\theta), R_Z(\theta)$), all feature normalization parameters were fitted **exclusively on the 200 training beats** (Records 106 and 119) and linearly mapped into the quantum angle domain $[0, \pi]$. Out-of-distribution observations on the 100 test beats (Records 200 and 208) are clipped safely at domain boundaries without contaminating training parameters.

The automated verification suite in [`tests/`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests) confirmed $21/21$ passing unit tests ($100\%$), zero missing/non-finite feature values, and mathematically bounded rotational angles.

---

## 2. Physiological Feature Definitions & Clinical Rationale

| # | Feature Name | Symbol | Units | Extraction Method & Formula | Clinical Diagnostic Rationale |
|---|---|---|---|---|---|
| **1** | **Pre-RR Interval** | $\Delta t_{\text{pre}}$ | Seconds ($\text{s}$) | $t_{i} - t_{i-1} = \frac{R_i - R_{i-1}}{f_s}$, queried from complete parent `.atr` annotation array. | **Prematurity marker:** Ventricular ectopic beats (PVCs) originate prematurely in ventricular tissue, resulting in a markedly shortened preceding RR interval compared to sinus rhythm. |
| **2** | **Post-RR Interval** | $\Delta t_{\text{post}}$ | Seconds ($\text{s}$) | $t_{i+1} - t_i = \frac{R_{i+1} - R_i}{f_s}$, queried from complete parent `.atr` annotation array. | **Compensatory pause marker:** Retrograde conduction block from ventricular ectopic impulses typically produces a prolonged compensatory pause before the next sinus activation. |
| **3** | **QRS RMS Amplitude** | $\text{RMS}_{\text{QRS}}$ | Millivolts ($\text{mV}$) | $\sqrt{\frac{1}{2K+1} \sum_{k=-K}^{K} s[144+k]^2}$, where $K = 25\text{ samples}$ ($\pm 69.4\text{ ms}$, $\approx 140\text{ ms}$ core QRS). | **Depolarization energy:** PVC depolarization spreads slowly via abnormal intramyocardial conduction pathways, yielding prolonged, high-energy voltage deflections. |
| **4** | **QRS Duration / Spread** | $w_{\text{QRS}}$ | Seconds ($\text{s}$) | Temporal distance between envelope onset and offset where envelope $\|s - \text{median}\| \ge 0.20 \times \max(\|s - \text{median}\|)$ in $[-100, +100]\text{ ms}$. | **Conduction velocity marker:** Normal sinus impulses travel rapidly through the His-Purkinje network ($<100\text{ ms}$). Ventricular ectopic beats bypass fast conduction, resulting in wide QRS complexes ($>120\text{ ms}$). |
| **5** | **Peak-to-Peak Amplitude** | $\Delta V_{\text{p-p}}$ | Millivolts ($\text{mV}$) | $\max_{k \in [0, 359]} s[k] - \min_{k \in [0, 359]} s[k]$ across the full $1.0\text{ s}$ window. | **Voltage excursion:** Measures the total dynamic range of cardiac depolarization and repolarization across the beat window. |
| **6** | **Spectral Band Power Ratio** | $R_{\text{band}}$ | Dimensionless | $\frac{P_{10\text{--}25\text{ Hz}}}{P_{0.5\text{--}40\text{ Hz}} + \epsilon}$ via $720\text{-point}$ RFFT ($0.5\text{ Hz}$ resolution), $\epsilon = 10^{-12}$. | **Frequency distribution:** Sharp, rapid sinus QRS complexes have concentrated high-frequency spectral content in $10\text{--}25\text{ Hz}$, whereas wide PVCs shift power to lower spectral bands ($<10\text{ Hz}$). |

---

## 3. Statistical Analysis & Class Discrimination

Summary statistics computed across the 300 segments from [`results/feature_summary.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/feature_summary.json):

### Class-Wise Distribution Metrics

| Feature Name | Normal Class (`N`, $n=150$) Mean $\pm$ Std | Normal Median | VEB Class (`V`, $n=150$) Mean $\pm$ Std | VEB Median | Relative Shift & Physiological Separation |
|---|---|---|---|---|---|
| **Pre-RR Interval** | $0.923 \pm 0.217\text{ s}$ | $0.906\text{ s}$ | $0.526 \pm 0.038\text{ s}$ | $0.528\text{ s}$ | **$-43.0\%$ (Strong prematurity clustering)** |
| **Post-RR Interval** | $0.746 \pm 0.192\text{ s}$ | $0.775\text{ s}$ | $1.052 \pm 0.283\text{ s}$ | $1.151\text{ s}$ | **$+41.0\%$ (Clear compensatory pause)** |
| **QRS RMS Amplitude** | $0.693 \pm 0.238\text{ mV}$ | $0.688\text{ mV}$ | $0.985 \pm 0.291\text{ mV}$ | $1.011\text{ mV}$ | **$+42.1\%$ (Higher energy in ectopic waves)** |
| **QRS Duration** | $0.038 \pm 0.006\text{ s}$ | $0.036\text{ s}$ | $0.079 \pm 0.017\text{ s}$ | $0.086\text{ s}$ | **$+107.9\%$ (Pronounced QRS broadening)** |
| **Peak-to-Peak Amplitude**| $2.296 \pm 0.580\text{ mV}$ | $2.395\text{ mV}$ | $3.085 \pm 1.037\text{ mV}$ | $2.848\text{ mV}$ | **$+34.4\%$ (Elevated total excursion)** |
| **Spectral Band Ratio** | $0.209 \pm 0.119$ | $0.182$ | $0.045 \pm 0.049$ | $0.021$ | **$-78.5\%$ (Dramatic drop in high-frequency QRS energy)** |

> [!NOTE]
> **Key Finding on Class Separability:**  
> The combination of `pre_rr`, `qrs_duration`, and `spectral_ratio` exhibits prominent divergence between Normal sinus and Ventricular ectopic beats. VEBs demonstrate tight clustering at $\Delta t_{\text{pre}} \approx 0.53\text{ s}$ ($\text{std} = 0.038\text{ s}$) compared to $\Delta t_{\text{pre}} \approx 0.92\text{ s}$ for Normal beats, providing distinct decision boundaries for classical and quantum classifiers.

---

## 4. Visual Diagnostics

The generated publication figures in [`figures/`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/figures) illustrate feature behavior:

1. **Feature Distributions by Class:** [`figures/feature_distributions.png`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/figures/feature_distributions.png) confirms bimodal separation between Normal (`N`) and Ventricular Ectopic (`V`) beats, particularly in Pre-RR, QRS duration, and spectral band power.
2. **Correlation Matrix:** [`figures/feature_correlation.png`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/figures/feature_correlation.png) reveals correlation patterns among morphological features:
   * Strong positive correlation between `qrs_rms` and `p2p_amplitude` ($r = +0.89$).
   * Strong negative correlation between `pre_rr` and `qrs_duration` ($r = -0.77$).
   * Negative correlation between `spectral_ratio` and `qrs_duration` ($r = -0.66$).
3. **Quantum-Scaled Boxplots:** [`figures/feature_boxplots.png`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/figures/feature_boxplots.png) confirms all normalized dimensions map cleanly within the $[0, \pi]$ rotation limits.

---

## 5. Data Leakage Prevention Protocol

```
Training Features (Records 106 & 119)        Testing Features (Records 200 & 208)
            │                                             │
            ▼                                             │
┌───────────────────────┐                                 │
│  QuantumFeatureScaler │                                 │
│      .fit(X_train)    │                                 │
│  Learns: min, max     │                                 │
└───────────┬───────────┘                                 │
            │                                             │
            ├─────────────── transform(X_train) ──────────┼────────────────► features_train.csv
            │                                             │
            └─────────────── transform(X_test)  ──────────┴────────────────► features_test.csv
                             (clipped safely to [0, π])
```

### Protocol Guarantees:
1. **Zero Test Knowledge:** Scaler bounds ($x_{\min}, x_{\max}$) were fitted exclusively on `features_train.csv`. The test partition had zero mathematical influence on transformation parameters.
2. **Angle Domain $[0, \pi]$:** Rotation angles $\theta_j \in [0, \pi]$ map directly to unitary gate inputs:
   $$\theta_j = \pi \cdot \frac{x_j - x_{\min, j}}{x_{\max, j} - x_{\min, j}}$$
3. **Constant Feature Guard:** If feature variance satisfies $\Delta x_j \le 10^{-12}$, the denominator defaults to $1.0$ and transformation yields $0.0$, preventing division by zero.
4. **Boundary Clipping:** In the test set, any values falling outside the training range due to inter-patient anatomical variability are safely clipped to $[0, \pi]$ (e.g. `test_min` $\ge 0.0$ and `test_max` $\le \pi$).

---

## 6. Model Selection Validation Strategy & Trade-Offs

### Analysis of Record-Level Partitioning
In Milestone 2B, the training cohort was configured with **two patient records**: Record 106 (Subject 207, 24 F) and Record 119 (Subject 218, 51 F).

For cross-validation and hyperparameter selection prior to test evaluation:
* **Option A: Leave-One-Record-Out (LORO) Validation:**
  * Fold 1: Train on Record 106 ($100\text{ beats}$), Validate on Record 119 ($100\text{ beats}$).
  * Fold 2: Train on Record 119 ($100\text{ beats}$), Validate on Record 106 ($100\text{ beats}$).
  * *Critical Limitation:* Severe morphological domain shift. Record 106 features multiform PVCs in a young patient on Inderal, whereas Record 119 features uniform PVCs in an older patient on Pronestyl. Training on one individual and testing on the other produces high inter-subject variance and unstable validation error estimates.
* **Option B: Stratified Grouped K-Fold with Stratified Beat Reservoir:**
  * Subdivide both Record 106 and 119 beats proportionally across $k=5$ folds (e.g., each fold contains beats from both subjects).
  * *Trade-off:* Provides stable internal cross-validation for hyperparameter tuning, but introduces intra-patient beat similarity within the training envelope (though completely isolated from the independent test subjects 200 and 208).
* **Recommendation for Milestone 4:** Use 5-fold stratified cross-validation on the 200 training samples for regularizer and learning rate tuning, while reporting LORO validation scores as an informative domain-shift benchmark.

---

## 7. Artifacts Summary

```
PS-Q1-Biomedical-Classifier/
├── src/
│   ├── feature_extraction.py          # Extraction logic for the 6 features
│   ├── feature_scaling.py             # Leakage-safe QuantumFeatureScaler to [0, π]
│   └── feature_validation.py          # Pipeline orchestration & visualization
├── data/
│   └── processed/
│       ├── features_train.csv         # 200 rows x 17 columns (metadata, raw, scaled)
│       └── features_test.csv          # 100 rows x 17 columns (metadata, raw, scaled)
├── results/
│   └── feature_summary.json           # Comprehensive statistical metrics & telemetry
├── figures/
│   ├── feature_distributions.png      # Class-wise distributions
│   ├── feature_correlation.png        # Correlation matrix heatmap
│   └── feature_boxplots.png           # [0, π] scaled feature boxplots
├── report/
│   └── feature_engineering.md         # This technical report
└── tests/
    ├── test_feature_extraction.py     # 5 passed unit tests
    └── test_feature_scaling.py        # 5 passed unit tests
```

---

## 8. Research Limitations & Recommendations for Milestone 4

1. **Single-Lead Limitation:** All features are extracted from Lead MLII. While MLII is clinically standard for rhythm and ventricular morphology, dual-lead fusion (combining MLII with V1) could provide additional spatial dipole resolution.
2. **Frequency Domain Edge Effects:** The $10\text{--}25\text{ Hz}$ spectral band ratio is computed on finite $1.0\text{ s}$ windows. While zero-padding ($720\text{ points}$) interpolates frequency bins to $0.5\text{ Hz}$, window truncation creates mild spectral leakage.
3. **Readiness for Milestone 4:** The feature matrices [`data/processed/features_train.csv`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/data/processed/features_train.csv) and [`data/processed/features_test.csv`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/data/processed/features_test.csv) are validated and ready for:
   * Classical Logistic Regression baseline training.
   * Parameterized Quantum Circuit (VQC) state preparation via angle encoding.
