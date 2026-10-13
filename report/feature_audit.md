# Milestone 3.1: Scientific Feature Audit and Validation Report
**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Status:** Completed & Validated  
**Date:** October 12, 2026  
**Lead Discipline:** Biomedical Signal Processing & Quantum Machine Learning  

---

## 1. Executive Summary

Milestone 3.1 executes an exhaustive scientific audit of the six-feature biomedical ECG pipeline developed for the NEXUS-OPS PS-Q1 classifier. This audit corrects methodological assumptions, validates signal processing foundations, audits test set scaler clipping, analyzes cross-validation limits, and formally documents operational real-time latency without altering the core 300-beat dataset, class mapping, or patient partitions.

The audit established that:
1. **Ordinary 5-fold beat-level cross-validation must not be used as evidence of patient generalization**, as it mixes heartbeats from the same subject across folds.
2. **Leave-One-Record-Out (LORO) evaluation with only two training subjects** (Records 106 and 119) exhibits extreme morphological domain shift and cannot provide a statistically valid population-level variance estimate.
3. **Feature clipping to $[0, \pi]$ incurs measurable information loss**, with 14 clipping events ($2.33\%$) detected across the 100 test beats, reflecting genuine inter-patient physiological distribution shifts.
4. **Baseline wander significantly contaminates uncorrected QRS RMS amplitude**, demonstrating the necessity of local baseline subtraction.
5. **Zero-padding in spectral estimation does not increase physical frequency resolution** ($\Delta f = 1.0\text{ Hz}$ for $T = 1.0\text{ s}$) and rectangular windowing introduces significant spectral leakage ($-13\text{ dB}$ sidelobes).
6. **The pipeline operates as a retrospective beat classifier** because the Post-RR interval imposes an unavoidable physiological lookahead latency of $0.42\text{--}1.48\text{ s}$.

All 28 unit tests across five test suites passed with $100\%$ compliance.

---

## 2. Cross-Validation Audit & Model Selection Protocol (Task 1)

### Refutation of Beat-Level Stratified Cross-Validation
In standard biomedical machine learning, evaluating heartbeats pooled randomly across patients produces artificially inflated test metrics (often $>98\%$ accuracy) due to **intra-patient waveform memorization**. A beat-level 5-fold CV splits beats from Record 106 across both training and validation folds; the model easily memorizes Subject 207's unique lead axis and chest impedance. **This must never be reported as patient-level generalization.**

### Leave-One-Record-Out (LORO) Evaluation on Training Records
To test true inter-patient transfer prior to final testing, an inter-record partition was constructed on the training set:

| Evaluation Fold | Training Subject | Validation Subject | Train Distribution | Validation Distribution | Subject Demographics | Medication Context |
|---|---|---|---|---|---|---|
| **Fold 1** | Record 106 | Record 119 | 50 `N` : 50 `V` ($n=100$) | 50 `N` : 50 `V` ($n=100$) | Train: 24 F; Val: 51 F | Inderal vs Pronestyl |
| **Fold 2** | Record 119 | Record 106 | 50 `N` : 50 `V` ($n=100$) | 50 `N` : 50 `V` ($n=100$) | Train: 51 F; Val: 24 F | Pronestyl vs Inderal |

### Critical Scientific Limitations of $N=2$ Training Subjects
1. **Small Group Sample Size ($K=2$):** Two folds cannot approximate an empirical sampling distribution or compute standard errors for population performance.
2. **Extreme Single-Patient Domain Shift:** A model trained exclusively on Record 106 has seen only multiform PVCs in a young patient on a beta-blocker (Inderal). When evaluated on Record 119 (uniform PVCs, older patient on Pronestyl), the morphological shift is substantial.
3. **High Validation Variance:** Model selection based purely on LORO across two subjects is prone to extreme sensitivity.
4. **Test Set Isolation:** Test records (`200` and `208`) remain completely untouched and are strictly forbidden from participating in cross-validation, model selection, or feature ranking.

---

## 3. Quantum Scaler Audit & Clipping Loss Quantification (Task 2)

The `QuantumFeatureScaler` in [`src/feature_scaling.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/feature_scaling.py) was audited against the 100 unseen test beats (Records 200 & 208).

### Test Feature Clipping Statistics

| Feature Name | Training Range $[x_{\min}, x_{\max}]$ | Test Points Below $x_{\min}$ | Max Magnitude Below | Test Points Above $x_{\max}$ | Max Magnitude Above | Total Clipped Points | Clipping Rate |
|---|---|---|---|---|---|---|---|
| **`pre_rr`** | $[0.4500, 1.3528]\text{ s}$ | 4 | $0.0278\text{ s}$ ($10\text{ samples}$) | 0 | $0.0000$ | 4 | $4.0\%$ |
| **`post_rr`** | $[0.4194, 1.4806]\text{ s}$ | 0 | $0.0000$ | 0 | $0.0000$ | 0 | $0.0\%$ |
| **`qrs_rms`** | $[0.3025, 1.5165]\text{ mV}$ | 0 | $0.0000$ | 1 | $0.0641\text{ mV}$ | 1 | $1.0\%$ |
| **`qrs_duration`** | $[0.0306, 0.0944]\text{ s}$ | 2 | $0.0028\text{ s}$ ($1\text{ sample}$) | 1 | $0.0028\text{ s}$ ($1\text{ sample}$) | 3 | $3.0\%$ |
| **`p2p_amplitude`**| $[0.8800, 4.6000]\text{ mV}$ | 0 | $0.0000$ | 0 | $0.0000$ | 0 | $0.0\%$ |
| **`spectral_ratio`**| $[0.0112, 0.4452]$ | 5 | $0.0040$ | 1 | $0.0012$ | 6 | $6.0\%$ |
| **TOTAL** | *6 Feature Dimensions* | **11** | — | **3** | — | **14 / 600** | **2.33%** |

```
Test Clipping Events: 14 out of 600 total scalar evaluations (2.33%)
├── Clipped at Lower Bound (0 rad): 11 events (4 pre_rr, 2 qrs_duration, 5 spectral_ratio)
└── Clipped at Upper Bound (π rad):  3 events (1 qrs_rms, 1 qrs_duration, 1 spectral_ratio)
```

> [!CAUTION]
> **Refutation of Zero Information Loss:**  
> Previous assumptions that clipping produces zero information loss are mathematically invalid. When test values are clamped to $0$ or $\pi$, fine physiological differences in the extreme tails are collapsed onto identical quantum states $|0\rangle$ or $|1\rangle$, causing boundary gate saturation. This loss is documented in [`results/feature_audit.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/feature_audit.json).

---

## 4. QRS RMS Audit: Impact of Baseline Wander (Task 3)

The core QRS window was audited across $[-25, +25]\text{ samples}$ ($\approx 141.7\text{ ms}$ at $360\text{ Hz}$) centered at sample 144.

### Mathematical Formulation
$$\text{RMS}_{\text{raw}} = \sqrt{\frac{1}{N} \sum_{k=1}^N s[k]^2} = \sqrt{\frac{1}{N} \sum_{k=1}^N (s_{\text{true}}[k] + V_{\text{DC}})^2} = \sqrt{\text{RMS}_{\text{true}}^2 + V_{\text{DC}}^2 + 2 V_{\text{DC}} \overline{s_{\text{true}}}}$$

Where $V_{\text{DC}}$ is respiration-induced baseline wander and electrode offset.

### Comparative Distribution Metrics

| Metric | Raw Uncorrected RMS | Baseline-Corrected RMS (Median Subtracted) | Measured Baseline Offset ($V_{\text{DC}}$) |
|---|---|---|---|
| **Normal Beats (`N`)** | $0.693 \pm 0.238\text{ mV}$ | $0.672 \pm 0.178\text{ mV}$ | $-0.477 \pm 0.398\text{ mV}$ (range: $-1.23$ to $+1.43$) |
| **VEB Beats (`V`)** | $0.985 \pm 0.291\text{ mV}$ | $0.810 \pm 0.271\text{ mV}$ | $+0.381 \pm 0.597\text{ mV}$ (range: $-0.92$ to $+1.53$) |

* **Scientific Finding:** Uncorrected RMS overestimates true depolarization energy because $V_{\text{DC}}^2$ inflates the integral. In normal beats, baseline wander contributes up to $0.021\text{ mV}$ spurious energy, and in VEBs, up to $0.175\text{ mV}$.
* **Methodological Decision:** Both formulations are documented. Baseline-corrected RMS isolates true biophysical power, whereas raw RMS remains sensitive to patient-level lead bias.

---

## 5. QRS Duration Audit & Morphological Boundaries (Task 4)

The $20\%$ relative amplitude envelope algorithm was audited in the search region $[-36, +36]\text{ samples}$ ($\pm 100\text{ ms}$ around R-peak):
1. **Search Window Clamping:** $0\text{ beats}$ hit the left boundary ($-100\text{ ms}$) and $0\text{ beats}$ hit the right boundary ($+100\text{ ms}$). All onsets and offsets converged within the $200\text{ ms}$ window.
2. **R-Peak Annotation Alignment:** In **$24\text{ beats}$ ($8.0\%$)**, the annotated R-peak differed by $>3\text{ samples}$ ($>8.3\text{ ms}$) from the local envelope maximum. This occurs in wide, notched, or biphasic PVC complexes where an S-wave or secondary R'-wave exceeds the initial deflection.
3. **Formal Specification:** This feature is formally designated **Estimated QRS Duration ($w_{\text{QRS}}^{\text{est}}$)** because single-lead amplitude thresholding cannot replicate multi-lead cardiologist consensus calipers.

---

## 6. Spectral Estimation Audit: Leakage and Resolution (Task 5)

The spectral band power ratio ($P_{10\text{--}25\text{ Hz}} / P_{0.5\text{--}40\text{ Hz}}$) was compared across spectral estimators:

| Property | Rectangular Zero-Padded FFT ($n=720$) | Detrended & Hann-Windowed Periodogram ($n=360$) | Physical Significance |
|---|---|---|---|
| **True Frequency Resolution** | $\Delta f_{\text{Rayleigh}} = 1.0\text{ Hz}$ | $\Delta f_{\text{Rayleigh}} = 1.0\text{ Hz}$ | Resolution is set by $T = 1.0\text{ s}$ ($1/T = 1.0\text{ Hz}$). Zero-padding only interpolates samples; it does **not** increase physical resolving power. |
| **Sidelobe Suppression** | $-13\text{ dB}$ ($1/f$ decay) | $-31\text{ dB}$ ($1/f^3$ decay) | Rectangular windowing produces severe sidelobe leakage. |
| **DC/Drift Impact** | DC leaks into $0.5\text{--}40\text{ Hz}$ | Linear detrend eliminates DC drift | Low-frequency baseline drift artificially inflates the denominator in rectangular FFT. |
| **Normal Beat Ratio** | $0.209 \pm 0.119$ | $0.401 \pm 0.064$ | Hann windowing sharpens QRS peak and reduces variance. |
| **VEB Ratio** | $0.045 \pm 0.049$ | $0.063 \pm 0.079$ | PVC power remains low due to broadband low-frequency shift. |
| **Method Correlation** | \multicolumn{2}{c|}{$r = 0.7891$ (Strong agreement)} | Both capture the diagnostic spectral shift. |

---

## 7. Real-Time Operational Latency Constraint (Task 6)

> [!IMPORTANT]
> **Operational Mode: Retrospective Beat Classifier**  
> Feature 2 (Post-RR interval, $\Delta t_{\text{post}}$) requires knowledge of the subsequent R-peak ($R_{i+1}$). At the exact timestamp of the current heartbeat ($t = R_i$), the classifier **cannot render an instantaneous classification**.

* **Mean Latency for Normal Beats:** $0.746\text{ s}$ ($\sim 750\text{ ms}$).
* **Mean Latency for VEB Beats:** $1.052\text{ s}$ ($\sim 1,050\text{ ms}$, due to compensatory pauses).
* **Maximum Observed Latency:** $1.481\text{ s}$.
* **Clinical Utility:** The classifier is clinically suited for **ambulatory Holter monitoring, retrospective telemetry auditing, and batch arrhythmia annotation**, but cannot be deployed for instantaneous real-time defibrillator triggers without replacing Post-RR with a causal past-history interval. Post-RR is retained per protocol.

---

## 8. Comparative Visual Diagnostics

Figure [`figures/feature_method_comparison.png`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/figures/feature_method_comparison.png) compiles diagnostic comparisons:
* **Panel A:** Boxplot comparison of Raw vs. Baseline-Corrected QRS RMS by class.
* **Panel B:** Histogram of estimated QRS duration distributions against the $\pm 100\text{ ms}$ search limit.
* **Panel C:** Boxplot comparison of Rectangular FFT vs. Detrended Hann Periodogram.
* **Panel D:** Bar chart quantifying test set scaler clipping counts and magnitudes across all six features.

---

## 9. Comprehensive Test Suite Summary

Automated testing across the repository confirmed all 28 tests passing ($100\%$):

```
tests/test_dataset_validation.py .....                                   [ 17%]
tests/test_ecg_pipeline.py ......                                        [ 39%]
tests/test_feature_audit.py .......                                      [ 64%]
tests/test_feature_extraction.py .....                                   [ 82%]
tests/test_feature_scaling.py .....                                      [100%]
============================= 28 passed in 1.26s ==============================
```

### New Audit Unit Tests ([`tests/test_feature_audit.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests/test_feature_audit.py)):
1. `test_patient_level_fold_isolation`: Enforces zero subject overlap across LORO folds and verifies 50:50 class balance.
2. `test_training_only_scaler_fitting`: Verifies that scaler parameters are immutable to test set presence.
3. `test_test_out_of_range_feature_handling`: Verifies clipping detection and confirms unclipped test features exceed bounds.
4. `test_baseline_corrected_rms`: Confirms DC offset immunity of baseline-corrected RMS compared to raw RMS.
5. `test_qrs_duration_boundary_conditions`: Asserts stability on flatlines, inverted peaks, and notched waveforms.
6. `test_spectral_estimator_stability`: Verifies sinc leakage detection, zero-division safety, and pure-tone response.
7. `test_reproducibility`: Confirms deterministic execution across pipeline runs.

---

## 10. Audit Conclusions & Recommendations for Milestone 4

1. **Model Selection Strategy:** Do not use naive 5-fold CV as proof of generalizability. Use 5-fold CV internally on the 200 training samples solely for hyperparameter sweeps ($C$, learning rate), but report LORO scores across Subjects 207 and 218 as an indicator of inter-patient stability before final evaluation on Subjects 200 and 208.
2. **Preserve Shared Pipeline:** Both the classical Logistic Regression baseline and the Variational Quantum Classifier (VQC) must intake the identical training and testing feature matrices with identical $[0, \pi]$ normalizations.
3. **Execution Gate:** No classifiers or quantum circuits have been implemented. Main notebook [`main.ipynb`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/main.ipynb) remains untouched. Staged and ready for Milestone 4.
