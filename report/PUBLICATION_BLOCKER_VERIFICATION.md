# NEXUS-OPS | PS-Q1 Biomedical Signal Classifier
# Publication Blocker Verification & Scientific Integrity Audit

**Project:** NEXUS-OPS — Project Q  
**Challenge:** PS-Q1 Biomedical Signal Classifier  
**Hackathon:** IBM Quantum Qiskit Fall Fest 2026  
**Audit Date:** 13 October 2026  
**Auditor Role:** Senior Technical Auditor & Scientific Software Architect  
**Repository:** `https://github.com/Hashir4m4/NEXUS-OPS-PS-Q1`  
**Overall Staging Status:** **`BLOCKED (ACTION REQUIRED PRIOR TO STAGING)`**  

---

## 1. Executive Summary & Verification Mandate

Following the preparation of the Final Public Repository Manifest, an independent scientific audit was executed to verify six critical publication blockers. In accordance with strict instructions, **no repository files were modified**, and no Git operations (`git add`, `git commit`, `git push`) were performed.

### Master Blocker Status Dashboard:

| # | Blocker Item | Evaluated Status | Core Finding & Required Action |
|:---:|:---|:---:|:---|
| **1** | **MIT-BIH Class `N` Description** | **`FAIL`** | Class `N` represents exclusively **Normal beats**, not "Normal / bundle branch block beats". Exact locations requiring correction identified. |
| **2** | **VQC Optimizer Verification** | **`FAIL`** | The true optimizer is **SciPy COBYLA**, not Nelder-Mead. Nelder-Mead was never invoked in `src/vqc_training.py`. |
| **3** | **Logistic Regression Metrics Reconciliation** | **`UNRESOLVED / FAIL`** | Canonical result is **92.00% accuracy** (`results/classical_baseline.json`). The 71.00% column in `README.md` has no supporting artifact and must be removed or corrected. |
| **4** | **Proposed Public Audit Documents Review** | **`FAIL`** | All 4 audit files contain copyrighted organizer quotes, Google Drive citations, or obsolete internal notes. Recommended: **EXCLUDE** from public repository. |
| **5** | **Proposed `.gitignore` Exclusions** | **`PASS`** | The proposed broad `docs/` rule is dangerous; refined to target exclusively `docs/challenge_materials/`. |
| **6** | **Comprehensive Security & Privacy Scan** | **`PASS`** | **Zero secrets, zero credentials, zero private tokens, and zero personal user paths** found in tracked or publishable files. |

**Final Recommendation:** The repository is **NOT SAFE TO STAGE** until the identified scientific discrepancies in `README.md` and the manifest exclusions are formally corrected.

---

## 2. Blocker 1: MIT-BIH Class Descriptions Verification

### 2.1 Codebase & Dataset Inspection
The dataset construction implementation and underlying PhysioNet records were inspected:
- **`src/dataset_builder.py` (Lines 8–9, 64, 97):**
  ```python
  LABEL_MAPPING = {"N": 0, "V": 1}
  # Line 97:
  if symbol not in LABEL_MAPPING:
      excluded_segments.append(...)
  ```
- **`data/processed/features_train.csv` & `features_test.csv`:**
  - Training cohort ($N=200$): Exactly 100 `'N'` beats, 100 `'V'` beats.
  - Test cohort ($N=100$): Exactly 50 `'N'` beats, 50 `'V'` beats.
- **Underlying MIT-BIH PhysioNet Records (106, 119, 200, 208):**
  - Record 106: 1507 `'N'`, 520 `'V'`, 0 `'L'`, 0 `'R'`, 0 `'B'`.
  - Record 119: 1543 `'N'`, 444 `'V'`, 0 `'L'`, 0 `'R'`, 0 `'B'`.
  - Record 200: 1743 `'N'`, 826 `'V'`, 0 `'L'`, 0 `'R'`, 0 `'B'`.
  - Record 208: 1586 `'N'`, 992 `'V'`, 0 `'L'`, 0 `'R'`, 0 `'B'`.

### 2.2 Finding & Scientific Correction
In MIT-BIH PhysioNet standard annotations, `'N'` denotes **Normal beat**, while `'L'`, `'R'`, and `'B'` denote bundle branch blocks. In the AAMI EC57 standard, `'N'`, `'L'`, `'R'`, `'e'`, `'j'` are grouped into a macro "Non-ectopic" superclass. However, because this project filtered specifically for symbol `'N'`, **there are exactly zero bundle branch block beats in this dataset**.

Describing class `N` as "Normal / bundle branch block beats" is factually incorrect. It must be described strictly as **Normal beats**.

### 2.3 Exact File Locations Requiring Correction:
1. [`README.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/README.md#L20) (Line 20):
   - *Current:* `MIT-BIH annotation class N (Normal / bundle branch block beats, class 0)`
   - *Correction:* `MIT-BIH annotation class N (Normal beats, class 0)`
2. [`report/README_SCIENTIFIC_ACCURACY_AUDIT.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/README_SCIENTIFIC_ACCURACY_AUDIT.md) (Lines 62, 166).
3. [`report/FINAL_PUBLIC_REPOSITORY_MANIFEST.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/FINAL_PUBLIC_REPOSITORY_MANIFEST.md) (Line 269).
4. [`results/final_public_repository_manifest.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/final_public_repository_manifest.json) (Line 273).
5. [`results/phase1_packaging_verification.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/phase1_packaging_verification.json) (Line 60).

---

## 3. Blocker 2: VQC Optimizer Verification

### 3.1 Codebase & Result Inspection
The training engine and result records were inspected:
- **`src/vqc_training.py` (Lines 11, 410–420):**
  ```python
  opt_result = opt.minimize(
      fun=objective_fn,
      x0=theta_0,
      method="COBYLA",
      callback=iteration_callback,
      options={"maxiter": maxiter, "rhobeg": rhobeg, "tol": tol},
  )
  ```
- **`results/vqc_training_runs.json` (Line 6):**
  ```json
  "optimizer": "COBYLA",
  "maxiter": 50,
  ```
- **`results/vqc_model_selection.json` (Lines 6–34):**
  Selected candidate `fold_1_seed_303` was trained under `method="COBYLA"`.

### 3.2 Finding & Scientific Correction
The actual optimizer implemented in `src/vqc_training.py` and executed for all 10 training runs is **SciPy COBYLA** (Constrained Optimization BY Linear Approximation). Nelder-Mead was never invoked in `src/vqc_training.py`.

The erroneous reference to "Nelder-Mead simplex algorithm" in earlier drafts likely arose because COBYLA constructs a simplex of $n+1$ points to calculate linear approximations. However, the algorithm is explicitly **COBYLA**.

### 3.3 Exact File Locations Requiring Correction:
1. [`README.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/README.md#L108) (Line 108):
   - *Current:* `The VQC was optimized classically using the Nelder-Mead simplex algorithm...`
   - *Correction:* `The VQC was optimized classically using the SciPy COBYLA (Constrained Optimization BY Linear Approximation) algorithm...`
2. [`report/FINAL_PUBLIC_REPOSITORY_MANIFEST.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/FINAL_PUBLIC_REPOSITORY_MANIFEST.md) (Lines 39, 95).
3. [`results/final_public_repository_manifest.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/final_public_repository_manifest.json) (Line 112).

---

## 4. Blocker 3: Logistic Regression Held-Out Metrics Reconciliation

### 4.1 Evaluation of Competing Metric Sets
The repository contains two conflicting accounts of the classical Logistic Regression benchmark on the held-out test cohort ($N=100$, Records 200 & 208):

| Metric | Set 1: Canonical Milestone 4 Result (`results/classical_baseline.json`) | Set 2: Unverified README Audit Table (`README.md` Line 114) |
|:---|:---:|:---:|
| **Accuracy** | **92.00%** (92/100) | **71.00%** (71/100) |
| **Sensitivity (VEB)** | **100.00%** (50/50) | **100.00%** (50/50) |
| **Specificity (Normal)** | **84.00%** (42/50) | **42.00%** (21/50) |
| **Precision** | **86.21%** (50/58) | **63.29%** (50/79) |
| **F1-Score** | **0.9259** | **0.7752** |
| **ROC-AUC** | **0.9960** | **0.9976** |
| **Brier / MSE** | **0.0547** | **0.1782** |
| **Confusion Matrix** | $\text{TN}=42, \text{FP}=8, \text{FN}=0, \text{TP}=50$ | $\text{TN}=21, \text{FP}=29, \text{FN}=0, \text{TP}=50$ |
| **Supporting Artifact** | [`results/classical_baseline.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/classical_baseline.json#L275-L285), [`report/classical_baseline.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/classical_baseline.md#L89) | **NONE (No JSON, no CSV, no script trace)** |

### 4.2 Independent Replication
Executing clean replication across training partition permutations revealed:
1. **Model trained on all $N=200$ development beats:**
   - Accuracy: **92.00%**, Sensitivity: **100.00%**, Specificity: **84.00%**, Precision: **86.21%**, F1: **0.9259**, ROC-AUC: **0.9960**. Exactly reproduces Set 1.
2. **Model trained only on Record 106 ($N=100$):**
   - Accuracy: **90.00%**, Sensitivity: **96.00%**, Specificity: **84.00%**, Precision: **85.71%**, F1: **0.9057**, ROC-AUC: **0.9884**.
3. **Model trained only on Record 119 ($N=100$):**
   - Accuracy: **64.00%**, Sensitivity: **28.00%**, Specificity: **100.00%**, Precision: **100.00%**, F1: **0.4375**, ROC-AUC: **0.9904**.

### 4.3 Root Cause & Recommendation
No valid configuration in the codebase produces 71.00% accuracy. The 71.00% result in `README.md` is an unverified artifact introduced in a preliminary draft.

**Auditor Directive:** In accordance with the mandate not to select whichever looks better, this blocker is marked **`UNRESOLVED / FAIL`**. 
- **Required Action:** Remove the unsupported 71.00% Classical Baseline column from `README.md` table, OR replace it with the verified 92.00% baseline from `results/classical_baseline.json` with honest scientific disclosure:
  > *"On the held-out test cohort, the classical L2-regularized Logistic Regression baseline achieved 92.00% accuracy (0.9259 F1), while the 6-qubit VQC achieved 76.00% accuracy (0.8065 F1) in ideal simulation and 77.00% (0.8130 F1) under noise, with both models achieving 100.00% sensitivity on VEB beats."*

---

## 5. Blocker 4: Review of Proposed Public Audit Documents

A thorough line-by-line inspection was performed on the 4 audit documents proposed for publication:

### 5.1 `report/ORGANIZER_FAQ_COMPLIANCE_RECONCILIATION.md`
- **Copyrighted / Restricted Content:** Lines 38, 65, 79, 87 quote organizer challenge kit PDFs and FAQ emails verbatim ("Sourced verbatim from Updated_Challenge_Kit.pdf, Section 3.1...").
- **Internal / Private Operations:** Section 7 reproduces raw Git terminal command outputs (`git ls-files`, `git status --short --untracked-files=all`).
- **Defective Content:** Line 67 reproduces the old hallucinated feature list ("$R_{\text{peak}}$, QRS duration, $T_{\text{amplitude}}$, $P\text{-}R$ interval, $R\text{-}R$ pre, $R\text{-}R$ post").
- **Recommendation:** **`EXCLUDE`** from public repository.

### 5.2 `report/PHASE1_SUBMISSION_READINESS_AUDIT.md`
- **Internal Operational Details:** Section 1 (line 22) states "README.md is empty (0 bytes) and main.ipynb is an unpopulated single-cell stub", which describes pre-packaging state and is now stale. Section 6 lists private internal decisions for the project owner.
- **Defective Content:** Line 31 cites the hallucinated feature list; line 154 cites Nelder-Mead.
- **Copyrighted Content:** Quotes Challenge Kit text verbatim.
- **Recommendation:** **`EXCLUDE`** from public repository.

### 5.3 `results/organizer_faq_compliance.json`
- **Restricted Content:** Cites internal Google Drive paths and reproduces organizer rulings.
- **Defective Content:** Line 23 cites the hallucinated feature names.
- **Recommendation:** **`EXCLUDE`** from public repository.

### 5.4 `results/phase1_submission_readiness.json`
- **Internal Operational Details:** Line 17 describes internal pre-submission tasks; line 47 cites `scratch/test_mapping.py` located in the unpublishable scratch directory.
- **Recommendation:** **`EXCLUDE`** from public repository.

---

## 6. Blocker 5: Proposed `.gitignore` Additions Review

### 6.1 Evaluation of Current & Proposed Rules
Current `.gitignore` properly excludes `.venv/`, `__pycache__/`, and `data/mitbih/`.

- **Proposed `docs/` Rule Evaluation:**  
  The proposed rule `docs/` is **OVERLY BROAD**. It would block any future project documentation, diagrams, or guides created in `docs/`.  
  *Refinement:* Exclude strictly `docs/challenge_materials/`, which contains only the organizer's copyrighted PDFs.
- **Proposed `backup_*/` Rule Evaluation:**  
  Safe and targeted. Successfully ignores `backup_audit_20261013/` and `backup_phase6_final_20261013/` without affecting any source or test code.
- **Proposed `scratch/` Rule Evaluation:**  
  Safe and targeted. Successfully ignores temporary test and diagnostic scripts.
- **Proposed `*.log` Rule Evaluation:**  
  Safe and standard.

### 6.2 Recommended Minimum Safe `.gitignore` Additions:
```gitignore
# ============================================================================
# Safety backups (local development and audit snapshots)
# ============================================================================
backup_*/

# ============================================================================
# Temporary scratch and diagnostic scripts
# ============================================================================
scratch/

# ============================================================================
# Competition challenge materials (organizer PDFs - not for redistribution)
# ============================================================================
docs/challenge_materials/

# ============================================================================
# Local task and execution logs
# ============================================================================
*.log
```

---

## 7. Blocker 6: Comprehensive Security & Privacy Scan

### 7.1 Scope & Methodology
A comprehensive scan was executed across all publishable and configuration files using `scratch/security_checker.py`:
- **File Extensions Covered:** `.py`, `.ipynb`, `.md`, `.json`, `.ini`, `.txt`, `.gitignore`.
- **Directories Inspected:** Root, `src/`, `processors/`, `tests/`, `results/`, `report/`, `data/processed/`, `figures/`.
- **Search Patterns:** Generic API keys, passwords, private keys, IBM Quantum tokens, bearer tokens, AWS keys (`AKIA...`), GitHub personal access tokens (`ghp_...`), and local Windows user profile paths (`C:\Users\...`).

### 7.2 Findings & Scan Limitations
- **Secrets & Credentials Found:** **`ZERO (0)`**.
- **Private Tokens / Auth Headers Found:** **`ZERO (0)`**.
- **Local User Directory Paths Found in Publishable Files:** **`ZERO (0)`**.
- **Scan Limitations:** Binary assets (`.png`, `.pdf`, `.dat`, `.atr`, `.hea`), `.git/`, and `.venv/` were not scanned for plaintext patterns.

---

## 8. Summary of Action Items Prior to Staging

To resolve all publication blockers and make the repository 100% ready for staging:

1. [ ] **Correct `README.md` Line 20:** Replace "Normal / bundle branch block beats" with "Normal beats".
2. [ ] **Correct `README.md` Line 108:** Replace "Nelder-Mead simplex algorithm" with "SciPy COBYLA (Constrained Optimization BY Linear Approximation)".
3. [ ] **Reconcile `README.md` Baseline Table:** Remove the unsupported 71.00% Classical Baseline column or replace it with the verified 92.00% baseline from `results/classical_baseline.json`.
4. [ ] **Update Public Manifest:** Reclassify the 4 audit documents (`report/ORGANIZER_FAQ_COMPLIANCE_RECONCILIATION.md`, `report/PHASE1_SUBMISSION_READINESS_AUDIT.md`, `results/organizer_faq_compliance.json`, `results/phase1_submission_readiness.json`) as **EXCLUDE**.
5. [ ] **Append Refined `.gitignore` Block:** Append `backup_*/`, `scratch/`, `docs/challenge_materials/`, `*.log`.
