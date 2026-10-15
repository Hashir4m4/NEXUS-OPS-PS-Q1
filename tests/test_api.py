"""
Tests for NEXUS-OPS FastAPI Backend API
=======================================
Verifies endpoint responses, schemas, deterministic inference,
hardware transpilation contracts, and scientific qualification disclosures.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "NEXUS-OPS"
    assert data["subproject"] == "PS-Q1 Biomedical Signal Classifier"
    assert data["is_physical_qpu"] is False
    assert data["execution_mode"] == "Classical Simulation (Qiskit StatevectorEstimator)"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert data["checkpoint_id"] == "fold_1_seed_303"
    assert data["is_physical_qpu"] is False
    assert "2.5.2" in data["qiskit_version"]


def test_model_info_endpoint():
    response = client.get("/api/model/info")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "fold_1_seed_303"
    assert data["source_fold"] == 1
    assert data["seed"] == 303
    assert data["train_record"] == 106
    assert data["val_record"] == 119
    assert data["parameter_count"] == 12
    assert len(data["optimal_theta"]) == 12
    assert data["num_qubits"] == 6


def test_inference_predict_normal_sample_14():
    """Sample 14 (Record 200) is Normal (N). Model should predict Normal."""
    payload = {
        "sample_id": "REC200_B0828_N",
        "record_id": 200,
        "features": {
            "pre_rr": 0.9055555555555556,
            "post_rr": 0.975,
            "qrs_rms": 0.5072870943345902,
            "qrs_duration": 0.05277777777777778,
            "p2p_amplitude": 1.605,
            "spectral_ratio": 0.21913284229572522,
            "is_pre_scaled": False,
        },
    }
    response = client.post("/api/inference/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["binary_prediction"] == 0
    assert data["classification_label"] == "Normal (N)"
    assert data["pauli_z_expectation"] < 0.0
    assert data["probability_veb"] < 0.5
    assert pytest.approx(data["pauli_z_expectation"], abs=1e-3) == -0.3603
    assert pytest.approx(data["probability_veb"], abs=1e-3) == 0.3199


def test_inference_predict_veb_sample_11():
    """Sample 11 (Record 200) is VEB (V). Model should predict VEB."""
    payload = {
        "sample_id": "REC200_B0693_V",
        "record_id": 200,
        "features": {
            "pre_rr": 0.5055555555555555,
            "post_rr": 0.9277777777777778,
            "qrs_rms": 1.1176274766086365,
            "qrs_duration": 0.06944444444444445,
            "p2p_amplitude": 2.945,
            "spectral_ratio": 0.09081898977565325,
            "is_pre_scaled": False,
        },
    }
    response = client.post("/api/inference/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["binary_prediction"] == 1
    assert data["classification_label"] == "Ventricular Ectopic Beat (VEB)"
    assert data["pauli_z_expectation"] > 0.0
    assert data["probability_veb"] > 0.5
    assert pytest.approx(data["pauli_z_expectation"], abs=1e-3) == 0.4774
    assert pytest.approx(data["probability_veb"], abs=1e-3) == 0.7387


def test_inference_predict_morphology_shift_sample_82():
    """Sample 82 (Record 208) is a Normal beat exhibiting tape shift false positive."""
    payload = {
        "sample_id": "REC208_B2007_N",
        "record_id": 208,
        "features": {
            "pre_rr": 0.4777777777777778,
            "post_rr": 0.4916666666666667,
            "qrs_rms": 0.5663737525301828,
            "qrs_duration": 0.03333333333333333,
            "p2p_amplitude": 2.775,
            "spectral_ratio": 0.18606086780829875,
            "is_pre_scaled": False,
        },
    }
    response = client.post("/api/inference/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Classified as VEB due to baseline recording shift
    assert data["binary_prediction"] == 1
    assert data["classification_label"] == "Ventricular Ectopic Beat (VEB)"
    assert pytest.approx(data["probability_veb"], abs=1e-3) == 0.5638


def test_ecg_samples_endpoint():
    response = client.get("/api/ecg/samples?limit=15")
    assert response.status_code == 200
    data = response.json()
    assert data["total_cohort_samples"] == 100
    assert len(data["samples"]) == 15
    assert data["held_out_records"] == [200, 208]

    # Verify sample 11 and 14 are in cohort
    sample_11 = next((s for s in data["samples"] if s["sample_index"] == 11), None)
    assert sample_11 is not None
    assert sample_11["true_label"] == 1
    assert sample_11["prediction"] == 1

    sample_14 = next((s for s in data["samples"] if s["sample_index"] == 14), None)
    assert sample_14 is not None
    assert sample_14["true_label"] == 0
    assert sample_14["prediction"] == 0


def test_hardware_transpile_processor_b():
    response = client.get("/api/hardware/transpile/processor-b")
    assert response.status_code == 200
    data = response.json()
    assert data["processor_name"] == "Processor B"
    assert data["physical_qubits"] == 9
    assert data["logical_qubits"] == 6
    assert data["success"] is True
    assert data["capacity_exceeded"] is False
    assert data["depth"] == 15
    assert data["depth_with_measurements"] == 16
    assert data["cx_count"] == 5
    assert data["swap_count"] == 0
    assert data["physical_layout"] == [0, 1, 2, 4, 5, 6]


def test_hardware_transpile_processor_a():
    response = client.get("/api/hardware/transpile/processor-a")
    assert response.status_code == 200
    data = response.json()
    assert data["processor_name"] == "Processor A"
    assert data["physical_qubits"] == 5
    assert data["logical_qubits"] == 6
    assert data["success"] is False
    assert data["capacity_exceeded"] is True
    assert data["error_type"] == "CircuitTooWideForTarget"


def test_evaluation_metrics():
    response = client.get("/api/metrics/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert data["checkpoint_id"] == "fold_1_seed_303"
    assert data["sample_count"] == 100
    metrics = data["vqc_metrics"]
    assert metrics["sensitivity"] == 1.0
    assert metrics["specificity"] == 0.52
    assert pytest.approx(metrics["f1_score"], abs=1e-3) == 0.8065
    assert metrics["roc_auc"] == 0.9988
    assert metrics["confusion_matrix"]["tp"] == 50
    assert metrics["confusion_matrix"]["tn"] == 26
    assert metrics["confusion_matrix"]["fp"] == 24
    assert metrics["confusion_matrix"]["fn"] == 0


def test_clipping_audit():
    response = client.get("/api/audit/clipping")
    assert response.status_code == 200
    data = response.json()
    assert data["total_evaluated_values"] == 600
    assert data["total_clipped_values"] == 14
    assert data["affected_beats_count"] == 13
    assert pytest.approx(data["clipping_rate_values_pct"], abs=1e-2) == 2.33
    assert data["affected_beats_pct"] == 13.0


def test_overview_endpoint():
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "NEXUS-OPS"
    assert data["checkpoint_id"] == "fold_1_seed_303"
    assert data["total_samples"] == 300
    assert data["train_samples"] == 200
    assert data["test_samples"] == 100
    assert data["qubit_count"] == 6
    assert data["parameter_count"] == 12
    assert data["is_physical_qpu"] is False
    assert data["key_metrics"]["vqc_sensitivity"] == 1.0
    assert data["key_metrics"]["vqc_specificity"] == 0.52
    assert data["key_metrics"]["vqc_accuracy"] == 0.76


def test_ecg_list_and_waveform_endpoints():
    # Test ECG list with filtering
    res_list = client.get("/api/ecg?record_id=200&limit=5")
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert data_list["total_segments"] > 0
    assert len(data_list["segments"]) <= 5
    seg_0 = data_list["segments"][0]
    assert seg_0["record_id"] == 200

    # Test full 360-sample waveform endpoint
    first_seg_id = seg_0["segment_id"]
    res_wave = client.get(f"/api/ecg/{first_seg_id}")
    assert res_wave.status_code == 200
    wave_data = res_wave.json()
    assert wave_data["segment_id"] == first_seg_id
    assert len(wave_data["signal_samples"]) == 360
    assert wave_data["sampling_rate_hz"] == 360.0
    assert wave_data["lead_name"] == "MLII"
    assert "pre_rr" in wave_data["features_raw"]

    # Test 404 for nonexistent segment
    res_404 = client.get("/api/ecg/NONEXISTENT_SEGMENT_9999")
    assert res_404.status_code == 404


def test_quantum_and_hardware_overview_endpoints():
    # Test /api/quantum
    res_q = client.get("/api/quantum")
    assert res_q.status_code == 200
    q_data = res_q.json()
    assert q_data["run_id"] == "fold_1_seed_303"
    assert q_data["observable"] == "Ensemble average Pauli-Z: O = (Z0 + Z1 + Z2 + Z3 + Z4 + Z5) / 6"
    assert q_data["ansatz_type"] == "RealAmplitudes (reps=1, linear entanglement, 12 parameters)"

    # Test /api/hardware
    res_hw = client.get("/api/hardware")
    assert res_hw.status_code == 200
    hw_data = res_hw.json()
    assert hw_data["is_physical_qpu"] is False
    assert hw_data["processor_b"]["success"] is True
    assert hw_data["processor_b"]["depth"] == 15
    assert hw_data["processor_a"]["capacity_exceeded"] is True


def test_performance_and_dataset_endpoints():
    # Test /api/performance
    res_perf = client.get("/api/performance")
    assert res_perf.status_code == 200
    perf_data = res_perf.json()
    assert perf_data["checkpoint_id"] == "fold_1_seed_303"
    assert perf_data["vqc_metrics"]["sensitivity"] == 1.0
    assert "Classical baselines were trained on 200" in perf_data["matched_condition_warning"]

    # Test /api/dataset
    res_ds = client.get("/api/dataset")
    assert res_ds.status_code == 200
    ds_data = res_ds.json()
    assert ds_data["total_segments"] == 300
    assert ds_data["splits"]["development"]["records"] == [106, 119]
    assert ds_data["splits"]["held_out_test"]["records"] == [200, 208]
    assert "post_rr uses the succeeding R-peak" in ds_data["retrospective_feature_disclosure"]
    assert "does not constitute verified patient-level separation" in ds_data["patient_separation_disclosure"]
    assert ds_data["clipping_audit"]["total_clipped_values"] == 14

