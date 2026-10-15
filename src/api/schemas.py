"""
Pydantic Request and Response Schemas for NEXUS-OPS FastAPI Backend.
===================================================================
NEXUS-OPS | PS-Q1 Biomedical Signal Classifier (IBM Quantum Qiskit Fall Fest 2026)
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health and quantum simulation telemetry status."""
    status: str = Field(default="ok", description="Service status ('ok' or 'degraded')")
    service: str = Field(default="NEXUS-OPS Biomedical AI Engine")
    version: str = Field(default="1.0.0")
    qiskit_version: str = Field(..., description="Installed Qiskit release")
    aer_version: str = Field(..., description="Installed Qiskit Aer release")
    execution_mode: str = Field(default="Classical Simulation (Qiskit StatevectorEstimator / Aer)")
    is_physical_qpu: bool = Field(default=False, description="Strictly False - simulator execution only")
    model_loaded: bool = Field(..., description="Whether frozen VQC model weights are loaded")
    checkpoint_id: str = Field(..., description="Checkpoint run ID (fold_1_seed_303)")
    timestamp: str = Field(..., description="ISO 8601 server timestamp")


class FrozenModelInfoResponse(BaseModel):
    """Frozen model checkpoint metadata and variational weights."""
    run_id: str = Field(..., description="Identifier of the selected cross-validation model")
    source_fold: int = Field(..., description="Source LORO fold (1 or 2)")
    seed: int = Field(..., description="Random initialization seed")
    train_record: int = Field(..., description="Development training record ID (e.g. 106)")
    val_record: int = Field(..., description="Development validation record ID (e.g. 119)")
    selection_rule: str = Field(..., description="Model selection criterion (balanced_validation)")
    parameter_count: int = Field(default=12, description="Trainable variational parameter count")
    optimal_theta: List[float] = Field(..., description="12 frozen variational angles in radians")
    num_qubits: int = Field(default=6, description="Logical qubit width")
    ansatz_type: str = Field(default="RealAmplitudes (reps=1, linear entanglement, 12 parameters)")
    observable: str = Field(default="Ensemble average Pauli-Z: O = (Z0 + Z1 + Z2 + Z3 + Z4 + Z5) / 6")
    composite_validation_score: float = Field(..., description="Composite score on validation set")


class EcgFeaturesInput(BaseModel):
    """6 continuous MLII features extracted from a 1.0-second ECG beat window."""
    pre_rr: float = Field(..., description="Pre-R-peak interval in seconds")
    post_rr: float = Field(..., description="Post-R-peak interval in seconds (retrospective feature)")
    qrs_rms: float = Field(..., description="Root-mean-square amplitude in QRS window in mV")
    qrs_duration: float = Field(..., description="QRS duration in seconds")
    p2p_amplitude: float = Field(..., description="Peak-to-peak amplitude in QRS window in mV")
    spectral_ratio: float = Field(..., description="Spectral band power ratio (high/low frequency)")
    is_pre_scaled: bool = Field(
        default=False,
        description="True if features are already normalized into [0, pi]; False to use training-fitted scaler"
    )


class InferenceRequest(BaseModel):
    """Request payload for quantum forward-pass inference on an ECG beat."""
    sample_id: Optional[Union[str, int]] = Field(default=None, description="Optional beat segment identifier or index")
    record_id: Optional[int] = Field(default=None, description="Optional MIT-BIH record ID")
    features: EcgFeaturesInput = Field(..., description="6 continuous morphological features")


class InferenceResponse(BaseModel):
    """Deterministic forward-pass quantum inference result."""
    sample_id: Optional[Union[str, int]] = None
    record_id: Optional[int] = None
    raw_features: Dict[str, float]
    scaled_features: List[float]
    clipping_occurred: bool = Field(..., description="Whether any feature exceeded [0, pi] and was clamped")
    clipped_features: List[str] = Field(default_factory=list, description="List of feature names that were clipped")
    pauli_z_expectation: float = Field(..., description="Expectation value <O> in [-1.0, +1.0]")
    probability_veb: float = Field(..., description="P(VEB) = (<O> + 1) / 2 in [0.0, 1.0]")
    binary_prediction: int = Field(..., description="0 for Normal (N), 1 for VEB (V)")
    classification_label: str = Field(..., description="'Normal (N)' or 'Ventricular Ectopic Beat (VEB)'")
    decision_threshold: float = Field(default=0.5, description="Decision boundary on P(VEB)")
    execution_type: str = Field(default="Qiskit StatevectorEstimator (Ideal Statevector Simulation)")
    is_physical_qpu: bool = Field(default=False)


class EcgSampleItem(BaseModel):
    """Single MIT-BIH beat from the quarantined held-out test cohort."""
    sample_index: int
    segment_id: str
    record_id: int
    true_label: int
    annotation_symbol: str
    true_label_name: str
    features_raw: Dict[str, float]
    features_scaled: List[float]
    pauli_z_expectation: float
    probability_veb: float
    prediction: int
    predicted_label_name: str
    is_correct: bool
    is_clipped: bool
    notes: Optional[str] = None


class EcgSamplesResponse(BaseModel):
    """List of representative and quarantined held-out test beats."""
    total_cohort_samples: int
    held_out_records: List[int]
    samples: List[EcgSampleItem]


class HardwareTranspileResponse(BaseModel):
    """Result of circuit compilation onto target quantum hardware topology."""
    processor_name: str
    physical_qubits: int
    logical_qubits: int = 6
    success: bool
    capacity_exceeded: bool
    error_type: Optional[str] = None
    message: str
    depth: Optional[int] = None
    depth_with_measurements: Optional[int] = None
    cx_count: Optional[int] = None
    swap_count: Optional[int] = None
    total_ops: Optional[int] = None
    ops: Optional[Dict[str, int]] = None
    physical_layout: Optional[List[int]] = None
    is_physical_qpu: bool = False


class EvaluationMetricsResponse(BaseModel):
    """Quarantined held-out evaluation and classical baseline benchmarks."""
    checkpoint_id: str
    held_out_records: List[int]
    sample_count: int
    vqc_metrics: Dict[str, Any]
    classical_baselines: Dict[str, Any]
    expected_calibration_error: float
    clipping_summary: Dict[str, Any]
    scientific_disclosures: Dict[str, str]


class OverviewResponse(BaseModel):
    """Executive summary of the NEXUS-OPS quantum biomedical classification engine."""
    project_name: str = "NEXUS-OPS"
    subproject: str = "PS-Q1 Biomedical Signal Classifier"
    event: str = "IBM Quantum Qiskit Fall Fest 2026"
    status: str = "operational"
    checkpoint_id: str
    qubit_count: int = 6
    parameter_count: int = 12
    total_samples: int = 300
    train_samples: int = 200
    test_samples: int = 100
    lead_name: str = "MLII"
    sampling_rate_hz: float = 360.0
    key_metrics: Dict[str, Any]
    clipping_summary: Dict[str, Any]
    execution_mode: str = "Classical Simulation (Qiskit StatevectorEstimator / Aer)"
    is_physical_qpu: bool = False
    scientific_disclosures: Dict[str, str]


class EcgWaveformResponse(BaseModel):
    """Full 360-sample raw voltage signal waveform and clinical annotations for an ECG segment."""
    segment_id: str
    record_id: int
    split: str
    beat_index: int
    r_peak_sample: int
    window_start: int
    window_end: int
    lead_name: str = "MLII"
    sampling_rate_hz: float = 360.0
    annotation_symbol: str
    label: int
    label_name: str
    signal_samples: List[float] = Field(..., description="Exactly 360 raw voltage signal samples (mV)")
    features_raw: Dict[str, float]
    features_scaled: Optional[List[float]] = None
    pauli_z_expectation: Optional[float] = None
    probability_veb: Optional[float] = None
    prediction: Optional[int] = None
    predicted_label_name: Optional[str] = None
    is_clipped: bool = False
    notes: Optional[str] = None


class EcgSegmentSummaryItem(BaseModel):
    """Compact summary of an ECG beat segment."""
    segment_id: str
    record_id: int
    split: str
    beat_index: int
    annotation_symbol: str
    label: int
    label_name: str
    r_peak_sample: int
    features_raw: Dict[str, float]
    is_clipped: bool = False


class EcgListResponse(BaseModel):
    """Collection of MIT-BIH segments with filtering metadata."""
    total_segments: int
    returned_count: int
    segments: List[EcgSegmentSummaryItem]


class DatasetResponse(BaseModel):
    """Dataset metadata, LORO partition specifications, and scaler clipping audit."""
    dataset_name: str = "MIT-BIH Arrhythmia Database"
    lead: str = "Modified Lead II (MLII)"
    sampling_rate_hz: float = 360.0
    segment_duration_seconds: float = 1.0
    samples_per_segment: int = 360
    total_segments: int = 300
    splits: Dict[str, Any]
    partitioning_type: str = "Record-Level Partitioning (Leave-One-Record-Out)"
    features: List[Dict[str, str]]
    retrospective_feature_disclosure: str
    patient_separation_disclosure: str
    clipping_audit: Dict[str, Any]


class HardwareOverviewResponse(BaseModel):
    """Comparative analysis of Processor A vs Processor B quantum compilation."""
    target_hardware: str = "Processor B (9-qubit Heavy-Hex Architecture)"
    reference_hardware: str = "Processor A (5-qubit Linear Baseline)"
    execution_mode: str = "Classical Simulation (Qiskit StatevectorEstimator / Aer Simulator)"
    is_physical_qpu: bool = False
    processor_a: HardwareTranspileResponse
    processor_b: HardwareTranspileResponse
    comparison_summary: Dict[str, Any]


class PerformanceResponse(BaseModel):
    """Model evaluation benchmarks, classical comparisons, and calibration metrics."""
    checkpoint_id: str
    held_out_records: List[int]
    sample_count: int
    vqc_metrics: Dict[str, Any]
    noisy_simulation_metrics: Dict[str, Any]
    classical_baselines: Dict[str, Any]
    matched_condition_warning: str
    expected_calibration_error: float
    scientific_limitations: Dict[str, str]

