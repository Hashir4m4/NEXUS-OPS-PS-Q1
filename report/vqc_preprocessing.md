# Milestone 5D: Leak-Free VQC Preprocessing Pipeline & Protocols

**Project:** Project Q — IBM Quantum Qiskit Fall Fest 2026  
**Challenge:** PS-Q1 — Biomedical Signal Classifier  
**Team:** NEXUS-OPS  
**Stage:** Milestone 5D Preprocessing Implementation & Validation  
**Document Purpose:** Architectural Specification, Verification Results, and Scientific Limitations of the Preprocessing Module for the Variational Quantum Classifier (VQC)  
**Governance Notice:** **ALL TEN VQC ARCHITECTURAL DECISIONS REMAIN PROPOSED — NOT YET TEAM-APPROVED**  
**Submission Deadline:** 14 October 2026  
**Date:** October 13, 2026  

---

## 1. Executive Summary & Engineering Objective

Following the findings of the Milestone 5C Pre-Implementation Leakage Audit ([`report/vqc_preprocessing_leakage_audit.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/vqc_preprocessing_leakage_audit.md)), this milestone implements and validates the standalone preprocessing module:
[`src/vqc_preprocessing.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/vqc_preprocessing.py).

The module establishes a rigorous, leak-free data ingestion interface for all downstream quantum circuits, optimizers, and evaluation routines. It strictly enforces:
1. **Dynamic, Fold-Isolated Scaling for LORO:** Never consumes precomputed `*_scaled` columns in cross-validation. Scalers are dynamically instantiated and fitted on raw features of the active training patient only.
2. **Quarantined Test Set Transformation:** Held-out test records 200 and 208 are transformed using a scaler fitted exclusively on the full training cohort (Records 106 and 119) without refitting.
3. **Rigorous Clipping Tracking:** Captures lower-bound, upper-bound, element-level, and beat-level clipping counts across all partitions.
4. **Guaranteed Bounded Domain:** All outputs strictly satisfy $0.0 \le X \le \pi$, with zero NaNs, zero Infs, and bitwise preservation of sample order, class labels, and metadata.

---

## 2. Preprocessing Architecture & Interface Contract

```
                     +---------------------------------------+
                     |         data/processed/*.csv          |
                     |  (Raw physiological FEATURE_NAMES)   |
                     +---------------------------------------+
                                         |
               +-------------------------+-------------------------+
               |                                                   |
               v                                                   v
     [ PROTOCOL A: LORO CV ]                             [ PROTOCOL B: FINAL BENCHMARK ]
   prepare_loro_datasets()                        prepare_final_benchmark_datasets()
               |                                                   |
    +----------+----------+                                        |
    |                     |                                        |
    v                     v                                        v
[ Fold 1 ]            [ Fold 2 ]                         [ Final Pipeline ]
Train: Rec 106        Train: Rec 119                     Train: Rec 106 + 119 (N=200)
  Fit Scaler            Fit Scaler                         Fit Single Scaler
  Transform Rec 106     Transform Rec 119                  Transform Train (N=200)
Val: Rec 119          Val: Rec 106                       Test: Rec 200 + 208 (N=100)
  Transform Rec 119     Transform Rec 106                  Transform Test (NO FIT)
  Clip to [0, pi]       Clip to [0, pi]                    Clip to [0, pi]
```

### 2.1 Core Data Structures
The module defines three primary dataclasses in [`src/vqc_preprocessing.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/vqc_preprocessing.py):

1. **`PreprocessedPartition`:**
   * `name: str` — Partition description (e.g. `"LORO Fold 1 Train (Record 106)"`).
   * `record_ids: List[int]` — Originating MIT-BIH record identifiers.
   * `X: np.ndarray` — Continuous feature array of shape $(N, 6)$, `float64`, strictly bounded in $[0, \pi]$.
   * `y: np.ndarray` — Binary ground-truth labels of shape $(N,)$, `int64` ($0 = \text{Normal}, 1 = \text{VEB}$).
   * `segment_ids: List[str]` — Unique segment identifiers for end-to-end beat tracking.
   * `annotation_symbols: List[str]` — Original PhysioNet annotation symbols.
   * `clipping_stats: Dict[str, Any]` — Comprehensive clipping breakdown.
   * `scaler: Optional[QuantumFeatureScaler]` — The fitted scaler that produced $X$.

2. **`LOROFoldData`:**
   * `fold_id: int` ($1$ or $2$).
   * `train: PreprocessedPartition` — Active training partition.
   * `val: PreprocessedPartition` — Active held-out validation partition.
   * `scaler: QuantumFeatureScaler` — Fitted scaler instance.

3. **`VQCPreprocessedBundle`:**
   * `fold1: LOROFoldData` — Fold 1 data package.
   * `fold2: LOROFoldData` — Fold 2 data package.
   * `final_train: PreprocessedPartition` — Full training cohort ($N=200$).
   * `final_test: PreprocessedPartition` — Quarantined test cohort ($N=100$).
   * `final_scaler: QuantumFeatureScaler` — Scaler fitted on all 200 training beats.

---

## 3. Protocol Specifications

### 3.1 Protocol A: Leave-One-Record-Out (LORO) Preprocessing
* **Purpose:** Validates patient-level generalizability and hyperparameter robustness during development.
* **Input:** `data/processed/features_train.csv` (using strictly the raw columns: `pre_rr`, `post_rr`, `qrs_rms`, `qrs_duration`, `p2p_amplitude`, `spectral_ratio`).
* **Execution Rule:**
  * **Fold 1:**
    * Training partition: Record 106 ($n=100$). A fresh `QuantumFeatureScaler` is fitted strictly on Record 106 raw features.
    * Validation partition: Record 119 ($n=100$). Transformed using Record 106’s scaler and clipped into $[0, \pi]$.
  * **Fold 2:**
    * Training partition: Record 119 ($n=100$). A fresh `QuantumFeatureScaler` is fitted strictly on Record 119 raw features.
    * Validation partition: Record 106 ($n=100$). Transformed using Record 119’s scaler and clipped into $[0, \pi]$.
* **Prohibition:** Precomputed `*_scaled` columns must **NEVER** be ingested in Protocol A.

### 3.2 Protocol B: Final Model Training & Quarantined Benchmark
* **Purpose:** Generates the input tensors for training the final frozen model and computing the post-hoc test benchmark against held-out patients.
* **Input:**
  * Training cohort: Records 106 and 119 from `features_train.csv` ($n=200$).
  * Quarantined test cohort: Records 200 and 208 from `features_test.csv` ($n=100$).
* **Execution Rule:**
  * A single `QuantumFeatureScaler` is fitted on all 200 samples of Records 106 and 119 combined.
  * Training data is transformed into $[0, \pi]$ ($0$ clips).
  * Held-out test records 200 and 208 are transformed into $[0, \pi]$ using the frozen training scaler without fitting or updating parameters.

---

## 4. Empirical Clipping Statistics & Distribution Shift Evidence

Clipping is monitored through `compute_clipping_statistics()`, which analyzes the continuous unclipped affine projection:
$$z_j = \pi \cdot \frac{x_j - x_{j,\min}}{x_{j,\max} - x_{j,\min}}$$
Values where $z_j < 0.0$ are flagged as lower-bound clipped; values where $z_j > \pi$ are flagged as upper-bound clipped.

### 4.1 Quantitative Summary Table

| Partition | Patient Record(s) | Scaler Origin | Samples ($N$) | Evaluated Elements ($N \times 6$) | Lower-Bound Clipped ($< 0.0$) | Upper-Bound Clipped ($> \pi$) | Total Clipped Elements (%) | Unique Beats Affected (%) |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1 Train** | 106 | Record 106 | $100$ | $600$ | $0$ | $0$ | **$0$ ($0.00\%$)** | **$0$ ($0.00\%$)** |
| **Fold 1 Val** | 119 | Record 106 | $100$ | $600$ | $1$ | $119$ | **$120$ ($20.00\%$)** | **$54$ ($54.00\%$)** |
| **Fold 2 Train** | 119 | Record 119 | $100$ | $600$ | $0$ | $0$ | **$0$ ($0.00\%$)** | **$0$ ($0.00\%$)** |
| **Fold 2 Val** | 106 | Record 119 | $100$ | $600$ | $115$ | $39$ | **$154$ ($25.67\%$)** | **$89$ ($89.00\%$)** |
| **Final Train** | 106 + 119 | Records 106 + 119 | $200$ | $1200$ | $0$ | $0$ | **$0$ ($0.00\%$)** | **$0$ ($0.00\%$)** |
| **Final Test** | 200 + 208 | Records 106 + 119 | $100$ | $600$ | $11$ | $3$ | **$14$ ($2.33\%$)** | **$13$ ($13.00\%$)** |

### 4.2 Feature-Level Breakdown

```
Fold 1 Validation (Record 119 evaluated against Record 106 scaler):
  - pre_rr         : 4 clipped (0 lower, 4 upper)
  - post_rr        : 0 clipped
  - qrs_rms        : 15 clipped (0 lower, 15 upper)
  - qrs_duration   : 50 clipped (0 lower, 50 upper)   <-- 100% of VEBs exceed Rec 106 QRS width
  - p2p_amplitude  : 50 clipped (0 lower, 50 upper)   <-- 100% of VEBs exceed Rec 106 max voltage
  - spectral_ratio : 1 clipped (1 lower, 0 upper)

Fold 2 Validation (Record 106 evaluated against Record 119 scaler):
  - pre_rr         : 21 clipped (21 lower, 0 upper)  <-- Rec 106 has shorter baseline RR
  - post_rr        : 14 clipped (12 lower, 2 upper)
  - qrs_rms        : 36 clipped (36 lower, 0 upper)  <-- Rec 106 has lower RMS amplitudes
  - qrs_duration   : 5 clipped (5 lower, 0 upper)
  - p2p_amplitude  : 41 clipped (41 lower, 0 upper)  <-- Rec 106 has much smaller peak-to-peak voltages
  - spectral_ratio : 37 clipped (0 lower, 37 upper)  <-- Rec 106 exhibits higher high-freq power
```

---

## 5. Critical Scientific Discussion: The Biological Limitations of Feature Clipping

> [!CAUTION]
> **CLIPPING DOES NOT RESOLVE INTER-PATIENT DISTRIBUTION SHIFTS.**  
> Under no circumstances should clipping be reported or understood as a solution to biological or inter-subject variance.

### 5.1 Why Clipping is Applied
In parameterized quantum circuits, single-qubit rotation gates ($R_y(\phi)$) are periodic functions of the rotational angle:
$$R_y(\phi) = \exp\left(-i \frac{\phi}{2} Y\right) = \begin{pmatrix} \cos(\phi/2) & -\sin(\phi/2) \\ \sin(\phi/2) & \cos(\phi/2) \end{pmatrix}$$
Because the gate acts on the initial ground state $|0\rangle$, rotating by $\phi \in [0, \pi]$ spans the upper hemisphere of the Bloch sphere from $|0\rangle$ ($\phi=0$) to $|1\rangle$ ($\phi=\pi$).

If an unclipped feature produced an angle such as $\phi = 1.5\pi$ or $\phi = -\pi/4$, the trigonometric periodicity of the quantum gate would fold the representation back onto the Bloch sphere:
* A feature value of $\phi = 1.5\pi$ would yield a state indistinguishable in probability from $\phi = 0.5\pi$.
* A feature value of $\phi = 2\pi$ would map back to $|0\rangle$, identical to an input of $0.0$.

Therefore, **clipping to $[0, \pi]$ is strictly a mathematical and geometric safeguard** required to prevent trigonometric alias errors and ensure valid arguments to quantum operators.

### 5.2 Why Clipping Truncates Biological Information
When an out-of-distribution feature is clipped:
1. **Dynamic Range Truncation:** All beats in Record 119 with peak-to-peak amplitude exceeding $3.65\text{ mV}$ (whether $3.7\text{ mV}$, $4.1\text{ mV}$, or $4.6\text{ mV}$) are assigned the exact same quantum angle ($\phi_4 = \pi$). The classifier is blinded to continuous morphological differences among these beats.
2. **Artificial Boundary Pile-Up:** Instead of following a continuous physiological distribution, the transformed feature develops a Dirac delta spike at the boundary ($\phi = 0$ or $\phi = \pi$).
3. **Loss of Discriminative Margin:** If both moderate VEBs and extreme VEBs collapse to $\pi$, the variational circuit's decision boundary loses resolution in the highest-risk region of the feature space.

### 5.3 Methodological Justification for LORO Over Stratified Cross-Validation
Ordinary 5-fold stratified cross-validation mixes beats from all patients into every fold. When this is done:
* The training set in every fold contains beats from all patients.
* The min and max statistics span the full cohort, resulting in **$0.0\%$ clipping**.
* The evaluation falsely appears stable, creating the **illusion of high performance** while ignoring that real clinical monitors encounter entirely unseen patients.

By enforcing LORO with fold-specific scaling, Milestone 5D exposes the true extent of inter-subject variance: **$54\%$ to $89\%$ of beats require clipping across individual patients.** This demonstrates that LORO is the only scientifically honest validation method for patient generalizability.

---

## 6. Software Architecture & Unit Test Verification

The module is validated by six specialized unit tests in [`tests/test_vqc_preprocessing.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests/test_vqc_preprocessing.py):

| Test Name | Verified Property | Result |
| :--- | :--- | :---: |
| `test_loro_scaler_isolation_from_validation_perturbations` | Adding $+5000$ to validation patient features causes ZERO change in training scaler parameters. | **PASSED** |
| `test_final_scaler_isolation_from_test_perturbations` | Scaling test set features by $100\times$ causes ZERO change in final training scaler parameters. | **PASSED** |
| `test_loro_ignores_precomputed_scaled_columns` | Stripping or setting precomputed `*_scaled` columns to $99999.9$ causes ZERO change in LORO outputs. | **PASSED** |
| `test_value_bounds_and_finiteness` | All $X$ matrices across all partitions lie strictly in $[0, \pi]$ with no NaNs and no Infs. | **PASSED** |
| `test_metadata_and_order_preservation` | Row order, labels, `record_id`, and `segment_id` match source CSVs row-for-row. | **PASSED** |
| `test_clipping_statistics_exact_counts` | Exact clipping counts (120 in Fold 1 Val, 154 in Fold 2 Val, 14 in Test) match audited numbers. | **PASSED** |

### Complete Test Suite Execution
```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
collected 48 items

tests/test_classical_evaluation.py ........                             [ 16%]
tests/test_classical_models.py ......                                   [ 29%]
tests/test_dataset_validation.py .....                                  [ 39%]
tests/test_ecg_pipeline.py ......                                       [ 52%]
tests/test_feature_audit.py .......                                     [ 66%]
tests/test_feature_extraction.py .....                                  [ 77%]
tests/test_feature_scaling.py .....                                     [ 87%]
tests/test_vqc_preprocessing.py ......                                  [100%]

============================= 48 passed in 6.82s ==============================
```

---

## 7. Compliance & Governance Verification

- [x] **No Quantum Circuits or Optimizers Implemented:** Preserved strictly for Milestone 5E.
- [x] **Classical Baseline Results Unaltered:** Baseline JSON files and metrics remain frozen.
- [x] **Decision Approvals Unaltered:** All ten architecture decisions (D1–D10) in `results/vqc_architecture_decisions.json` remain `PROPOSED_NOT_TEAM_APPROVED`.
- [x] **Original Datasets Unmodified:** All data files in `data/mitbih/` and `data/processed/` are intact.
- [x] **No Claims of Overcoming Distribution Shift:** Explicitly documented that clipping is a numerical quantum gate constraint, not a biological fix.

---

## 8. Single Recommended Next Action for the Technical Lead

> **Present `report/vqc_team_review_summary.md` to the NEXUS-OPS team for formal review, approve the 10 architecture decisions (D1–D10) in `results/vqc_architecture_decisions.json` by updating their status from `PROPOSED_NOT_TEAM_APPROVED` to `TEAM_APPROVED`, and proceed to Milestone 5E: Core VQC Circuit Implementation (`src/vqc_circuit.py`).**
