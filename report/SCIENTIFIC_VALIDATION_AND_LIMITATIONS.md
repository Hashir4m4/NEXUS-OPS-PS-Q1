# NEXUS-OPS | PS-Q1 Biomedical Signal Classifier
# Scientific Validation, Experimental Rigor & Clinical Limitations Dossier

**Project:** NEXUS-OPS — Project Q
**Challenge:** Problem Statement PS-Q1 — Biomedical Signal Classification
**Competition:** IBM Quantum Qiskit Fall Fest 2026 (SRM University-AP)
**Auditor Roles:** Biomedical Signal-Processing Researcher, QML Scientist, Scientific Reproducibility Auditor
**Primary Artifacts:** `src/dataset_builder.py`, `src/feature_extraction.py`, `src/vqc_circuit.py`, `src/vqc_training.py`, `results/vqc_heldout_evaluation.json`, `results/classical_baseline.json`

---

## 1. Clinical Context & Benchmark Motivation

Cardiovascular disease remains the leading cause of global mortality. Ventricular Ectopic Beats (VEBs / Premature Ventricular Contractions) originate from ectopic pacemaker sites in the ventricular myocardium rather than the sinoatrial node.

In automated ECG monitoring systems, missing a ventricular ectopic event carries far greater clinical risk than a false alarm. Consequently, in clinical screening benchmarks, **Sensitivity (Recall on VEBs)** is prioritized to minimize false negatives ($\text{FN} = 0$).

NEXUS-OPS designed and evaluated a 6-qubit Variational Quantum Classifier (VQC) to address binary discrimination between:
- **Class `N` (Label 0):** Normal heartbeats.
- **Class `V` (Label 1):** Ventricular Ectopic Beats (VEBs / PVCs).

---

## 2. Dataset Curation, Provenance & Leakage Controls

### 2.1 PhysioNet MIT-BIH Arrhythmia Database
- **Standard Reference:** Moody GB, Mark RG. *The impact of the MIT-BIH Arrhythmia Database.* IEEE Eng in Med and Biol 20(3):45-50 (May-June 2001).
- **Signal Parameters:** Continuous ambulatory ECG recordings, modified limb Lead II (MLII), digitized at a sampling frequency $f_s = 360\text{ Hz}$ with 11-bit resolution over a $\pm 5\text{ mV}$ dynamic range.
- **Data Provenance Disclosure:** Datasets were independently downloaded and curated by the NEXUS-OPS team from PhysioNet using official WFDB libraries (`src/acquire_and_inspect_mitbih.py` and `src/dataset_builder.py`). No pre-packaged dataset was provided by organizers.

### 2.2 Record-Level Cohort Partitioning (LORO Protocol A)
A widespread methodological failure in published ECG machine learning papers is random beat-level cross-validation, where heartbeats from the same recording appear in both training and test sets. Because intra-record morphological correlation is extraordinarily high, random partitioning yields inflated accuracy that collapses on unseen records.

To enforce absolute external validity, NEXUS-OPS implemented strict record-level separation between training and held-out test records:

| Cohort Partition | Record IDs | Sample Size | Class Balance | Methodological Function |
|:---|:---:|:---:|:---:|:---|
| **Development Cohort** | Records `106` & `119` | $N = 200$ beats | 100 Normal, 100 VEB | Feature scaling and LORO cross-validation model selection |
| **Held-Out Test Cohort** | Records `200` & `208` | $N = 100$ beats | 50 Normal, 50 VEB | **Quarantined:** Evaluated once under frozen model parameters |

- **Zero Inter-Record Leakage:** Record-level separation between training and held-out test records guarantees that no beats or records cross the partition boundary. Patient identities are not inferred from record numbers.

### 2.3 Strict Annotation Verification (Class `N` Definition)
In MIT-BIH PhysioNet standard annotations, symbol `'N'` denotes Normal beats, while `'L'`, `'R'`, and `'B'` denote bundle branch blocks. In `src/dataset_builder.py` (lines 8–9, 97):
```python
LABEL_MAPPING = {"N": 0, "V": 1}
if symbol not in LABEL_MAPPING:
    excluded_segments.append(...)
```
Because the extraction pipeline explicitly filtered strictly for `symbol == 'N'`, **there are exactly zero bundle branch block beats in the dataset**. All earlier draft descriptions claiming "Normal / bundle branch block beats" have been formally corrected to **Normal beats**.

---

## 3. Signal Preprocessing & Feature Engineering

### 3.1 Preprocessing Pipeline
Raw ECG signals undergo two-stage filtering (`src/signal_preprocessing.py`):
1. **Baseline Wander Removal:** Two consecutive median filters with window lengths of $200\text{ ms}$ (72 samples) and $600\text{ ms}$ (216 samples) extract the low-frequency baseline drift, which is subtracted from the raw signal.
2. **Bandpass Filtering:** 4th-order Butterworth bandpass filter ($0.5\text{--}40\text{ Hz}$) eliminates high-frequency electromyographic (EMG) noise and powerline interference ($50/60\text{ Hz}$).
3. **Beat Windowing:** Exactly 360 samples ($1.0\text{ s}$) centered on the annotated R-peak: 144 samples ($400\text{ ms}$) pre-R, and 216 samples ($600\text{ ms}$) post-R.

### 3.2 Six Clinically Grounded Physiological Features
In `src/feature_extraction.py`, exactly 6 numerical features are extracted per segmented beat:

| Feature Name | Physical Units | Mathematical Definition | Physiological Justification |
|:---|:---:|:---|:---|
| **`pre_rr`** | Seconds ($s$) | $t_{R_i} - t_{R_{i-1}}$ (from continuous `.atr` stream) | Primary prematurity indicator: VEBs originate prematurely before the normal sinus beat. |
| **`post_rr`** | Seconds ($s$) | $t_{R_{i+1}} - t_{R_i}$ (from continuous `.atr` stream) | Compensatory pause: VEBs typically fail to reset the sinoatrial node, producing a prolonged post-ectopic interval. |
| **`qrs_rms`** | Millivolts ($mV$) | $\sqrt{\frac{1}{51} \sum_{k=-25}^{+25} s[R_i + k]^2}$ | RMS amplitude across a $140\text{ ms}$ window centered on R-peak; quantifies concentrated depolarization energy. |
| **`qrs_duration`**| Seconds ($s$) | Width at 20% envelope threshold in $\pm 36$ samples | Conduction delay: VEBs propagate slowly through ventricular myocardium rather than the fast His-Purkinje system. |
| **`p2p_amplitude`**| Millivolts ($mV$) | $\max(s) - \min(s)$ across the 360-sample beat window | Global voltage excursion: ectopic depolarization often causes exaggerated peak-to-peak voltages. |
| **`spectral_ratio`**| Dimensionless | $P_{[10, 25]\text{ Hz}} / P_{[0.5, 40]\text{ Hz}}$ (FFT Periodogram) | Frequency concentration: normal QRS energy is sharply concentrated in 10–25 Hz; broadened VEB complexes shift energy lower. |

### 3.3 Scaler Quarantine & Value Clamping
Features are mapped linearly into quantum rotation angles $[0, \pi]$ via `QuantumFeatureScaler` (`src/feature_scaling.py`):
$$\tilde{x}_j = \pi \cdot \text{clip}\left(\frac{x_j - x_{j,\min}^{\text{dev}}}{x_{j,\max}^{\text{dev}} - x_{j,\min}^{\text{dev}}}, 0.0, 1.0\right)$$
- **Zero Distribution Lookahead:** The minimum and maximum parameters are fitted **strictly on the $N=200$ development cohort** and frozen. When applied to the test cohort, out-of-range values are clamped to $[0, \pi]$ without refitting.

---

## 4. Quantum Architecture & Classical Optimization

### 4.1 Variational Circuit Formulation
- **Qubits:** 6 logical qubits ($q_0 \leftrightarrow \text{pre\_rr}, q_1 \leftrightarrow \text{post\_rr}, q_2 \leftrightarrow \text{qrs\_rms}, q_3 \leftrightarrow \text{qrs\_duration}, q_4 \leftrightarrow \text{p2p\_amplitude}, q_5 \leftrightarrow \text{spectral\_ratio}$).
- **State Preparation:** First-order $R_y$ rotation encoding:
  $$U_{\Phi}(\mathbf{x}) = \bigotimes_{j=0}^5 R_y(\tilde{x}_j)$$
- **Variational Ansatz:** `RealAmplitudes` with 1 repetition and linear nearest-neighbor CX entanglement:
  $$U_A(\boldsymbol{\theta}) = \left(\bigotimes_{j=0}^5 R_y(\theta_{j+6})\right) \left(\prod_{j=0}^4 \text{CX}_{j, j+1}\right) \left(\bigotimes_{j=0}^5 R_y(\theta_j)\right)$$
- **Parameters:** Exactly 12 trainable variational parameters ($\boldsymbol{\theta} \in \mathbb{R}^{12}$). Total circuit parameters: 18 (6 encoding + 12 variational).
- **Observable:** Equal-weight Pauli-$Z$ ensemble:
  $$\hat{O} = \frac{1}{6} \sum_{j=0}^5 Z_j$$
- **Probability Conversion:** Monotonic affine conversion mapping expectation value $\langle\hat{O}\rangle \in [-1, +1]$ to probability:
  $$P(\text{VEB}) = \frac{\langle\hat{O}\rangle + 1}{2} \in [0.0, 1.0]$$
- **Decision Rule:** Binary threshold $\tau = 0.5$ ($\langle\hat{O}\rangle \ge 0 \implies \text{VEB}$, $\langle\hat{O}\rangle < 0 \implies \text{Normal}$).

### 4.2 Optimization & Checkpoint Selection
- **Optimizer:** Verified as **SciPy COBYLA** (`method="COBYLA"`) in `src/vqc_training.py` line 413.
- **Loss Function:** Mean Squared Error (MSE) loss against labels $y \in \{0, 1\}$:
  $$\mathcal{L}(\boldsymbol{\theta}) = \frac{1}{M} \sum_{i=1}^M \left(P(\text{VEB} \mid \mathbf{x}_i, \boldsymbol{\theta}) - y_i\right)^2$$
- **Frozen Checkpoint:** Evaluated across 10 multi-seed training runs in LORO cross-validation. Candidate **`fold_1_seed_303`** (trained on Record 106, validated on Record 119) achieved 100% validation accuracy and was frozen in `results/vqc_model_selection.json`:
  $$\boldsymbol{\theta}^* = [0.4889, -1.2636, -0.4962, -0.9823, -0.8178, -0.7964, -0.3341, -0.3669, -0.8661, -1.0348, 0.5614, 0.4214]$$

---

## 5. Experimental Results & Classical Benchmark Comparison

### 5.1 Quarantined Held-Out Test Evaluation ($N = 100$)

| Performance Metric | Classical Baseline (Logistic Regression) | VQC Ideal Simulation (`StatevectorEstimator`) | VQC Full Noise Simulation (`AerSimulator` Measurements) | Status |
|:---|:---:|:---:|:---:|:---:|
| **Accuracy** | **92.00%** (92 / 100) | **76.00%** (76 / 100) | **77.00%** (77 / 100) | Verified |
| **Sensitivity (Recall on VEB)** | **100.00%** (50 / 50) | **100.00%** (50 / 50) | **100.00%** (50 / 50) | Verified |
| **Specificity (Normal Recall)** | **84.00%** (42 / 50) | **52.00%** (26 / 50) | **54.00%** (27 / 50) | Verified |
| **Precision** | **86.21%** (50 / 58) | **67.57%** (50 / 74) | **68.49%** (50 / 73) | Verified |
| **F1-Score** | **0.9259** | **0.8065** | **0.8130** | Verified |
| **ROC-AUC** | **0.9960** | **0.9988** | **0.9984** | Verified |
| **Brier / MSE Score** | **0.0547** | **0.1626** | **0.1644** | Verified |
| **Class Polarity $\Delta p$** | **+0.4429** | **+0.2317** | **+0.2246** | Verified |
| **Confusion Matrix [TN, FP, FN, TP]**| [42, 8, 0, 50] | [26, 24, 0, 50] | [27, 23, 0, 50] | Verified |

### 5.2 Methodological Comparison Disclosure
The classical $L_2$-regularized Logistic Regression baseline was trained on all $N=200$ development beats (`records 106 & 119`), achieving 92.00% test accuracy and 0.9259 F1. In contrast, the frozen 6-qubit VQC (`fold_1_seed_303`) was trained under strict Leave-One-Record-Out cross-validation on the Record 106 partition ($N=100$), achieving 76.00% ideal (0.8065 F1) and 77.00% noisy (0.8130 F1) test accuracy under 4096 measurement shots.

Both models were evaluated on the identical, unseen $N=100$ held-out test cohort (Records 200 & 208) and both achieved **100.00% empirical Sensitivity on VEB beats** (identifying all 50 class `V` beats with zero false negatives in this sample).

**Patient-Stratified Specificity Disaggregation:**
Evaluating specificities across the two held-out test patients reveals inter-subject distribution shifts:
- **Record 200 ($N=50$, 25 Normal, 25 VEB):** Specificity is **68.00%** (17 / 25) in ideal simulation and **68.00%** (17 / 25) under noisy simulation (Sensitivity: 100.0%, 25 / 25).
- **Record 208 ($N=50$, 25 Normal, 25 VEB):** Specificity is **36.00%** (9 / 25) in ideal simulation and **40.00%** (10 / 25) under noisy simulation (Sensitivity: 100.0%, 25 / 25).
Across both test patients combined, the overall specificity is **52.00%** (26 / 50) ideal and **54.00%** (27 / 50) noisy.

---

## 6. Scientific Limitations & Ethical Disclosures

In accordance with strict scientific integrity guidelines, NEXUS-OPS explicitly establishes five critical boundaries:

1. **Retrospective / Offline Scope Disclosure:**
   The `post_rr` feature measures the interval to the subsequent R-peak ($t_{R_{i+1}} - t_{R_i}$). Consequently, computing this feature requires observing the succeeding beat, introducing a one-beat latency ($\sim 0.6\text{--}1.0\text{ s}$). The classifier is therefore designed for retrospective Holter tape scanning, automated batch triage, or delayed telemetry review—**it is not a zero-lookahead real-time detector**.
2. **Empirical Sensitivity Limitation:**
   The 100.00% sensitivity reported on the held-out test cohort represents an empirical result on a fixed sample of 50 VEB beats across two patient recordings. **It does not constitute an unconstrained clinical guarantee, diagnostic certification, or medical device clearance across broader patient populations**.
3. **Window Overlap Disclosure:**
   ECG segments are extracted using 360-sample ($1.0\text{ s}$) windows centered on annotated R-peaks. For heart rates exceeding $60\text{ bpm}$ ($R\text{-}R < 1.0\text{ s}$), adjacent temporal windows exhibit partial sample overlap, although each window represents an independent annotated cardiac event.
4. **Simulation Boundary:**
   All quantum hardware benchmarks and noise models represent classical simulation on Qiskit Aer (`StatevectorEstimator` and `AerSimulator`). **Zero physical IBM QPU hardware execution is claimed**.
5. **No Quantum Supremacy Claims:**
   We do not claim quantum supremacy or computational advantage over classical algorithms on this dataset. The classical Logistic Regression model achieves higher overall accuracy (92% vs 76%), reflecting the early developmental stage of NISQ QML classifiers. The value of this project lies in proving high-fidelity state encoding, noise resilience, and native compilation compatibility on constrained quantum processors.
