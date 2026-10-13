# Milestone 2B: ECG Dataset Construction & Validation Report
**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Status:** Completed & Validated  
**Date:** October 12, 2026  
**Lead Discipline:** Quantum Machine Learning & Biomedical Biosignal Processing  

---

## 1. Executive Summary

Milestone 2B establishes the standardized, leakage-free biomedical benchmark dataset for the NEXUS-OPS PS-Q1 quantum ECG classifier. From the PhysioNet MIT-BIH Arrhythmia Database, a cohort of **300 balanced ECG beat segments** (150 Normal `N`, 150 Ventricular Ectopic Beat `V`) was extracted across four distinct patient recordings (`106`, `119`, `200`, `208`) under fixed $360\text{-sample}$ ($1.0\text{ s}$) windows.

The dataset strictly enforces **patient-level isolation** between the training partition ($200\text{ segments}$ from Patients 106 & 119) and testing partition ($100\text{ segments}$ from Patients 200 & 208). Automated verification suites confirmed zero patient overlap, exact class balance, zero boundary breaches, zero non-finite values, and $100\%$ deterministic reproducibility under random seed `42`.

---

## 2. Metadata Audit & Patient Provenance

To guarantee data integrity and prevent fabrication, all metadata was audited directly against the raw `.hea` (Header) files downloaded from PhysioNet.

### Record Header Audit Table

| Record ID | Sampling Rate ($f_s$) | Lead 0 (Selected) | Lead 1 | Total Samples | Header Subject Metadata Line | Verified Clinical Demographics | Prescribed Medications | Clinical Rhythm Remarks |
|---|---|---|---|---|---|---|---|---|
| **`106`** | $360\text{ Hz}$ | `MLII` | `V1` | 650,000 ($1,805.6\text{ s}$) | `# 24 F 1581 654 x1` | Age 24, Female | Inderal | Multiform PVCs |
| **`119`** | $360\text{ Hz}$ | `MLII` | `V1` | 650,000 ($1,805.6\text{ s}$) | `# 51 F 1129 654 x2` | Age 51, Female | Pronestyl | Uniform PVCs |
| **`200`** | $360\text{ Hz}$ | `MLII` | `V1` | 650,000 ($1,805.6\text{ s}$) | `# 64 M 1953 3655 x1` | Age 64, Male | Digoxin, Quinidine | Multiform PVCs; high-frequency bursts |
| **`208`** | $360\text{ Hz}$ | `MLII` | `V1` | 650,000 ($1,805.6\text{ s}$) | `# 23 F 2546 N/A x1` | Age 23, Female | None | Uniform PVCs; bigeminal couplets & triplets |

> [!IMPORTANT]
> **Source Verification of Subject Demographics:**  
> Demographic identifiers were extracted verbatim from comments embedded in the `.hea` files (Line 4). Note that while secondary literature sometimes erroneously cites Record 208 as 63/F, the authoritative PhysioNet header text explicitly documents `# 23 F`. All four records represent distinct individual subjects, proving zero intra-patient leakage across records.

---

## 3. Dataset Construction & Sampling Strategy

### Window Definition
* **Center Point:** Cardiologist-annotated R-peak sample index ($R_i$).
* **Temporal Span:** $144\text{ samples}$ pre-R-peak ($400\text{ ms}$) + $216\text{ samples}$ post-R-peak ($600\text{ ms}$) = **$360\text{ samples}$ total ($1.0\text{ second}$)**.
* **Lead Selection:** Modified Limb Lead II (`MLII`). MLII provides optimal alignment with the primary cardiac electrical axis, accentuating the morphological widening and amplitude anomalies characteristic of ventricular ectopic beats (`V`).

### Quota Allocation (Phase 1 Design)

$$\begin{aligned}
\text{Training Set (Records 106 \& 119)}&: 100\text{ Normal } (50 + 50) + 100\text{ VEB } (50 + 50) = 200\text{ samples} \\
\text{Testing Set (Records 200 \& 208)}&: 50\text{ Normal } (25 + 25) + 50\text{ VEB } (25 + 25) = 100\text{ samples} \\
\mathbf{Total\ Dataset}&: \mathbf{150\ Normal } + \mathbf{150\ VEB } = \mathbf{300\ samples}
\end{aligned}$$

### Deterministic Subsampling
Selection was executed via NumPy's pseudo-random generator with `RANDOM_SEED = 42`. Subsampling was performed without replacement from the pool of valid, boundary-compliant beats within each record.

---

## 4. Signal Quality, Filtering Decisions & Boundary Compliance

### Signal Integrity & Missing Values
* **Zero Missing Values:** Programmatic analysis confirmed $0$ missing, $0\text{ NaN}$, and $0\text{ Infinite}$ values across all 300 extracted segments ($108,000$ discrete scalar signal values).
* **Calibrated Units:** Signals are stored in physical millivolts ($\text{mV}$), converted directly from raw 11-bit ADC format 212 samples using the calibrated gain ($200\text{ ADC units/mV}$) and baseline offset ($1024$) specified in the header.

### Filtering Policy
* **No Black-Box or Non-Causal Filtering:** Raw calibrated physical signals are preserved in their authentic clinical state without arbitrary frequency truncation, moving-average smoothing, or manual cherry-picking of "clean-looking" beats.
* **Reproducible Preprocessing:** All subsequent feature extraction and baseline drift correction will be strictly deterministic and explicitly documented in Milestone 3.

### Exclusions & Rejections Tracking
A total of **867 annotations** were excluded across the four recordings during segment extraction. Every exclusion was classified and logged:

| Exclusion Reason | Count | Clinical & Technical Rationale |
|---|---|---|
| **Non-target symbol `F`** | 375 | Fusion of ventricular and normal beat (excluded to maintain unambiguous binary `N` vs `V` targets). |
| **Non-target symbol `+`** | 345 | Rhythm change indicator (non-beat annotation). |
| **Non-target symbol `~`** | 101 | Signal artifact / electrode noise comment. |
| **Non-target symbol `A`** | 30 | Atrial premature contraction (supraventricular ectopic, excluded from VEB scope). |
| **Non-target symbol `\|`** | 8 | Isolated pacemaker rhythm mark. |
| **Boundary Violation** | 4 | Beat located within $144\text{ samples}$ of recording onset ($t < 400\text{ ms}$). |
| **Non-target symbol `S`** | 2 | Supraventricular premature beat. |
| **Non-target symbol `Q`** | 2 | Unclassifiable beat. |

### Adjacent Beat Window Overlap Analysis
* **Physiological Context:** At typical resting heart rates ($60\text{--}100\text{ bpm}$), the physiological RR interval spans $0.6\text{--}1.0\text{ s}$ ($216\text{--}360\text{ samples}$). Thus, consecutive beats naturally overlap in the peripheral P-wave / T-wave zones when a $1.0\text{ s}$ window is applied.
* **Observed Sampled Overlap:** Because the 300 segments were sparsely sampled across $>9,100$ total beats, **only 9 pairs of adjacent segments** exhibit temporal overlap in the selected dataset. Since feature extraction is performed independently per segment (centered on the segment's dedicated R-peak), this physiological overlap introduces zero distortion or leakage.

---

## 5. Partitioning & Data Leakage Prevention

> [!CAUTION]
> **Zero Inter-Patient Contamination:**  
> Training and testing partitions were segregated at the **subject/record level**. Heartbeats from Subject 207 (Rec 106) and Subject 218 (Rec 119) appear exclusively in `train.csv`. Heartbeats from Subject 219 (Rec 200) and Subject 220 (Rec 208) appear exclusively in `test.csv`.

* **Feature Scaler Safeguard:** No feature scaling was performed across the complete dataset. In Milestone 3, all normalization scalers ($[0, \pi]$) will be fitted **exclusively on the 200 training samples** and applied transitively to the test samples.

---

## 6. Generated Project Artifacts

```
PS-Q1-Biomedical-Classifier/
├── src/
│   ├── dataset_builder.py          # Deterministic 300-beat dataset builder
│   └── dataset_validation.py       # Automated verification engine
├── data/
│   └── processed/
│       ├── ecg_segments.csv        # Master dataset (300 rows x 371 columns)
│       ├── train.csv               # Training partition (200 rows x 371 columns)
│       └── test.csv                # Testing partition (100 rows x 371 columns)
├── results/
│   └── dataset_validation.json     # Complete structured verification telemetry
├── report/
│   └── dataset_preparation.md      # Comprehensive technical documentation
└── tests/
    └── test_dataset_validation.py  # Pytest test suite (5 passed, 100%)
```

---

## 7. Verification Test Suite Results

Automated execution via `pytest tests/test_dataset_validation.py` and `src/dataset_validation.py`:

```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Data\Projects\NEXUS-OPS\NEXUS-OPS\PS-Q1-Biomedical-Classifier
collected 5 items

tests/test_dataset_validation.py .....                                   [100%]
============================== 5 passed in 1.51s ==============================
```

| Check Item | Specification | Observed Status | Verdict |
|---|---|---|---|
| **Total Segment Count** | Exactly 300 | 300 | **PASS** |
| **Train/Test Partition Sizes** | 200 Train / 100 Test | 200 Train / 100 Test | **PASS** |
| **Class Balance (Overall)** | 150 `N` : 150 `V` (1:1) | 150 `N` : 150 `V` | **PASS** |
| **Class Balance (Train)** | 100 `N` : 100 `V` (1:1) | 100 `N` : 100 `V` | **PASS** |
| **Class Balance (Test)** | 50 `N` : 50 `V` (1:1) | 50 `N` : 50 `V` | **PASS** |
| **Inter-Patient Isolation** | $\text{Train} \cap \text{Test} = \emptyset$ | $\{106, 119\} \cap \{200, 208\} = \emptyset$ | **PASS** |
| **Signal Dimension** | 360 samples ($1.0\text{ s}$) | 360 columns (`s_0` to `s_359`) | **PASS** |
| **Signal Finiteness** | No NaN, Inf, or Null | $0\text{ NaN}$, $0\text{ Inf}$, $0\text{ Null}$ | **PASS** |
| **Boundary Integrity** | $0 \le \text{Start} < \text{End} \le 650,000$ | Min start: 6,328, Max end: 649,556 | **PASS** |
| **Seed Determinism** | Seed 42 exact match | Re-run produced identical CSVs | **PASS** |

---

## 8. Unresolved Items & Discussion for Team Review

1. **Demographic Clarification on Record 208:** The header file confirms `# 23 F`, while older literature reviews occasionally listed 63/F. The team will maintain the exact `.hea` provenance (`23 F`).
2. **Transition to Milestone 3 (Feature Engineering):** With 300 pristine segments secured, the next objective is designing the **4 to 8 quantum-rotational features** (e.g., QRS energy, pre/post RR intervals, frequency band ratios) scaled strictly within $[0, \pi]$ using training-only parameter fitting.
