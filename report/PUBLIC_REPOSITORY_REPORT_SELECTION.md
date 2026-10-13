# NEXUS-OPS — Public Repository Report Selection & Curation Guide
## IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Signal Classifier

**Document Version:** 1.0  
**Audit Date:** 2026-10-13  
**Auditor:** Technical Governance & Scientific Software Lead  
**Scope:** Curation of 43 internal project reports for public GitHub repository submission.

---

## 1. Curation Principles

The NEXUS-OPS project generated 43 technical reports during its phased development, auditing, and calibration cycle. For an external challenge evaluator, submitting 43 separate reports creates cognitive overload and obscures core findings.

This guide classifies every report into three actionable categories:
- **`INCLUDE` (Recommended Public Set):** High-value reports that synthesize final methodology, held-out clinical metrics, hardware compilation evidence, and organizer compliance.
- **`EXCLUDE` (Internal / Redundant / Superseded):** Daily session handover logs, intermediate step-by-step drafting reviews, internal correction logs, and superseded draft audits. These are preserved locally in the project workspace but should not clutter the public repository.
- **`REVIEW` (Human Decision):** Deep-dive research or architectural documents that the project owner may optionally include as supplementary documentation.

---

## 2. Complete Classification Matrix (43 Reports)

| Report File Name | Size (Bytes) | Category | Rationale & Reviewer Utility |
|:---|:---:|:---:|:---|
| **`PHASE5_PHASE6_COMPLETION_REPORT.md`** | 12,496 | **`INCLUDE`** | **Primary Technical Report:** Synthesizes complete Phase 5 QML training and Phase 6 hardware benchmarks. |
| **`quantum_hardware_experiment_report.md`** | 11,394 | **`INCLUDE`** | **Hardware Experiment Report:** Comprehensive analysis of Processor A capacity and Processor B transpilation. |
| **`vqc_evaluation_report.md`** | 10,130 | **`INCLUDE`** | **Clinical Evaluation Report:** Held-out test cohort performance (Records 200 & 208), ECE calibration, and confusion matrices. |
| **`ORGANIZER_FAQ_COMPLIANCE_RECONCILIATION.md`** | 20,382 | **`INCLUDE`** | **Governance Report:** Full reconciliation against 13 October 2026 Organizer FAQ; establishes PS-Q1 vs PS-O1 boundaries. |
| **`PHASE1_SUBMISSION_READINESS_AUDIT.md`** | 21,330 | **`INCLUDE`** | **Independent Audit Report:** Definitive verification of claims, evidence line citations, and submission readiness. |
| **`dataset_preparation.md`** | 10,261 | **`INCLUDE`** | **Data Engineering Report:** MIT-BIH cohort extraction (300 beats) and LORO patient-level split protocol. |
| **`feature_engineering.md`** | 13,149 | **`INCLUDE`** | **Signal Processing Report:** 6 continuous morphological/timing feature extraction and $[0, \pi]$ scaling. |
| **`classical_baseline.md`** | 12,345 | **`INCLUDE`** | **Benchmark Report:** Classical baselines (Logistic Regression, SVM, Random Forest) for comparative evaluation. |
| **`processor_architecture_comparison.md`** | 7,688 | **`INCLUDE`** | **Architecture Summary:** Concise summary of Processor A (5Q linear) vs Processor B (9Q heavy-hex). |
| `vqc_architecture_research.md` | 27,659 | **`REVIEW`** | Supplementary literature review of QML architectures, barren plateaus, and encoding methods. |
| `vqc_architecture_decision_review.md` | 27,966 | **`REVIEW`** | Supplementary architectural justification for 6Q RY + RealAmplitudes vs alternative designs. |
| `vqc_training_report.md` | 8,549 | **`REVIEW`** | Supplementary summary of the 10 Nelder-Mead optimization trajectories. |
| `vqc_model_selection_protocol.md` | 5,326 | **`REVIEW`** | Supplementary description of the composite validation selection metric. |
| `quantum_noise_analysis.md` | 8,256 | **`REVIEW`** | Supplementary sensitivity study on synthetic depolarizing and readout noise. |
| `processor_ab_topology_research.md` | 20,259 | **`REVIEW`** | Deep-dive research document on superconducting chip topology and connectivity. |
| `AUTONOMOUS_SESSION_HANDOVER.md` | 12,743 | **`EXCLUDE`** | Internal agent session handover log; temporary developer context. |
| `PHASE5_PHASE6_FINAL_HANDOVER.md` | 9,925 | **`EXCLUDE`** | Internal milestone handover log; redundant with completion report. |
| `PHASE5_PHASE6_CORRECTION_LOG.md` | 8,399 | **`EXCLUDE`** | Internal intermediate debugging notes and edit changelog. |
| `PHASE5_PHASE6_EXECUTION_PLAN.md` | 7,434 | **`EXCLUDE`** | Preliminary planning checklist superseded by actual completion. |
| `PHASE5_FINAL_AUDIT.md` | 6,044 | **`EXCLUDE`** | Intermediate phase audit superseded by master audit. |
| `PHASE6_FINAL_AUDIT.md` | 6,242 | **`EXCLUDE`** | Intermediate phase audit superseded by master audit. |
| `PHASE5_PHASE6_INDEPENDENT_AUDIT.md` | 14,593 | **`EXCLUDE`** | Intermediate audit iteration superseded by final submission audit. |
| `PHASE6_FINAL_TECHNICAL_CORRECTIONS.md` | 13,621 | **`EXCLUDE`** | Intermediate technical corrections log superseded by final audit. |
| `PHASE6_FINAL_EVIDENCE_RECONCILIATION.md` | 23,522 | **`EXCLUDE`** | Intermediate evidence reconciliation superseded by final submission audit. |
| `classical_baseline_audit.md` | 14,344 | **`EXCLUDE`** | Internal test leakage audit for classical models; validated in code. |
| `feature_audit.md` | 13,970 | **`EXCLUDE`** | Internal scaler clipping audit; findings summarized in feature engineering report. |
| `processor_ab_evidence_audit.md` | 14,361 | **`EXCLUDE`** | Intermediate evidence audit superseded by Phase 6 completion report. |
| `processor_ab_experiment_design.md` | 9,816 | **`EXCLUDE`** | Intermediate design specification superseded by experiment report. |
| `vqc_circuit_design_review.md` | 26,862 | **`EXCLUDE`** | Intermediate circuit review notes; findings consolidated in architecture report. |
| `vqc_circuit_step2_review.md` | 10,730 | **`EXCLUDE`** | Intermediate incremental step log. |
| `vqc_circuit_step3_review.md` | 11,527 | **`EXCLUDE`** | Intermediate incremental step log. |
| `vqc_circuit_step5_review.md` | 13,215 | **`EXCLUDE`** | Intermediate incremental step log. |
| `vqc_circuit_step6_review.md` | 12,808 | **`EXCLUDE`** | Intermediate incremental step log. |
| `vqc_observable_step4_review.md` | 12,283 | **`EXCLUDE`** | Intermediate incremental step log. |
| `vqc_training_architecture_step1_review.md` | 31,863 | **`EXCLUDE`** | Intermediate incremental step log. |
| `vqc_training_step2_diagnostics.md` | 23,009 | **`EXCLUDE`** | Intermediate diagnostic run log. |
| `vqc_implementation_contract.md` | 14,526 | **`EXCLUDE`** | Internal interface contract specification. |
| `vqc_implementation_preflight.md` | 12,900 | **`EXCLUDE`** | Internal preflight verification checklist. |
| `vqc_implementation_readiness_checklist.md` | 8,811 | **`EXCLUDE`** | Internal checklist superseded by completion. |
| `vqc_preprocessing.md` | 15,693 | **`EXCLUDE`** | Detailed intermediate preprocessing draft superseded by `dataset_preparation.md`. |
| `vqc_preprocessing_leakage_audit.md` | 19,206 | **`EXCLUDE`** | Internal leakage verification log; findings preserved in final reports. |
| `vqc_team_approval_record.md` | 8,886 | **`EXCLUDE`** | Internal simulated consensus record. |
| `vqc_team_review_summary.md` | 12,700 | **`EXCLUDE`** | Internal review summary. |

---

## 3. Recommended Core Public Documentation Package

For an elegant, authoritative, and clean GitHub repository submission, the following **9 curated reports** are recommended for public tracking in `report/`:

1. [`report/PHASE5_PHASE6_COMPLETION_REPORT.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE5_PHASE6_COMPLETION_REPORT.md) — Master Technical Synthesis.
2. [`report/quantum_hardware_experiment_report.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/quantum_hardware_experiment_report.md) — Hardware & Noise Analysis.
3. [`report/vqc_evaluation_report.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/vqc_evaluation_report.md) — Clinical Performance & Metrics.
4. [`report/ORGANIZER_FAQ_COMPLIANCE_RECONCILIATION.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/ORGANIZER_FAQ_COMPLIANCE_RECONCILIATION.md) — Organizer FAQ Governance.
5. [`report/PHASE1_SUBMISSION_READINESS_AUDIT.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/PHASE1_SUBMISSION_READINESS_AUDIT.md) — Independent Technical Audit.
6. [`report/dataset_preparation.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/dataset_preparation.md) — Dataset Extraction & LORO Splitting.
7. [`report/feature_engineering.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/feature_engineering.md) — Signal Processing & Feature Scaling.
8. [`report/classical_baseline.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/classical_baseline.md) — Classical Baselines.
9. [`report/processor_architecture_comparison.md`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/report/processor_architecture_comparison.md) — Processor A vs Processor B Comparison.

### Exclusion Rules
- All intermediate step review documents and session handovers remain preserved locally in `report/`, but can be omitted from the initial git commit or moved to an `archive/` folder upon project owner approval.
- Organizer competition guides in `docs/challenge_materials/` must **not** be included in the public repository.
- Internal backups in `backup_audit_*` and `backup_phase6_*` must **not** be tracked.
