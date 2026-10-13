"""
Unit Tests for VQC Pre-Training Baseline Diagnostics & Forward-Pass Validation
=============================================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 5F.3, Step 2)

Verifies:
1. Training cohort data integrity (200 samples, 100 per record, balanced, no NaNs/Infs,
   held-out test records 200 and 208 strictly quarantined in features_test.csv).
2. Diagnostics JSON artifact integrity and schema compliance.
3. Multi-seed initialization properties across all 5 approved seeds [42, 101, 202, 303, 404]:
   - Parameters strictly in [-0.1, 0.1]
   - Initial mean probability centered near neutral ([0.50, 0.53])
   - Initial Brier/MSE loss < 0.20 (outperforming naive 0.25 coin-flip baseline on balanced data)
   - Positive class-polarity separation (Δp > 0) with Normal < 0.50 and VEB > 0.50
   - Non-trivial initial prediction distribution.
4. Active parameter sensitivity across all 12 variational weights (|dE/dθ| >= 1e-4 with ε=0.01;
   zero dead parameters at tested initialization).
5. LORO fold diagnostic consistency and feature distribution shift (clipping rates).
6. Bit-exact reproducibility under StatevectorEstimator simulation for both expectation and probability.
7. Processor B transpilation compatibility (compilation checks: depth 15, 5 CX, 0 SWAP;
   not physical hardware execution).
"""

import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qiskit.primitives import StatevectorEstimator

from src.feature_extraction import FEATURE_NAMES
from src.vqc_circuit import (
    NUM_QUBITS,
    NUM_ENCODING_PARAMS,
    NUM_VARIATIONAL_PARAMS,
    TOTAL_CIRCUIT_PARAMS,
    create_parameter_vectors,
    build_vqc_circuit,
    build_ensemble_z_observable,
    format_pub_parameters,
    expectation_to_probability,
)
from src.vqc_preprocessing import prepare_loro_fold
from processors.processor_b import transpile_for_processor_b

DATA_DIR = PROJECT_ROOT / "data" / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
DIAGNOSTICS_JSON_PATH = RESULTS_DIR / "vqc_training_step2_diagnostics.json"


@pytest.fixture(scope="module")
def training_dataset():
    """Loads the training dataset (features_train.csv)."""
    csv_path = DATA_DIR / "features_train.csv"
    assert csv_path.exists(), f"features_train.csv not found at {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def test_dataset():
    """Loads the quarantined test dataset (features_test.csv)."""
    csv_path = DATA_DIR / "features_test.csv"
    assert csv_path.exists(), f"features_test.csv not found at {csv_path}"
    return pd.read_csv(csv_path)


@pytest.fixture(scope="module")
def diagnostics_artifact():
    """Loads the Milestone 5F.3 Step 2 diagnostics JSON artifact."""
    assert DIAGNOSTICS_JSON_PATH.exists(), f"Diagnostics JSON not found at {DIAGNOSTICS_JSON_PATH}"
    with open(DIAGNOSTICS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# 1. DATASET INTEGRITY & HELD-OUT QUARANTINE
# ============================================================================

def test_training_dataset_integrity_and_quarantine(training_dataset, test_dataset):
    """
    Independently derives and verifies that features_train.csv contains exactly
    200 samples from records 106 and 119 with perfect 50/50 class balance,
    zero NaNs/Infs across the six continuous features, and that held-out test
    patients (200, 208) reside strictly in features_test.csv.
    """
    df_train = training_dataset
    df_test = test_dataset

    # Row count verification
    assert len(df_train) == 200, f"Expected exactly 200 training rows, found {len(df_train)}"

    # Record distribution independently derived
    record_counts = df_train["record_id"].value_counts().to_dict()
    assert set(record_counts.keys()) == {106, 119}, f"Unexpected training records: {set(record_counts.keys())}"
    assert record_counts[106] == 100
    assert record_counts[119] == 100

    # Class balance independently derived
    label_counts = df_train["label"].value_counts().to_dict()
    assert label_counts.get(0, 0) == 100
    assert label_counts.get(1, 0) == 100

    # Six continuous feature columns verification
    expected_features = [
        "pre_rr",
        "post_rr",
        "qrs_rms",
        "qrs_duration",
        "p2p_amplitude",
        "spectral_ratio",
    ]
    assert list(FEATURE_NAMES) == expected_features, f"FEATURE_NAMES mismatch: {FEATURE_NAMES}"
    for col in FEATURE_NAMES:
        assert col in df_train.columns, f"Missing feature column {col} in training set"
        assert not df_train[col].isna().any(), f"NaN values detected in feature {col}"
        assert not np.isinf(df_train[col]).any(), f"Inf values detected in feature {col}"

    # Strict held-out quarantine: Records 200 and 208 MUST NOT be present in training set
    assert 200 not in df_train["record_id"].values, "Contamination: Record 200 found in training set!"
    assert 208 not in df_train["record_id"].values, "Contamination: Record 208 found in training set!"

    # Verify that test records 200 and 208 reside in test set
    test_record_counts = df_test["record_id"].value_counts().to_dict()
    assert set(test_record_counts.keys()) == {200, 208}, f"Unexpected test records: {set(test_record_counts.keys())}"
    assert len(df_test) == 100, f"Expected 100 test rows, found {len(df_test)}"


# ============================================================================
# 2. DIAGNOSTICS ARTIFACT SCHEMA & INTEGRITY
# ============================================================================

def test_diagnostics_artifact_schema(diagnostics_artifact):
    """
    Verifies that the generated diagnostics JSON contains all mandatory
    top-level sections, approved metadata, qualified thresholds, and correct keys.
    """
    data = diagnostics_artifact
    required_sections = [
        "metadata",
        "dataset_integrity",
        "initialization_diagnostics",
        "loro_record_wise_diagnostics",
        "parameter_sensitivity_diagnostics",
        "reproducibility_verification",
        "processor_b_compatibility",
    ]
    for section in required_sections:
        assert section in data, f"Missing required top-level section: {section}"

    meta = data["metadata"]
    assert meta["qiskit_version"] == "2.5.2"
    assert meta["qiskit_aer_version"] == "0.17.2"
    assert meta["approved_seeds"] == [42, 101, 202, 303, 404]
    assert meta["theta_init_distribution"] == "Uniform[-0.1, 0.1]"

    ds_integrity = data["dataset_integrity"]
    assert ds_integrity["total_rows"] == 200
    assert ds_integrity["class_balance"] == {"0": 100, "1": 100}
    assert ds_integrity["record_counts"] == {"106": 100, "119": 100}
    assert ds_integrity["nan_count"] == 0
    assert ds_integrity["inf_count"] == 0
    assert ds_integrity["test_contamination_detected"] is False
    assert ds_integrity["held_out_quarantine_maintained"] is True

    # Parameter sensitivity section qualification check
    ps_data = data["parameter_sensitivity_diagnostics"]
    assert ps_data["perturbation_epsilon"] == 0.01
    assert ps_data["sensitivity_threshold"] == 0.0001
    assert "qualification" in ps_data

    # Reproducibility section checks
    repro_data = data["reproducibility_verification"]
    assert repro_data["max_absolute_expectation_difference"] == 0.0
    assert repro_data["max_absolute_probability_difference"] == 0.0
    assert repro_data["status"] == "BIT_EXACT_REPRODUCIBLE"


# ============================================================================
# 3. MULTI-SEED INITIALIZATION PROPERTIES (SEEDS 42, 101, 202, 303, 404)
# ============================================================================

def test_five_seed_initialization_metrics(diagnostics_artifact):
    """
    Verifies all 5 seeds adhere to pre-training diagnostic expectations:
    - 12 parameters initialized in [-0.1, 0.1]
    - Mean probability in [0.50, 0.53]
    - Initial Brier/MSE loss < 0.20 on balanced cohort (better than 0.25 naive guess)
    - Positive initial polarity separation Δp > 0.13
    - Normal mean p < 0.50, VEB mean p > 0.50
    - Non-trivial predicted class balance.
    NOTE: These values are initialization diagnostics on balanced training data,
    not evidence of trained model performance or clinical utility.
    """
    init_diag = diagnostics_artifact["initialization_diagnostics"]
    approved_seeds = [42, 101, 202, 303, 404]

    for seed in approved_seeds:
        seed_key = f"seed_{seed}"
        assert seed_key in init_diag, f"Missing diagnostic data for {seed_key}"
        s_data = init_diag[seed_key]

        # 12 variational parameters
        theta = s_data["initial_theta"]
        assert len(theta) == NUM_VARIATIONAL_PARAMS
        assert all(-0.1 <= t <= 0.1 for t in theta)

        # Probabilities centered near 0.50
        p_stats = s_data["probability_stats"]
        assert 0.50 <= p_stats["mean"] <= 0.53, f"Seed {seed} p_mean {p_stats['mean']} out of bounds"
        assert p_stats["min"] >= 0.0
        assert p_stats["max"] <= 1.0

        # Brier/MSE loss < 0.20 (better than 0.25 naive baseline on balanced cohort)
        mse_loss = s_data["brier_mse_loss"]
        assert 0.15 <= mse_loss < 0.20, f"Seed {seed} MSE loss {mse_loss} unexpected"

        # Polarity separation: VEB - Normal > 0
        delta_p = s_data["polarity_separation_delta_p"]
        assert delta_p > 0.13, f"Seed {seed} polarity separation {delta_p} too low"

        normal_dist = s_data["normal_class_distribution"]
        veb_dist = s_data["veb_class_distribution"]
        assert normal_dist["p_mean"] < 0.50, f"Seed {seed} Normal mean {normal_dist['p_mean']} >= 0.50"
        assert veb_dist["p_mean"] >= 0.50, f"Seed {seed} VEB mean {veb_dist['p_mean']} < 0.50"
        assert veb_dist["p_mean"] > normal_dist["p_mean"]

        # No single-class collapse
        pred_counts = s_data["predicted_class_counts"]
        assert pred_counts["Normal_0"] > 0
        assert pred_counts["VEB_1"] > 0
        assert pred_counts["Normal_0"] + pred_counts["VEB_1"] == 200


# ============================================================================
# 4. ACTIVE PARAMETER SENSITIVITY (ZERO DEAD WEIGHTS AT INITIALIZATION)
# ============================================================================

def test_parameter_sensitivity_profile(diagnostics_artifact):
    """
    Verifies that all 12 parameters have non-negligible local gradient sensitivity
    (|dE/dθ| >= 1e-4) under central finite differences (ε=0.01) at tested initialization.
    NOTE: Local sensitivity at initialization does not guarantee global trainability
    or absence of barren plateaus on wider topologies.
    """
    sens_data = diagnostics_artifact["parameter_sensitivity_diagnostics"]

    assert sens_data["zero_sensitivity_count"] == 0
    assert sens_data["negligible_sensitivity_count"] == 0
    assert sens_data["non_negligible_sensitivity_count"] == 12

    per_param = sens_data["parameter_details"]
    assert len(per_param) == 12

    layer1_max_sens = []
    layer2_max_sens = []

    for item in per_param:
        assert item["classification"] == "Non-negligible"
        assert item["mean_abs_dE_dtheta"] >= 1e-4
        assert item["max_abs_dE_dtheta"] >= 1e-4
        if "Layer 1" in item["layer"]:
            layer1_max_sens.append(item["max_abs_dE_dtheta"])
        else:
            layer2_max_sens.append(item["max_abs_dE_dtheta"])

    assert len(layer1_max_sens) == 6
    assert len(layer2_max_sens) == 6

    # Structural check: Pre-CX Layer 1 rotations exhibit highest dynamic range
    # because they rotate states prior to the entangling linear CX cascade.
    assert max(layer1_max_sens) > max(layer2_max_sens)


# ============================================================================
# 5. LORO CROSS-VALIDATION BASELINE & DISTRIBUTION SHIFT
# ============================================================================

def test_loro_cross_validation_diagnostics(diagnostics_artifact):
    """
    Verifies LORO cross-validation fold baselines across Fold 1 and Fold 2.
    Confirms positive initial class-polarity separation holds on both folds under
    ideal StatevectorEstimator simulation, while documenting exact clipping counts
    reflecting inter-patient feature distribution shifts.
    NOTE: Evaluated under ideal simulation without hardware noise or decoherence.
    Clipping enforces valid angles in [0, pi] but does not eliminate distribution shift.
    """
    loro_data = diagnostics_artifact["loro_record_wise_diagnostics"]
    assert "fold_1" in loro_data
    assert "fold_2" in loro_data

    f1 = loro_data["fold_1"]
    f2 = loro_data["fold_2"]

    assert f1["train_record"] == 106 and f1["val_record"] == 119
    assert f2["train_record"] == 119 and f2["val_record"] == 106

    # Exact clipping statistics
    f1_clip = f1["val_clipping_stats"]
    assert f1_clip["affected_beats_pct"] == 54.0
    assert f1_clip["clipping_rate_values_pct"] == 20.0
    assert f1_clip["by_feature"]["p2p_amplitude"]["total_clipped"] == 50
    assert f1_clip["by_feature"]["qrs_duration"]["total_clipped"] == 50
    assert f1_clip["by_feature"]["qrs_rms"]["total_clipped"] == 15
    assert f1_clip["by_feature"]["pre_rr"]["total_clipped"] == 4
    assert f1_clip["by_feature"]["spectral_ratio"]["total_clipped"] == 1

    f2_clip = f2["val_clipping_stats"]
    assert f2_clip["affected_beats_pct"] == 89.0
    assert abs(f2_clip["clipping_rate_values_pct"] - 25.6667) < 0.01
    assert f2_clip["by_feature"]["p2p_amplitude"]["total_clipped"] == 41
    assert f2_clip["by_feature"]["spectral_ratio"]["total_clipped"] == 37
    assert f2_clip["by_feature"]["qrs_rms"]["total_clipped"] == 36
    assert f2_clip["by_feature"]["pre_rr"]["total_clipped"] == 21
    assert f2_clip["by_feature"]["post_rr"]["total_clipped"] == 14
    assert f2_clip["by_feature"]["qrs_duration"]["total_clipped"] == 5

    # Polarity separation holds on validation sets for all seeds under ideal simulation
    for s_key in ["seed_42", "seed_101", "seed_202", "seed_303", "seed_404"]:
        f1_perf = f1["seed_evaluations"][s_key]
        f2_perf = f2["seed_evaluations"][s_key]

        assert f1_perf["val_delta_p"] > 0
        assert f2_perf["val_delta_p"] > 0
        assert f1_perf["val_mse"] < 0.20
        assert f2_perf["val_mse"] < 0.25
        assert f1_perf["polarity_consistent"] is True
        assert f2_perf["polarity_consistent"] is True


# ============================================================================
# 6. LIVE STATEVECTOR FORWARD PASS & BIT-EXACT REPRODUCIBILITY
# ============================================================================

def test_live_forward_pass_and_reproducibility():
    """
    Executes live duplicate forward passes using StatevectorEstimator on a 10-beat sample.
    Calculates both maximum expectation difference and maximum probability difference
    directly from their respective arrays, verifying bit-exact determinism without
    unused variables.
    NOTE: Applies strictly to ideal noiseless StatevectorEstimator simulation.
    """
    p_enc, p_var = create_parameter_vectors()
    qc = build_vqc_circuit(p_enc, p_var)
    obs = build_ensemble_z_observable()

    rng = np.random.default_rng(42)
    sample_features = rng.uniform(0.0, np.pi, size=(10, 6))
    theta = rng.uniform(-0.1, 0.1, size=(12,))

    pub_params = format_pub_parameters(sample_features, theta)
    pub = (qc, [obs], pub_params)

    estimator = StatevectorEstimator()
    job1 = estimator.run([pub])
    res1 = job1.result()
    exp1 = res1[0].data.evs

    job2 = estimator.run([pub])
    res2 = job2.result()
    exp2 = res2[0].data.evs

    # Expectations bounded in [-1, 1]
    assert np.all(exp1 >= -1.0) and np.all(exp1 <= 1.0)
    assert np.all(exp2 >= -1.0) and np.all(exp2 <= 1.0)

    # Probabilities computed from expectation arrays and bounded in [0, 1]
    prob1 = expectation_to_probability(exp1)
    prob2 = expectation_to_probability(exp2)
    assert np.all(prob1 >= 0.0) and np.all(prob1 <= 1.0)
    assert np.all(prob2 >= 0.0) and np.all(prob2 <= 1.0)

    # Calculate both maximum expectation difference and maximum probability difference
    max_exp_diff = float(np.max(np.abs(exp1 - exp2)))
    max_prob_diff = float(np.max(np.abs(prob1 - prob2)))

    # Assert bit-exact determinism under ideal simulation
    assert max_exp_diff == 0.0, f"Expectation values non-deterministic: max diff = {max_exp_diff}"
    assert max_prob_diff == 0.0, f"Probabilities non-deterministic: max diff = {max_prob_diff}"


# ============================================================================
# 7. PROCESSOR B TRANSPILATION COMPATIBILITY (NOT PHYSICAL HARDWARE EXECUTION)
# ============================================================================

def test_processor_b_transpilation_compatibility_metrics(diagnostics_artifact):
    """
    Verifies that the approved VQC circuit transpiles to Processor B with
    depth 15, exactly 5 CX gates, and 0 routing SWAPs.
    NOTE: Transpilation confirms compiler mapping and coupling topology routing;
    this is NOT physical quantum hardware execution.
    """
    proc_b = diagnostics_artifact["processor_b_compatibility"]
    assert proc_b["success"] is True
    assert proc_b["transpiled_depth"] == 15
    assert proc_b["cx_count"] == 5
    assert proc_b["swap_count"] == 0
    assert proc_b["routing_overhead_cx"] == 0
    assert proc_b["total_ops"] == 65
    assert proc_b["ops"]["cx"] == 5
    assert proc_b["ops"]["rz"] == 36
    assert proc_b["ops"]["sx"] == 24
