# NEXUS-OPS — Organizer FAQ Compliance & Specification Reconciliation Report
## IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Signal Classifier

**Document Version:** 1.0
**Audit Date:** 2026-10-13
**Auditor:** Senior Quantum Machine Learning Research Auditor & Technical Governance Lead
**Project Workspace:** `c:\Data\Projects\NEXUS-OPS\NEXUS-OPS\PS-Q1-Biomedical-Classifier`
**Milestone:** Post-Phase 6 Compliance Audit & Organizer FAQ Alignment
**Overall Compliance Status:** **`VERIFIED WITH LIMITATIONS`**

---

## 1. Executive Summary & Audit Mandate

On 13 October 2026, the Qiskit Fall Fest 2026 organizers released an updated FAQ clarifying critical aspects of problem statement formulations, hardware specifications, noise models, and competition phase boundaries:

1. **Problem Statement Distinction:** Clarified the scope of PS-O1 (6-vertex combinatorial graph problem) and affirmed that vertex-reduction or fixing techniques are not officially approved.
2. **Processor Capacities:** Affirmed Processor A as 5 physical qubits and Processor B as 9 physical qubits.
3. **Phase-Gated Handling:** Clarified that the expected handling of 6-variable problems on 5-qubit Processor A will be officially specified in Phase 2.
4. **Noise Model Status:** Declared that conflicting CX error rates (e.g., $0.005$ vs. $0.010$) in earlier documents are illustrative examples, and that final physical noise models and native basis gates will only be confirmed post-Phase 1 shortlisting.
5. **Phase Boundaries:** Reaffirmed that Phase 1 focuses on Processor A vs. Processor B comparisons, while Processor C (13 qubits) and custom Processor D belong strictly to Phase 2.

This report independently audits the entire NEXUS-OPS codebase, experimental outputs, and Phase 6 reports against these 10 organizer clarifications. It establishes rigorous project identity boundaries, reclassifies noise and hardware claims, provides an exhaustive conflict resolution table, and validates repository integrity without altering frozen VQC models or raw results.

---

## 2. Task 1 — Project Identity and Scope: PS-Q1 vs. PS-O1

### 2.1 Project Identity & Registration Verification
The NEXUS-OPS repository is exclusively registered for and executing:
- **Track:** Quantum Machine Learning (QML) Track (Section 9, `Updated_Challenge_Kit.pdf`, Page 11).
- **Problem Statement:** **`PS-Q1: Biomedical Signal Classifier`**.
- **Objective:** Supervised binary classification of patient electrocardiogram (ECG) beat segments as Normal (`N`, class 0) versus Ventricular Ectopic Beat (`V`, class 1) using the PhysioNet MIT-BIH Arrhythmia Database.
- **Circuit Architecture:** 6-feature continuous angle encoding ($\text{RY}$ gates), 6-qubit `RealAmplitudes` ansatz (linear entanglement, 12 variational parameters), and an ensemble Pauli-$Z$ observable $\hat{O} = \frac{1}{6}\sum_{j=0}^5 Z_j$.

### 2.2 Formal Demarcation: PS-Q1 vs. PS-O1
The organizer FAQ dated 13 October 2026 mentions:
> *"PS-O1 has 6 vertices... Do not assume fixing a vertex or another vertex-reduction method is officially approved. The expected handling of the 6-vertex versus 5-qubit case will be clarified in the updated specification during Phase 2."*

To prevent scope creep and invalid methodological transfers, the table below establishes the fundamental distinctions between the two problem statements:

| Dimension | PS-Q1 (NEXUS-OPS Workspace) | PS-O1 (Organizer FAQ Reference) |
|:---|:---|:---|
| **Challenge Track** | **Quantum Machine Learning Track** | **Quantum Optimization Track** |
| **Problem Description** | Biomedical Signal Classifier (ECG beats) | Max-Cut on a Weighted Graph |
| **Input Data Structure** | Continuous feature vectors $\mathbf{x} \in \mathbb{R}^6$ derived from ECG signals | Adjacency matrix of a 6-vertex graph $G=(V, E)$ with integer weights $w_{ij} \in \{1,\dots,5\}$ |
| **Algorithmic Family** | Variational Quantum Classifier (VQC) with classical optimizer (COBYLA) | Quantum Approximate Optimization Algorithm (QAOA) / QUBO formulation |
| **Variables / Qubits** | 6 logical qubits encoding 6 independent physiological features | 6 graph vertices mapping to 6 spin variables $\sigma_i \in \{-1, +1\}$ |
| **Symmetry Properties** | Asymmetric continuous feature space (no $\mathbb{Z}_2$ symmetry) | Global $\mathbb{Z}_2$ bit-flip symmetry ($\sigma \to -\sigma$ preserves cut value) |
| **Vertex-Reduction Concept** | **Not applicable.** Fixing or discarding a feature deletes clinical information | Proposed by participants to fix one vertex to 0 (exploiting $\mathbb{Z}_2$ symmetry) to fit 5 qubits |
| **Organizer FAQ Status** | Independent continuous classifier; capacity limit audited | Fixing a vertex is **NOT officially approved**; handling clarified in Phase 2 |

### 2.3 Methodological Directive
**NEXUS-OPS shall not apply PS-O1 graph constraints, vertex-fixing heuristics, or combinatorial cut metrics to the PS-Q1 Biomedical Classifier.** The official challenge documents maintain strict track separation between Quantum Machine Learning (PS-Q1) and Quantum Optimization (PS-O1).

---

## 3. Task 2 — Processor A/B Specifications & Capacity Reconciliation

### 3.1 Processor A: 5-Qubit Linear Topology
- **Physical Capacity:** Exactly **5 physical qubits**.
- **Coupling Topology:** Canonical linear nearest-neighbor chain: `0 - 1 - 2 - 3 - 4` (bidirectional CX).
- **Organizer Capacity Instruction:**
  Sourced verbatim from `Updated_Challenge_Kit.pdf`, Section 3.1 (Page 3) and Section 12 FAQ (Page 15):
  > *"For a problem requiring more than 5 logical qubits, do not delete variables merely to force the full problem into A. Treat A as a capacity/routing reference and perform the full-size execution on Processor B where permitted."*
- **Capacity Finding for PS-Q1:**
  Our approved VQC requires 6 logical qubits to represent the 6 extracted ECG features (pre-RR, post-RR, QRS RMS amplitude, QRS duration, peak-to-peak amplitude, spectral ratio). As proven in [`report/quantum_hardware_experiment_report.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/quantum_hardware_experiment_report.md) and enforced in unit test [`tests/test_hardware_experiments.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests/test_hardware_experiments.py)::`test_processor_a_capacity_limit_enforcement`, transpiling a 6-qubit circuit onto 5 physical qubits raises a `TranspilerError` due to insufficient physical qubits.
- **Handling of Comparator:**
  To satisfy the Phase 1 requirement for Processor A/B comparison without violating the non-truncation directive, NEXUS-OPS constructed an auxiliary **5-Qubit Reference Circuit** solely as an architectural comparator. The full 6-variable biomedical model is executed exclusively on Processor B.
- **Outstanding Question for Organizers (Phase 2):**
  > *For 6-variable problems (such as 6-feature QML classifiers or 6-vertex optimization graphs), will Phase 2 require an official feature-selection/decomposition protocol for Processor A, or will Processor A remain strictly a formal capacity/routing reference demonstrating the threshold where 5-qubit hardware is insufficient?*

### 3.2 Processor B: 9-Qubit Heavy-Hex Sparse Tree Topology
- **Physical Capacity:** Exactly **9 physical qubits** (confirmed by the 13 October FAQ and `Updated_Challenge_Kit.pdf`).
- **Coupling Map:** 8 bidirectional pairs forming a heavy-hex-inspired sparse tree:
  `[(0,1), (1,2), (2,3), (2,4), (4,5), (5,6), (4,7), (7,8)]`.
- **Superseded Statements:**
  Older draft documents (`processor_ab_benchmark.pdf`, p. 4) described an exploratory 7-qubit Processor B. The Updated Challenge Kit FAQ (Page 15) and new 13 October FAQ explicitly instruct:
  > *"For this participant-facing kit, use Processor B as a 9-qubit architecture. Do not revert to an older 7-qubit description."*
  Any prior mention of a 7-qubit Processor B is formally marked **`SUPERSEDED`**.

---

## 4. Task 3 — Reclassification of Noise Parameters and Basis Gates

The new FAQ states:
> *"Conflicting illustrative CX error rates such as 0.005 and 0.01 are not official. Final noise parameters and supported basis gates will be clarified in the official configuration after Phase 1 shortlisting."*

Accordingly, all hardware parameters previously cited in NEXUS-OPS reports are hereby reclassified into distinct epistemic categories:

| Parameter / Setting | Value in Project | Status in Challenge Materials | Epistemic Classification in NEXUS-OPS | Auditor Instruction |
|:---|:---:|:---|:---|:---|
| **Single-Qubit Error Rate** $p_{1q}$ | $0.001$ (depolarizing) | Sourced from Section 3.4 of Updated Challenge Kit | **PROVISIONAL SIMULATION ASSUMPTION** | Do not cite as certified hardware rate; cite as challenge illustrative model. |
| **Two-Qubit Error Rate** $p_{2q}$ | $0.005$ (depolarizing) | Section 3.4 of Updated Challenge Kit; conflicts with $0.010$ in Starter Guide | **PROVISIONAL SIMULATION ASSUMPTION** | Note conflict with 0.010; cite as team-selected simulation parameter for benchmark comparability. |
| **Readout Error Rate** $p_{\text{meas}}$ | $0.010$ (symmetric bit-flip) | Section 3.4 of Updated Challenge Kit | **PROVISIONAL SIMULATION ASSUMPTION** | Treat as illustrative measurement noise baseline. |
| **Basis Gate Set** | `{rz, sx, x, cx}` | Standard universal IBM decomposition in Challenge Kit | **PROVISIONAL TARGET BASIS** | Target compilation set for simulated transpilation; final hardware native gates confirmed in Phase 2. |
| **Shot Budget** | $S = 4096$ shots | Sourced from Section 3.4 | **PROVISIONAL BENCHMARK BUDGET** | Used for finite-sampling statistical evaluations; physical budget subject to execution guidelines. |
| **Transpiler Directives** | `optimization_level=1`, SABRE, seed 42 | Section 3.4 of Updated Challenge Kit | **STANDARDIZED REPRODUCIBILITY BASELINE** | Standardized for deterministic benchmark comparison across teams. |
| **Processor JSON Files** | `processor_A.json`, `processor_B.json` | Section 4.1 / Notes (Page 6) | **TEAM-DEFINED IMPLEMENTATION** | Participant-created files based on organizer topology definitions. |

### Preservation of Scientific Results
All Phase 6 simulated benchmark results (e.g., [`results/transpilation_comparison.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/transpilation_comparison.json), [`results/noisy_simulation_results.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/noisy_simulation_results.json), [`results/shot_based_results.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/shot_based_results.json)) remain mathematically and computationally valid. They represent **rigorous simulated hardware benchmarks under provisional organizer specifications**, not measurements on physical quantum processors.

---

## 5. Task 4 — Reassessment of Phase 6 Claims and Scientific Verifications

### 5.1 Maintained Scientific & Mathematical Findings
The following empirical and theoretical results are independently audited and confirmed to stand without qualification:
1. **Analytical Variance of Ensemble Observable:**
   Proved that $\hat{O}^2 = \frac{1}{6}I + \frac{1}{18}\sum_{j < k} Z_j Z_k$, giving exact state variance $\text{Var}_{\psi}(\hat{O}) = \frac{1}{6} + \frac{1}{18}\sum_{j < k}\langle Z_j Z_k \rangle_{\psi} - \langle \hat{O} \rangle_{\psi}^2$.
2. **Exact Quantum State Variance Across 100 Test Samples:**
   Mean quantum state variance $\overline{\text{Var}(\hat{O})} = \mathbf{0.334035}$ (min $0.127490$, max $0.623930$, std $0.126820$), yielding a noiseless theoretical standard error of $\mathbf{0.008870}$ at $S = 4096$.
3. **Formal Retraction of the "0.533" Covariance Claim:**
   Formally retracted the claim that $0.533$ represents a measured covariance. It was an inverted back-calculation $(0.011403 / 0.015625)^2 = 0.5326$ derived from noisy 3-seed simulation dispersion.
4. **Statevector vs. Aer Sampler Equivalence:**
   Reconciled test shot counts: CI unit test operates at $S = 50,000$ shots ($|diff| < 0.0016 < 0.015$), while standalone high-precision benchmark operates at $S = 500,000$ shots ($|diff| < 0.0009 < 0.005$). Both confirm layout and bitstring unpacking correctness.
5. **Transpilation Metrics on Processor B:**
   Compiled 6-qubit circuit onto 9-qubit topology with 0 SWAP gates, 5 CX gates, and circuit depth of 24.
6. **Regression Test Integrity:**
   **116 / 116 passing tests** across 12.78s with 0 failures and 0 warnings.

### 5.2 Calibrated Reporting Claims
To ensure complete compliance with the new FAQ:
- **No Physical Hardware Execution:** Explicitly stated as **`NOT PERFORMED`**.
- **No Claim of Final Noise Certification:** Synthetic noise experiments are reported strictly as simulated sensitivity analyses under provisional challenge parameters.
- **No Equivalence with PS-O1:** Explicitly recorded that PS-Q1 operates on clinical ECG features, not combinatorial graph vertices.
- **Phase 2 Scope Boundary:** Processor C and custom Processor D are acknowledged as Phase 2 activities, with preliminary conceptual exploration deferred to post-shortlisting.

---

## 6. Comprehensive Organizer FAQ Conflict Resolution Matrix

| # | Topic / Issue | Authoritative Document & Location | Previous Working Statement | Latest Organizer Clarification (13 Oct 2026 FAQ) | NEXUS-OPS Final Treatment | Final Evidence Status |
|:---:|:---|:---|:---|:---|:---|:---:|
| **1** | **Scope of PS-O1 vs. PS-Q1** | FAQ Item 1; Updated Challenge Kit Section 7 (p. 8) & Section 9 (p. 11) | Implicit assumption that 6-variable capacity rules are uniform across all tracks | PS-O1 has 6 vertices in Max-Cut; vertex-fixing is NOT approved; PS-Q1 is a separate QML classifier | Formally demarcated PS-Q1 (biomedical signal classifier) from PS-O1 (graph optimization); graph vertex rules do not apply to PS-Q1 | **`VERIFIED`** |
| **2** | **Processor A Capacity Limit** | FAQ Item 2 & 4; Updated Challenge Kit Section 3.1 (p. 3) & Section 12 (p. 15) | 6Q cannot map to 5Q Processor A; used 5Q reference circuit as comparator | Processor A has 5 qubits; do not assume vertex reduction or variable truncation is approved; Phase 2 will clarify | Preserved 5Q reference circuit as an auxiliary architectural comparator; documented Processor A capacity limit; awaiting Phase 2 guidance | **`VERIFIED WITH LIMITATIONS`** |
| **3** | **Processor B Capacity Definition** | FAQ Item 3; Updated Challenge Kit Section 3.2 (p. 3) & Section 12 (p. 15) | Processor B is 9 qubits; older drafts mentioned 7 qubits | Processor B has 9 qubits; do not revert to older 7-qubit descriptions | Confirmed 9-qubit heavy-hex sparse tree as authoritative; marked all 7-qubit references as SUPERSEDED | **`VERIFIED`** |
| **4** | **Conflicting CX Error Rates** | FAQ Item 6; Updated Challenge Kit Section 3.4 (p. 4); Starter Guide | $p_{2q} = 0.005$ treated as challenge specification | Conflicting CX rates (0.005 in kit vs 0.01 in Starter Guide) are illustrative, not official | Reclassified $p_{2q} = 0.005$ as a PROVISIONAL SIMULATION ASSUMPTION; preserved simulation results with explicit caveat | **`VERIFIED WITH LIMITATIONS`** |
| **5** | **Noise Model & Basis Gate Finality** | FAQ Item 7; Updated Challenge Kit Section 3.4 (p. 4) | Basis `{rz, sx, x, cx}` and noise parameters treated as official baseline | Final noise parameters and supported basis gates clarified post-Phase 1 shortlisting | Reclassified all noise parameters and basis gates as PROVISIONAL / AWAITING CONFIRMATION | **`VERIFIED WITH LIMITATIONS`** |
| **6** | **Phase 1 Required Comparisons** | FAQ Item 8; Participant Instructions (p. 7) | Required Processor A vs Processor B comparison, metrics, and routing | Phase 1 requires Processor A/B comparison, problem-specific metrics, and architecture metrics | Verified that existing deliverables provide complete A/B routing, depth, CX, accuracy, and F1 comparisons | **`VERIFIED`** |
| **7** | **Processor C and Processor D Scope** | FAQ Item 9; Participant Instructions (p. 8) | Exploratory Processor D concepts discussed in Phase 1 planning | Processor C (13Q) and custom Processor D belong to Phase 2 | Confirmed Phase 1 scope stops at Processor A and B; Processor C and D reserved for Phase 2 | **`VERIFIED`** |
| **8** | **Authoritative Information Source** | FAQ Item 10; Updated Challenge Kit (p. 1) | Updated Challenge Kit PDF treated as main reference | Pinned Google Drive folder is authoritative location for Phase 1 instructions, notebooks, and structure | Synchronized all project documentation with pinned Drive kit; noted Drive repository structure guidelines | **`VERIFIED`** |

---

## 7. Task 5 — Repository Evidence & Git Tracking Status

### 7.1 Command Output: `git ls-files`
Executing inspection of critical Phase 5 and Phase 6 milestone handover documents:
```powershell
git ls-files report/PHASE6_FINAL_EVIDENCE_RECONCILIATION.md results/phase6_final_verification.json report/PHASE5_PHASE6_FINAL_HANDOVER.md
```
**Captured Output:**
*(No files returned — standard output is empty)*

**Auditor Interpretation:**
The queried files (`PHASE6_FINAL_EVIDENCE_RECONCILIATION.md`, `phase6_final_verification.json`, `PHASE5_PHASE6_FINAL_HANDOVER.md`) are currently **untracked by git**. They reside safely on the local file system within the workspace, but have not been staged (`git add`) or committed, adhering strictly to the non-commit mandate.

### 7.2 Command Output: `git status --short --untracked-files=all`
```powershell
git status --short --untracked-files=all
```
**Analysis of Output:**
- **Modified Tracked Files:** **0** (no lines starting with `M` or `M `).
- **Deleted Tracked Files:** **0**.
- **Staged Changes:** **0**.
- **Untracked Workspace Artifacts (`??`):**
  - Project configuration: `pytest.ini`
  - Processor definitions: `processors/processor_A.json`, `processors/processor_B.json`, `processors/processor_a.py`, `processors/processor_b.py`
  - Phase 5/6 reports: `report/PHASE5_FINAL_AUDIT.md`, `report/PHASE6_FINAL_EVIDENCE_RECONCILIATION.md`, etc.
  - Phase 5/6 results: `results/phase6_final_verification.json`, `results/shot_based_results.json`, etc.
  - Phase 5/6 tests: `tests/test_hardware_experiments.py`, `tests/test_vqc_training.py`, etc.
  - Full backups: `backup_audit_20261013/`, `backup_phase6_final_20261013/`

**Integrity Conclusion:**
The working tree has **zero uncommitted modifications to existing tracked files**. The untracked files strictly represent active development artifacts, tests, and safety backups produced during authorized milestones.

---

## 8. Summary of Authorized Milestone Statuses

| Milestone / Component | Evaluated Status | Justification |
|:---|:---:|:---|
| **Project Scope & Identity** | **`VERIFIED`** | Formally confirmed as PS-Q1 (Biomedical Signal Classifier); segregated from PS-O1. |
| **Processor B Specification** | **`VERIFIED`** | Confirmed 9 qubits, heavy-hex tree topology; superseded older 7Q description. |
| **Processor A Specification & Capacity** | **`VERIFIED WITH LIMITATIONS`** | Confirmed 5 qubits, linear chain; capacity limit enforced; awaiting Phase 2 guidance. |
| **Noise Model & Basis Gate Classification** | **`VERIFIED WITH LIMITATIONS`** | Reclassified as provisional simulation assumptions awaiting post-shortlisting confirmation. |
| **Analytical Variance & Retraction** | **`VERIFIED`** | Exact formula proved; mean variance $0.334035$ measured; $0.533$ claim formally retracted. |
| **Transpiler Mapping & Aer Equivalence** | **`VERIFIED`** | Reconciled 50k (CI) vs 500k (benchmark) shot counts; bitstring order and layout verified. |
| **Physical Hardware Execution** | **`NOT PERFORMED`** | No physical IBM QPU execution was performed. |
| **Test Suite Integrity** | **`VERIFIED`** | 116 / 116 tests passing in 12.78s. |
| **Overall FAQ Compliance** | **`VERIFIED WITH LIMITATIONS`** | Fully aligned with 13 October 2026 FAQ; provisional parameters explicitly caveated. |

---

**Auditor Sign-off:**
The NEXUS-OPS project documentation, benchmark metrics, and reporting language are now completely reconciled with the 13 October 2026 Organizer FAQ. Phase 6 remains frozen, reproducible, scientifically defensible, and ready for Phase 1 submission evaluation.
