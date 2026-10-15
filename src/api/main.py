"""
NEXUS-OPS — PS-Q1 Quantum Biomedical Classifier API Entry Point
==============================================================
FastAPI REST backend serving deterministic quantum inference,
circuit metadata, hardware transpilation results, and scientific evaluation benchmarks.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.schemas import (
    HealthResponse,
    FrozenModelInfoResponse,
    InferenceRequest,
    InferenceResponse,
    EcgSamplesResponse,
    HardwareTranspileResponse,
    EvaluationMetricsResponse,
    OverviewResponse,
    EcgWaveformResponse,
    EcgListResponse,
    DatasetResponse,
    HardwareOverviewResponse,
    PerformanceResponse,
)
from src.api.service import QuantumBackendService

app = FastAPI(
    title="NEXUS-OPS Quantum Biomedical API",
    description=(
        "REST API for PS-Q1 Biomedical Signal Classifier (IBM Quantum Qiskit Fall Fest 2026). "
        "Deterministic Qiskit VQC forward-pass inference, hardware compilation, and scientific evaluation."
    ),
    version="1.0.0",
)

# Configure CORS for local development and dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
def root() -> Dict[str, Any]:
    """Root endpoint summarizing API identity and execution mode."""
    return {
        "project": "NEXUS-OPS",
        "subproject": "PS-Q1 Biomedical Signal Classifier",
        "event": "IBM Quantum Qiskit Fall Fest 2026",
        "status": "operational",
        "docs_url": "/docs",
        "execution_mode": "Classical Simulation (Qiskit StatevectorEstimator)",
        "is_physical_qpu": False,
    }


@app.get("/health", response_model=HealthResponse, tags=["Diagnostics"])
@app.get("/api/health", response_model=HealthResponse, tags=["Diagnostics"])
def get_health() -> HealthResponse:
    """Returns quantum simulation telemetry and service status."""
    service = QuantumBackendService.get_instance()
    return service.get_health()


# -----------------------------------------------------------------------------
# 1. OVERVIEW ENDPOINT
# -----------------------------------------------------------------------------
@app.get("/api/overview", response_model=OverviewResponse, tags=["Overview"])
def get_overview() -> OverviewResponse:
    """Returns comprehensive executive summary of dataset, model, and hardware metrics."""
    service = QuantumBackendService.get_instance()
    return service.get_overview()


# -----------------------------------------------------------------------------
# 2. ECG DATASET & WAVEFORM ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/ecg", response_model=EcgListResponse, tags=["ECG Dataset"])
def get_ecg_list(
    record_id: Optional[int] = Query(default=None, description="Filter by MIT-BIH record (106, 119, 200, 208)"),
    label: Optional[int] = Query(default=None, description="Filter by label: 0 for Normal (N), 1 for VEB (V)"),
    split: Optional[str] = Query(default=None, description="Filter by split: 'train' or 'test'"),
    limit: Optional[int] = Query(default=100, ge=1, le=300, description="Max segments to return"),
) -> EcgListResponse:
    """Returns filtered collection of ECG beat segments with clinical metadata."""
    service = QuantumBackendService.get_instance()
    return service.get_ecg_segments(record_id=record_id, label=label, split=split, limit=limit)


@app.get("/api/ecg/samples", response_model=EcgSamplesResponse, tags=["ECG Dataset"])
def get_ecg_samples(
    limit: Optional[int] = Query(default=None, ge=1, le=100, description="Max samples to return")
) -> EcgSamplesResponse:
    """Returns representative MIT-BIH beats from the held-out test cohort."""
    service = QuantumBackendService.get_instance()
    return service.get_test_samples(limit=limit)


@app.get("/api/ecg/{segment_id}", response_model=EcgWaveformResponse, tags=["ECG Dataset"])
def get_ecg_waveform(segment_id: str) -> EcgWaveformResponse:
    """Returns the full 360-sample raw voltage signal waveform and features for a specific beat segment."""
    service = QuantumBackendService.get_instance()
    waveform = service.get_ecg_waveform(segment_id=segment_id)
    if waveform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ECG segment '{segment_id}' not found in dataset."
        )
    return waveform


# -----------------------------------------------------------------------------
# 3. QUANTUM MODEL & INFERENCE ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/quantum", response_model=FrozenModelInfoResponse, tags=["Quantum"])
@app.get("/api/quantum/info", response_model=FrozenModelInfoResponse, tags=["Quantum"])
@app.get("/api/model/info", response_model=FrozenModelInfoResponse, tags=["Quantum"])
def get_model_info() -> FrozenModelInfoResponse:
    """Returns frozen VQC checkpoint metadata, optimal weights, and architecture."""
    service = QuantumBackendService.get_instance()
    return service.get_model_info()


@app.post("/api/quantum/predict", response_model=InferenceResponse, tags=["Quantum"])
@app.post("/api/inference/predict", response_model=InferenceResponse, tags=["Quantum"])
def predict(request: InferenceRequest) -> InferenceResponse:
    """
    Executes a deterministic forward-pass on 6 continuous MLII features.
    Computes Pauli-Z expectation value <O> and derived P(VEB) = (<O> + 1) / 2.
    """
    try:
        service = QuantumBackendService.get_instance()
        features_dict = {
            "pre_rr": request.features.pre_rr,
            "post_rr": request.features.post_rr,
            "qrs_rms": request.features.qrs_rms,
            "qrs_duration": request.features.qrs_duration,
            "p2p_amplitude": request.features.p2p_amplitude,
            "spectral_ratio": request.features.spectral_ratio,
        }
        return service.run_inference(
            features=features_dict,
            is_pre_scaled=request.features.is_pre_scaled,
            sample_id=request.sample_id,
            record_id=request.record_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quantum inference execution failed: {str(exc)}"
        )


# -----------------------------------------------------------------------------
# 4. HARDWARE TOPOLOGY & COMPILATION ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/hardware", response_model=HardwareOverviewResponse, tags=["Hardware"])
def get_hardware_overview() -> HardwareOverviewResponse:
    """Returns comparative hardware topology and transpilation analysis."""
    service = QuantumBackendService.get_instance()
    return service.get_hardware_overview()


@app.get("/api/hardware/transpile/processor-b", response_model=HardwareTranspileResponse, tags=["Hardware"])
def transpile_processor_b() -> HardwareTranspileResponse:
    """Transpiles the 6-qubit VQC onto 9-qubit Processor B (0 SWAPs, depth 15/16)."""
    service = QuantumBackendService.get_instance()
    return service.transpile_processor_b()


@app.get("/api/hardware/transpile/processor-a", response_model=HardwareTranspileResponse, tags=["Hardware"])
def transpile_processor_a() -> HardwareTranspileResponse:
    """Enforces capacity boundary on 5-qubit Processor A (CircuitTooWideForTarget)."""
    service = QuantumBackendService.get_instance()
    return service.transpile_processor_a()


# -----------------------------------------------------------------------------
# 5. PERFORMANCE & EVALUATION BENCHMARKS
# -----------------------------------------------------------------------------
@app.get("/api/performance", response_model=PerformanceResponse, tags=["Performance"])
def get_performance_overview() -> PerformanceResponse:
    """Returns complete evaluation benchmarks, classical comparisons, and calibration statistics."""
    service = QuantumBackendService.get_instance()
    return service.get_performance_overview()


@app.get("/api/metrics/evaluation", response_model=EvaluationMetricsResponse, tags=["Performance"])
def get_evaluation_metrics() -> EvaluationMetricsResponse:
    """Returns held-out test evaluation benchmarks and classical baselines."""
    service = QuantumBackendService.get_instance()
    return service.get_evaluation_metrics()


# -----------------------------------------------------------------------------
# 6. DATASET & AUDIT ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/dataset", response_model=DatasetResponse, tags=["Dataset"])
def get_dataset_overview() -> DatasetResponse:
    """Returns MIT-BIH dataset splits, feature descriptions, and clipping audit statistics."""
    service = QuantumBackendService.get_instance()
    return service.get_dataset_overview()


@app.get("/api/audit/clipping", tags=["Dataset"])
def get_clipping_audit() -> Dict[str, Any]:
    """Returns exact feature scaler clamping statistics (14/600 values, 13/100 beats)."""
    service = QuantumBackendService.get_instance()
    eval_resp = service.get_evaluation_metrics()
    return eval_resp.clipping_summary


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)

