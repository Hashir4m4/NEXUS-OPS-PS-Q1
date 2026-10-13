"""Unit and integration tests for Milestone 4.1 Classical Baseline Scientific Integrity Audit.

Validates:
1. Integrity and completeness of classical baseline audit artifacts.
2. Test-set isolation and historical bias documentation.
3. LORO Fold 2 ranking-monotonicity versus threshold calibration.
4. Correct patient record attribution of false positives (Records 200 and 208).
5. Scaled-space odds ratio and physical interval calculations.
6. Conditional pass verdict enforcement.
"""

import sys
import json
from pathlib import Path
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.classical_baseline_audit import run_baseline_audit


@pytest.fixture(scope="module")
def audit_data():
    """Load the generated classical baseline audit results."""
    artifact_path = Path("results/classical_baseline_audit.json")
    if not artifact_path.exists():
        run_baseline_audit()
    with open(artifact_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_audit_artifact_completeness(audit_data):
    """Verify that all required audit sections are present in the JSON artifact."""
    required_keys = [
        "test_set_isolation_audit",
        "loro_investigation",
        "loro_auc_explanation",
        "false_positive_audit",
        "feature_interpretability_audit",
        "clinical_safety_audit",
        "audit_verdict",
    ]
    for key in required_keys:
        assert key in audit_data, f"Missing required section in audit JSON: {key}"


def test_test_set_isolation_status(audit_data):
    """Verify that test set isolation was strictly audited and retrospectively corrected."""
    iso_audit = audit_data["test_set_isolation_audit"]
    assert iso_audit["status"] == "CORRECTED_RETROSPECTIVELY"
    assert iso_audit["test_records"] == [200, 208]
    assert iso_audit["participated_in_feature_selection"] is False
    assert iso_audit["participated_in_hyperparameter_tuning"] is False
    assert iso_audit["participated_in_scaler_fitting"] is False
    assert "pre-specified architectural parity" in iso_audit["corrected_selection_rule"]


def test_loro_fold_2_ranking_monotonicity(audit_data):
    """Verify that Fold 2 AUC=1.0 is driven by strict monotonic separation despite low threshold sensitivity."""
    fold_2_lr = audit_data["loro_investigation"]["fold_2"]["models"]["logistic_regression"]
    
    assert fold_2_lr["roc_auc"] == 1.0
    assert fold_2_lr["threshold_sensitivity_at_0_5"] < 0.5  # Sensitivity is 0.28 due to threshold miscalibration
    assert fold_2_lr["probability_overlap"] is False  # Zero overlap between Normal and VEB
    
    # min(VEB prob) must be strictly greater than max(Normal prob)
    min_veb_prob = fold_2_lr["veb_prob_range"][0]
    max_normal_prob = fold_2_lr["normal_prob_range"][1]
    assert min_veb_prob > max_normal_prob, (
        f"Expected monotonic separation but min(VEB)={min_veb_prob} <= max(Normal)={max_normal_prob}"
    )


def test_test_false_positive_record_attribution(audit_data):
    """Verify exact false positive counts and record origins in test cohort (200 & 208)."""
    fp_audit = audit_data["false_positive_audit"]
    assert fp_audit["total_false_positives_logistic_regression"] == 8
    
    breakdown = fp_audit["false_positive_breakdown_by_record"]
    assert breakdown["record_200"] == 3
    assert breakdown["record_208"] == 5
    
    traces = fp_audit["individual_fp_traces"]
    assert len(traces) == 8
    
    # Check that all FP traces come from either 200 or 208 and have label 0 (Normal)
    for trace in traces:
        assert trace["record_id"] in [200, 208]
        assert trace["segment_id"].endswith("_N")
        assert trace["logistic_probability"] >= 0.5


def test_record_208_tachycardia_evidence(audit_data):
    """Verify that Record 208 false positives have RR intervals under 0.60 seconds (tachycardia)."""
    traces = audit_data["false_positive_audit"]["individual_fp_traces"]
    rec_208_traces = [t for t in traces if t["record_id"] == 208]
    assert len(rec_208_traces) == 5
    
    for trace in rec_208_traces:
        # Patient 208 sinus tachycardia gives normal RR around 0.47 - 0.57s
        assert trace["pre_rr_seconds"] < 0.60, (
            f"Expected Pre-RR < 0.60s for Rec 208 tachycardia beat, got {trace['pre_rr_seconds']}"
        )


def test_scaled_feature_odds_ratios_and_conversions(audit_data):
    """Verify mathematical consistency of scaled odds ratios and physical step conversions."""
    lr_interp = audit_data["feature_interpretability_audit"]["logistic_regression"]
    
    # Features must match 6 engineered features
    expected_features = ["pre_rr", "post_rr", "qrs_rms", "qrs_duration", "p2p_amplitude", "spectral_ratio"]
    for feat in expected_features:
        assert feat in lr_interp
        coeff = lr_interp[feat]["coefficient_scaled_space"]
        or_val = lr_interp[feat]["odds_ratio_per_radian"]
        np.testing.assert_allclose(np.exp(coeff), or_val, rtol=1e-5)
        assert lr_interp[feat]["physical_change_per_radian"] > 0


def test_clinical_safety_qualifications(audit_data):
    """Verify that zero false negatives is qualified as a sample statistic and lookahead latency is documented."""
    safety = audit_data["clinical_safety_audit"]
    assert "sample statistic" in safety["zero_false_negatives_qualification"]
    assert "lookahead delay" in safety["post_rr_latency_qualification"]
    assert "retrospective" in safety["post_rr_latency_qualification"]


def test_audit_verdict_conditional_pass(audit_data):
    """Verify that the baseline audit verdict is explicitly CONDITIONAL PASS and permits proceeding to VQC."""
    verdict_info = audit_data["audit_verdict"]
    assert verdict_info["verdict"] == "CONDITIONAL PASS"
    assert verdict_info["safe_to_proceed_to_vqc"] is True
