# NEXUS-OPS | PS-Q1 Biomedical Signal Classifier
# README Scientific Accuracy & Integrity Audit Report

**Project:** NEXUS-OPS — Project Q  
**Challenge:** PS-Q1 Biomedical Signal Classifier  
**Hackathon:** IBM Quantum Qiskit Fall Fest 2026  
**Audit Date:** 13 October 2026  
**Auditor Role:** Senior Quantum Machine Learning Research Engineer & Scientific Integrity Auditor  
**Repository:** `https://github.com/Hashir4m4/NEXUS-OPS-PS-Q1`  

---

## 1. Executive Audit Summary

Following the initial Phase 1 submission packaging, an independent scientific accuracy audit was performed on `README.md`, `demo.py`, and supporting packaging artifacts. 

The audit focused specifically on eliminating documentation discrepancies, correcting biomedical feature definitions, calibrating clinical claims to match empirical evidence, and cross-checking every quantitative metric against raw experimental JSON outputs and passing test contracts.

### Audit Verdict: **PASSED WITH CORRECTIONS APPLIED**
All identified discrepancies in feature nomenclature, physical units, clinical over-claims, and documentation boundaries have been corrected directly in `README.md` and `demo.py`. All 116 automated tests remain passing (100% green), and no unauthorized Git operations (`git add`, `git commit`, `git push`) or Phase 7 work were initiated.

---

## 2. Feature Definition Verification & Reconciliation

### 2.1 Source-of-Truth Inspection
The codebase was inspected across all layers of the scientific pipeline:
- `src/feature_extraction.py` (Lines 8–13, 38–54)
- `data/processed/features_train.csv` & `features_test.csv` (Header columns)
- `src/vqc_preprocessing.py` (Lines 36, 48, 57–60)
- `src/vqc_circuit.py` (Lines 8–10, 98–140)

### 2.2 Reconciled 6-Feature Specification
The actual six features used throughout data preprocessing, model training, held-out evaluation, and quantum state encoding are:

| Feature Name | Physical Unit | Domain Range | Signal Processing Definition | Quantum Register |
|:---|:---:|:---:|:---|:---:|
| **`pre_rr`** | seconds | $[0.2, 2.5]$ | Preceding R-R interval from prior annotated R-peak ($t_{R_i} - t_{R_{i-1}}$) measured from continuous annotation stream (`.atr`). Key marker for prematurity. | Qubit $q_0$ ($x_0$) |
| **`post_rr`** | seconds | $[0.2, 2.5]$ | Succeeding R-R interval to subsequent annotated R-peak ($t_{R_{i+1}} - t_{R_i}$) measured from continuous annotation stream. Captures compensatory pause. | Qubit $q_1$ ($x_1$) |
| **`qrs_rms`** | $mV$ | $[0.0, 5.0]$ | Root Mean Square signal amplitude in a $[-25, +25]$ sample window ($\pm 69.4\text{ ms}$, $\sim 140\text{ ms}$ total span) centered on R-peak (sample 144). Captures ventricular depolarization energy. | Qubit $q_2$ ($x_2$) |
| **`qrs_duration`** | seconds | $[0.02, 0.20]$ | QRS complex temporal width estimated by 20% envelope threshold within $\pm 36$-sample search window ($\pm 100\text{ ms}$). Reflects ventricular conduction delay. | Qubit $q_3$ ($x_3$) |
| **`p2p_amplitude`** | $mV$ | $[0.1, 8.0]$ | Peak-to-peak amplitude excursion ($\max(s) - \min(s)$) across full 360-sample ($1.0\text{ s}$) segmented beat window. | Qubit $q_4$ ($x_4$) |
| **`spectral_ratio`** | dimensionless | $[0.0, 1.0]$ | Power spectral ratio $P([10, 25]\text{ Hz}) / P([0.5, 40]\text{ Hz})$ computed via FFT periodogram. Distinguishes narrow normal complexes from broad ectopic waves. | Qubit $q_5$ ($x_5$) |

### 2.3 Hallucinated Features Caught and Corrected
The audit identified that the preliminary README draft erroneously listed generic literature features that do not exist in this project's implementation:
- **Discrepancy 1:** Listed "$R_{\text{peak}}$ Amplitude ($mV$)" $\to$ **Corrected** to `p2p_amplitude` ($mV$) and `qrs_rms` ($mV$).
- **Discrepancy 2:** Listed "$T_{\text{wave}}$ Amplitude ($mV$)" $\to$ **Corrected**: $T$-wave amplitude was never extracted or implemented.
- **Discrepancy 3:** Listed "$P\text{-}R$ Interval ($ms$)" $\to$ **Corrected**: $P\text{-}R$ interval was never extracted; replaced with `spectral_ratio`.
- **Discrepancy 4:** Listed units in milliseconds $\to$ **Corrected**: True units in code and CSVs are seconds (`pre_rr`, `post_rr`, `qrs_duration`).
- **Discrepancy 5:** ASCII circuit diagram lacked qubit-to-feature labeling $\to$ **Corrected**: Qubit lines $q_0 \dots q_5$ now explicitly show the corresponding feature names and physical mappings.

---

## 3. Scientific Wording & Clinical Claim Calibrations

To conform strictly to scientific integrity and avoid unsupportable hype, the following language calibrations were executed across `README.md` and `demo.py`:

| Context | Previous Draft Phrasing | Calibrated Scientific Phrasing | Rationale |
|:---|:---|:---|:---|
| **Pipeline Title** | "Zero-Leakage Pipeline" | "Leakage-Controlled Evaluation Pipeline" | Prevents overclaiming total leakage absence; precisely scopes controls to patient-level separation and scaler isolation. |
| **Target Classes** | "Normal sinus rhythm vs malignant arrhythmia precursors" | "MIT-BIH annotation class `N` (Normal / bundle branch block beats) vs class `V` (Ventricular Ectopic Beats)" | MIT-BIH class `N` includes non-sinus bundle branch blocks; class `V` includes isolated benign VEBs as well as premature beats. Exact annotation taxonomy is required. |
| **Clinical Performance** | "Across all test configurations, the VQC achieved 100.00% Sensitivity ... without a single false negative." | "The frozen VQC achieved 100.00% empirical Sensitivity on the quarantined test cohort (identifying all 50 class `V` beats from Records 200 and 208, with 0 false negatives in this 100-beat sample). ... not a generalized clinical guarantee." | An empirical test result on 50 beats cannot be claimed as a clinical guarantee or medical device certification. |
| **Temporal Lookahead** | Undisclosed in Section 2 | Fully disclosed in Sections 2.4 and 8: measuring `post_rr` introduces a 1-beat retrospective latency in prospective streaming. | Full transparency regarding prospective clinical deployment constraints. |
| **Window Overlap** | Undisclosed in Section 2 | Fully disclosed in Sections 2.4 and 8: 360-sample (1.0 s) windows centered on consecutive R-peaks may share raw samples if heart rate $> 60\text{ bpm}$. | Preempts peer reviewer questions regarding adjacent sample overlap. |

---

## 4. Quantitative Metric Cross-Check

All performance, compilation, and hardware metrics reported in `README.md` were independently verified against raw experimental JSON records:

### 4.1 Quarantined Test Cohort ($N = 100$, Records 200 & 208)
Source artifacts: `results/vqc_heldout_evaluation.json`, `results/noisy_simulation_results.json`

| Metric | Source JSON Value | `README.md` Reported | Audit Status |
|:---|:---:|:---:|:---:|
| **Ideal Accuracy** | `0.76` (76/100) | 76.00% | **MATCH** |
| **Ideal Sensitivity** | `1.00` (50/50) | 100.00% | **MATCH** |
| **Ideal Specificity** | `0.52` (26/50) | 52.00% | **MATCH** |
| **Ideal Precision** | `0.6756756756756757` | 67.57% | **MATCH** |
| **Ideal F1-Score** | `0.8064516129032258` | 0.8065 | **MATCH** |
| **Ideal ROC-AUC** | `0.9988` | 0.9988 | **MATCH** |
| **Ideal MSE Loss** | `0.16263370085155973` | 0.1626 | **MATCH** |
| **Ideal Class Polarity $\Delta p$** | `+0.23171347623870325` | +0.2317 | **MATCH** |
| **Noisy Accuracy (Aer + Meas)** | `0.77` (77/100) | 77.00% | **MATCH** |
| **Noisy Sensitivity** | `1.00` (50/50) | 100.00% | **MATCH** |
| **Noisy Specificity** | `0.54` (27/50) | 54.00% | **MATCH** |
| **Noisy Precision** | `0.684931506849315` | 68.49% | **MATCH** |
| **Noisy F1-Score** | `0.8130081300813007` | 0.8130 | **MATCH** |
| **Noisy ROC-AUC** | `0.9984` | 0.9984 | **MATCH** |
| **Noisy MSE Loss** | `0.16437617093324658` | 0.1644 | **MATCH** |
| **Noisy Class Polarity $\Delta p$** | `+0.22456705729166648` | +0.2246 | **MATCH** |

### 4.2 Processor B (9-Qubit Target) Compilation Metrics
Source artifact: `results/noisy_simulation_results.json`, `tests/test_hardware_experiments.py`

| Property | Source Value | `README.md` Reported | Audit Status |
|:---|:---:|:---:|:---:|
| **Physical Qubits** | 9 | 9 | **MATCH** |
| **Transpiled Depth (Unmeasured)** | 15 | 15 | **MATCH** |
| **Transpiled Depth (Measured)** | 16 | 16 | **MATCH** |
| **2-Qubit (CX) Gates** | 5 | 5 | **MATCH** |
| **SWAP Gates** | 0 | 0 | **MATCH** |
| **Total Operations (Unmeasured)** | 65 (`rz`: 36, `sx`: 24, `cx`: 5) | 65 | **MATCH** |
| **Total Operations (Measured)** | 71 (65 gates + 6 measure) | 71 | **MATCH** |
| **Physical Layout** | `[0, 1, 2, 4, 5, 6]` | `[0, 1, 2, 4, 5, 6]` | **MATCH** |

### 4.3 Processor A (5-Qubit Target) Capacity Enforcement
Source artifact: `processors/processor_a.py`, `tests/test_processor_ab.py`

| Property | Source Value | `README.md` Reported | Audit Status |
|:---|:---:|:---:|:---:|
| **Physical Qubits** | 5 | 5 | **MATCH** |
| **VQC Circuit Width** | 6 logical qubits | 6 logical qubits | **MATCH** |
| **Transpilation Exception** | `CircuitTooWideForTarget` | `CircuitTooWideForTarget` | **MATCH** |
| **Organizer FAQ Compliance** | Section 3.1 & 13 Oct FAQ | Accurately cited & respected | **MATCH** |

---

## 5. Demonstration Script Audit (`demo.py`)

The lightweight demonstration runner `demo.py` was executed directly under Python 3.13 (`.venv`):
- **Command:** `.venv\Scripts\python demo.py`
- **Execution Time:** ~1.9 seconds
- **Memory Consumption:** Minimal (< 200 MB RSS)
- **Deterministic Output:**
  - Frozen weights `fold_1_seed_303` loaded correctly.
  - Test beat 14 (Record 200, Normal N): $\langle\hat{O}\rangle = -0.3603 \implies P(\text{VEB}) = 0.3199 \implies$ Normal (`CORRECT`).
  - Test beat 11 (Record 200, VEB V): $\langle\hat{O}\rangle = +0.4774 \implies P(\text{VEB}) = 0.7387 \implies$ VEB (`CORRECT`).
  - Processor B native transpilation confirmed: Depth 15, 5 CX, 0 SWAP, 65 ops, layout `[0, 1, 2, 4, 5, 6]`.
  - Processor A capacity boundary enforced: correctly catches `CircuitTooWideForTarget`.

---

## 6. Repository Integrity & Git Status

The workspace was inspected to ensure zero violations of user safety constraints:

```bash
git status --short
 M README.md
 M demo.py
?? report/README_SCIENTIFIC_ACCURACY_AUDIT.md
... (existing untracked files preserved)
```

- **Staged Files:** Exactly 0 (`git add` was NOT executed).
- **Commits:** 0 (`git commit` was NOT executed).
- **Remote Push:** 0 (`git push` was NOT executed).
- **Submissions:** 0 (Portal submission was NOT attempted).
- **Deletions:** 0 (No existing test, report, result, or processor files were deleted).
- **Phase 7:** Completely untouched.
- **Tests Passing:** 116 / 116 tests passing in 12.57s.

---

## 7. Final Recommendation & Owner Approval Checklist

The Phase 1 documentation and demonstration package are now scientifically rigorous, fully reproducible, and aligned with hackathon organizer guidelines and peer-review standards.

Before staging and pushing to the public GitHub repository, the repository owner should review:
- [x] Correct feature names (`pre_rr`, `post_rr`, `qrs_rms`, `qrs_duration`, `p2p_amplitude`, `spectral_ratio`) in `README.md`.
- [x] Removal of exaggerated clinical claims ("zero false negatives", "zero leakage") in favor of empirical benchmark reporting.
- [x] Clear disclosures of prospective `post_rr` latency and adjacent window overlap.
- [x] Successful local run of `python demo.py` (~2s).
- [ ] Authorization to update `.gitignore` (ignore `backup_*`, `scratch/`, `docs/challenge_materials/`).
- [ ] Authorization to stage and commit approved Phase 1 artifacts (`git add`, `git commit`).
