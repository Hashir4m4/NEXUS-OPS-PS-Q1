import React, { useState, useEffect, useMemo } from "react";
import {
  Atom,
  Cpu,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Activity,
  Info,
  Sparkles,
  RefreshCw,
  Sliders,
  ShieldAlert,
  Binary,
} from "lucide-react";
import { GlassCard } from "../components/ui/GlassCard";
import { StatusBadge } from "../components/ui/StatusBadge";
import { QuantumCircuitViewer } from "../components/quantum/QuantumCircuitViewer";
import { api } from "../services/api";
import type {
  BackendModelInfo,
  HardwareOverviewResult,
  TranspileResult,
  TestSampleItem,
  PredictResult,
} from "../services/api";
import { FROZEN_MODEL } from "../types/scientific";

interface QuantumAiLabProps {
  onOpenDisclosures: () => void;
}

// 6 Feature Definitions for Lead II encoding
const FEATURE_DEFINITIONS = [
  {
    key: "pre_rr",
    qubit: 0,
    name: "Pre-RR Interval",
    symbol: "x_0",
    unit: "seconds",
    description: "Pre-R-peak interval (R_i - R_{i-1}). Primary clinical marker for premature ventricular pacing.",
    isRetrospective: false,
    minVal: 0.35,
    maxVal: 1.15,
  },
  {
    key: "post_rr",
    qubit: 1,
    name: "Post-RR Interval",
    symbol: "x_1",
    unit: "seconds",
    description: "Post-R-peak interval (R_{i+1} - R_i). Quantifies compensatory pause following ectopic beat.",
    isRetrospective: true,
    minVal: 0.35,
    maxVal: 1.40,
  },
  {
    key: "qrs_rms",
    qubit: 2,
    name: "QRS RMS Voltage",
    symbol: "x_2",
    unit: "mV",
    description: "Root-mean-square amplitude in ±69.4 ms window around R-peak.",
    isRetrospective: false,
    minVal: 0.15,
    maxVal: 1.85,
  },
  {
    key: "qrs_duration",
    qubit: 3,
    name: "QRS Duration",
    symbol: "x_3",
    unit: "seconds",
    description: "Estimated QRS complex duration at 20% envelope threshold.",
    isRetrospective: false,
    minVal: 0.02,
    maxVal: 0.12,
  },
  {
    key: "p2p_amplitude",
    qubit: 4,
    name: "Peak-to-Peak Amplitude",
    symbol: "x_4",
    unit: "mV",
    description: "Total voltage excursion between Q-S extrema in Modified Lead II.",
    isRetrospective: false,
    minVal: 0.50,
    maxVal: 3.50,
  },
  {
    key: "spectral_ratio",
    qubit: 5,
    name: "Spectral Power Ratio",
    symbol: "x_5",
    unit: "ratio",
    description: "High/low frequency spectral power band ratio (P[10-25Hz] / P[0.5-40Hz]).",
    isRetrospective: false,
    minVal: 0.01,
    maxVal: 0.65,
  },
];

// Presets for quick exploration
const SAMPLE_PRESETS = [
  {
    id: "REC200_B0105_N",
    label: "Beat 105 (Normal)",
    recordId: 200,
    type: "Normal (N)",
    variant: "emerald" as const,
    note: "Normal sinus rhythm beat with balanced pre/post RR intervals",
  },
  {
    id: "REC200_B0061_V",
    label: "Beat 61 (VEB)",
    recordId: 200,
    type: "Ventricular Ectopic (V)",
    variant: "magenta" as const,
    note: "Classic premature ventricular contraction with compensatory pause",
  },
  {
    id: "REC208_B2007_N",
    label: "Beat 2007 (Rec 208)",
    recordId: 208,
    type: "Normal (Shift FP)",
    variant: "amber" as const,
    note: "Record 208 tape session morphology shift false positive",
  },
  {
    id: "REC200_B0693_V",
    label: "Beat 693 (High-Amp V)",
    recordId: 200,
    type: "Ventricular Ectopic (V)",
    variant: "magenta" as const,
    note: "High peak-to-peak amplitude VEB with wide QRS complex",
  },
];

export const QuantumAiLab: React.FC<QuantumAiLabProps> = ({ onOpenDisclosures }) => {
  // Live API states
  const [isLive, setIsLive] = useState<boolean>(false);
  const [modelInfo, setModelInfo] = useState<BackendModelInfo | null>(null);
  const [hardwareOverview, setHardwareOverview] = useState<HardwareOverviewResult | null>(null);
  const [testSamples, setTestSamples] = useState<TestSampleItem[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>("REC200_B0105_N");
  const [activeFeatureKey, setActiveFeatureKey] = useState<string>("pre_rr");

  // Live forward pass execution state
  const [isRunningInference, setIsRunningInference] = useState<boolean>(false);
  const [livePrediction, setLivePrediction] = useState<PredictResult | null>(null);

  // Hardware Transpiler interactive tester
  const [selectedTarget, setSelectedTarget] = useState<"processor_b" | "processor_a">("processor_b");
  const [transpileResult, setTranspileResult] = useState<TranspileResult | null>(null);
  const [isTranspiling, setIsTranspiling] = useState<boolean>(false);

  // Load Model Info, Hardware Overview & Test Samples on Mount
  useEffect(() => {
    // 1. Model Info
    api.getModelInfo().then((res) => {
      if (res.data) {
        setModelInfo(res.data);
        if (res.isLive) setIsLive(true);
      }
    });

    // 2. Hardware Overview
    api.getHardwareOverview().then((res) => {
      if (res.data) {
        setHardwareOverview(res.data);
        setTranspileResult(res.data.processor_b);
      }
    });

    // 3. Test Samples
    api.getEcgSamples(50).then((res) => {
      if (res.data && res.data.samples.length > 0) {
        setTestSamples(res.data.samples);
      }
    });
  }, []);

  // Currently selected sample data
  const currentSample = useMemo(() => {
    return (
      testSamples.find((s) => s.segment_id === selectedSampleId) ||
      testSamples[0] ||
      null
    );
  }, [testSamples, selectedSampleId]);

  // Scaled features array: continuous values in [0, pi]
  const currentScaledFeatures = useMemo(() => {
    if (currentSample?.features_scaled && currentSample.features_scaled.length === 6) {
      return currentSample.features_scaled;
    }
    // Fallback normal beat values
    return [1.5853, 1.6448, 0.5298, 1.0927, 0.6123, 1.5051];
  }, [currentSample]);

  // Variational weights: 12 theta parameters
  const currentTheta = useMemo(() => {
    if (modelInfo?.optimal_theta && modelInfo.optimal_theta.length === 12) {
      return modelInfo.optimal_theta;
    }
    return FROZEN_MODEL.optimalTheta;
  }, [modelInfo]);

  // Handle Live Quantum Inference Execution
  const handleExecuteInference = async () => {
    if (!currentSample) return;
    setIsRunningInference(true);
    try {
      const res = await api.predict({
        sample_id: currentSample.segment_id,
        record_id: currentSample.record_id,
        features: {
          pre_rr: currentSample.features_raw.pre_rr,
          post_rr: currentSample.features_raw.post_rr,
          qrs_rms: currentSample.features_raw.qrs_rms,
          qrs_duration: currentSample.features_raw.qrs_duration,
          p2p_amplitude: currentSample.features_raw.p2p_amplitude,
          spectral_ratio: currentSample.features_raw.spectral_ratio,
          is_pre_scaled: false,
        },
      });
      if (res.data) {
        setLivePrediction(res.data);
      }
    } catch {
      // Retain previous state
    } finally {
      setIsRunningInference(false);
    }
  };

  // Handle Hardware Transpilation Trigger
  const handleTranspile = async (target: "processor_b" | "processor_a") => {
    setSelectedTarget(target);
    setIsTranspiling(true);
    try {
      const res = await api.transpile(target);
      if (res.data) {
        setTranspileResult(res.data);
      }
    } finally {
      setIsTranspiling(false);
    }
  };

  // Active expectation value and VEB probability
  const displayedPauliZ =
    livePrediction?.pauli_z_expectation ??
    currentSample?.pauli_z_expectation ??
    -0.3603;

  const displayedProbVeb =
    livePrediction?.probability_veb ??
    currentSample?.probability_veb ??
    0.3199;

  return (
    <div className="space-y-6">
      {/* Top Banner with Strict Simulation Guardrails */}
      <div className="p-4 rounded-xl bg-nexus-blue/10 border border-nexus-blue/30 flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-nexus-blue/20 text-nexus-cyan">
            <Atom className="w-5 h-5 animate-spin" style={{ animationDuration: "14s" }} />
          </div>
          <div>
            <div className="text-xs font-semibold text-white uppercase tracking-wider flex items-center gap-2 flex-wrap">
              <span>Quantum AI Lab: 6-Qubit Variational Quantum Classifier (VQC)</span>
              <StatusBadge variant="cyan" size="sm">Qiskit 2.5.2 · Qiskit Aer 0.17.2</StatusBadge>
              {isLive ? (
                <StatusBadge variant="cyan" size="sm">LIVE FASTAPI (/api/quantum)</StatusBadge>
              ) : (
                <StatusBadge variant="neutral" size="sm">VERIFIED FROZEN CHECKPOINT</StatusBadge>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Architecture: First-order RY feature encoding + RealAmplitudes linear entanglement (12 weights) · Checkpoint: <strong className="text-white font-mono">fold_1_seed_303</strong>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onOpenDisclosures}
            className="px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-xs font-mono text-slate-300 border border-white/10 flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Info className="w-3.5 h-3.5 text-nexus-cyan" />
            <span>Audit Guardrails</span>
          </button>
          <StatusBadge variant="amber" size="sm">
            100% Classical Simulation · No Physical QPU
          </StatusBadge>
        </div>
      </div>

      {/* =========================================================================
          SECTION A: QUANTUM CIRCUIT EXPLORER
         ========================================================================= */}
      <GlassCard
        variant="hud"
        showBrackets
        title={
          <div className="flex items-center justify-between w-full flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-nexus-cyan" />
              <span className="font-mono text-xs uppercase tracking-wider text-white">
                Quantum Circuit Explorer: 6-Qubit Feature Encoding & RealAmplitudes Ansatz
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              Active Input: <strong className="text-nexus-cyan">{selectedSampleId}</strong>
            </span>
          </div>
        }
        subtitle="Hardware-accurate algorithmic circuit representation. 6 RY feature rotations, 12 variational weights (reps=1, linear CX), and ensemble Pauli-Z measurement."
      >
        <div className="space-y-4 pt-1">
          {/* Interactive Circuit SVG Canvas */}
          <QuantumCircuitViewer
            scaledFeatures={currentScaledFeatures}
            optimalTheta={currentTheta}
            activeFeatureName={activeFeatureKey}
            onSelectFeature={(name) => setActiveFeatureKey(name)}
          />

          {/* Circuit Specifications Matrix */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-white/[0.06] font-mono text-xs">
            <div className="p-2.5 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase block">Encoding Layer</span>
              <span className="text-white font-bold text-sm mt-0.5 block">6 × RY(x_i)</span>
              <span className="text-[10px] text-nexus-cyan">Single-qubit rotation [0, π]</span>
            </div>

            <div className="p-2.5 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase block">Variational Ansatz</span>
              <span className="text-white font-bold text-sm mt-0.5 block">RealAmplitudes</span>
              <span className="text-[10px] text-violet-300">reps=1 · 12 Trainable θ</span>
            </div>

            <div className="p-2.5 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase block">Entanglement Topology</span>
              <span className="text-white font-bold text-sm mt-0.5 block">5 CX Gates</span>
              <span className="text-[10px] text-sky-400">Linear nearest-neighbor ladder</span>
            </div>

            <div className="p-2.5 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-400 uppercase block">Ensemble Observable</span>
              <span className="text-white font-bold text-sm mt-0.5 block">Ô = ⅙ ∑ Z_i</span>
              <span className="text-[10px] text-emerald-400">All 6 qubits measured</span>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* =========================================================================
          SECTION B: FEATURE ENCODING TO 6 QUBITS
         ========================================================================= */}
      <GlassCard
        variant="hud"
        showBrackets
        title={
          <div className="flex items-center justify-between w-full flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-nexus-cyan" />
              <span className="font-mono text-xs uppercase tracking-wider text-white">
                Biomarker Feature Mapping to [0, π] Bloch Sphere Rotations
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              MinMax Fitted on Dev Records (106, 119)
            </span>
          </div>
        }
        subtitle="Continuous MLII biomarkers scaled to rotation angles x_i ∈ [0, π]. Out-of-distribution values are strictly clamped at 0.0 or π."
      >
        <div className="space-y-4 pt-1">
          {/* Preset Sample Selector */}
          <div className="space-y-1.5">
            <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-amber-400" />
              <span>Select Benchmark Test Beat to Drive Circuit:</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {SAMPLE_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  onClick={() => {
                    setSelectedSampleId(preset.id);
                    setLivePrediction(null);
                  }}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-mono border transition-all flex items-center gap-2 cursor-pointer ${
                    selectedSampleId === preset.id
                      ? "bg-nexus-cyan/20 border-nexus-cyan text-white shadow-glow-cyan-sm"
                      : "bg-black/40 border-white/10 text-slate-400 hover:text-white hover:border-white/20"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      preset.variant === "magenta"
                        ? "bg-pink-500"
                        : preset.variant === "amber"
                        ? "bg-amber-400"
                        : "bg-emerald-400"
                    }`}
                  />
                  <span>{preset.label}</span>
                  <span className="text-[10px] text-slate-500 font-normal">[{preset.type}]</span>
                </button>
              ))}
            </div>
          </div>

          {/* 6 Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {FEATURE_DEFINITIONS.map((feat) => {
              const rawVal =
                currentSample?.features_raw?.[feat.key] ??
                (feat.isRetrospective ? 0.7056 : 0.675);
              const scaledAngle = currentScaledFeatures[feat.qubit];
              const isSelected = activeFeatureKey === feat.key;
              const angleDeg = ((scaledAngle / Math.PI) * 180).toFixed(1);
              const isClipped = scaledAngle <= 0.0001 || scaledAngle >= Math.PI - 0.0001;

              return (
                <div
                  key={feat.key}
                  onClick={() => setActiveFeatureKey(feat.key)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? "bg-nexus-cyan/10 border-nexus-cyan shadow-glow-cyan-sm"
                      : "bg-nexus-card border-white/10 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-nexus-cyan font-bold">
                      Qubit q[{feat.qubit}] · {feat.symbol}
                    </span>
                    {feat.isRetrospective ? (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        * Retrospective
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono text-slate-400">{feat.unit}</span>
                    )}
                  </div>

                  <div className="mt-1">
                    <div className="text-xs font-bold text-white">{feat.name}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5 leading-tight">
                      {feat.description}
                    </div>
                  </div>

                  {/* Raw vs Encoded Angle Row */}
                  <div className="mt-3 pt-2 border-t border-white/[0.06] grid grid-cols-2 gap-2 text-xs font-mono">
                    <div>
                      <span className="text-[9px] text-slate-500 block uppercase">Raw Value</span>
                      <span className="text-white font-bold">
                        {typeof rawVal === "number" ? rawVal.toFixed(4) : rawVal}
                      </span>
                    </div>
                    <div>
                      <span className="text-[9px] text-slate-500 block uppercase">Angle x_i [0, π]</span>
                      <span className="text-emerald-400 font-bold">
                        {scaledAngle.toFixed(4)} rad
                      </span>
                    </div>
                  </div>

                  {/* Bloch Sphere Angular Gauge Bar */}
                  <div className="mt-2.5">
                    <div className="flex items-center justify-between text-[9px] font-mono text-slate-500 mb-1">
                      <span>0.0 rad (0°)</span>
                      <span className="text-nexus-cyan font-bold">{angleDeg}°</span>
                      <span>π rad (180°)</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden border border-white/10">
                      <div
                        className="h-full bg-gradient-to-r from-nexus-cyan to-emerald-400 rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(100, Math.max(0, (scaledAngle / Math.PI) * 100))}%` }}
                      />
                    </div>
                  </div>

                  {/* Clipping Alert if out of bounds */}
                  {isClipped && (
                    <div className="mt-2 text-[10px] font-mono text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3 shrink-0" />
                      <span>Boundary clamp active at [0, π] limit</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Mandatory Feature Disclosure Alert */}
          <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[11px] font-mono text-amber-300 flex items-center gap-2">
            <Info className="w-4 h-4 shrink-0 text-amber-400" />
            <span>
              <strong>Scientific Disclosure:</strong> Feature <strong>post_rr</strong> measures the distance to the succeeding R-peak (R_{`{i+1}`} - R_i) and is strictly an offline, retrospective feature. It is not available in causal real-time streaming without buffering one future beat.
            </span>
          </div>
        </div>
      </GlassCard>

      {/* =========================================================================
          SECTION C & D: VQC MATHEMATICS & IDEAL VS NOISY BENCHMARKS
         ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 6 cols: Variational Quantum Classifier Math & Checkpoint Provenance */}
        <div className="lg:col-span-6 space-y-4">
          <GlassCard
            variant="hud"
            showBrackets
            title={
              <div className="flex items-center gap-2">
                <Binary className="w-4 h-4 text-nexus-cyan" />
                <span className="font-mono text-xs uppercase tracking-wider text-white">
                  VQC Observable & Probability Mapping
                </span>
              </div>
            }
            subtitle="Mathematical formulation connecting unitary statevector expectation to clinical classification probability."
          >
            <div className="space-y-4 pt-1 font-mono text-xs">
              {/* Observable Formula Box */}
              <div className="p-3.5 rounded-xl bg-black/60 border border-nexus-cyan/30 space-y-2">
                <div className="flex items-center justify-between text-slate-400 text-[10px] uppercase">
                  <span>Ensemble Pauli-Z Observable</span>
                  <span className="text-nexus-cyan">6-Qubit Symmetrized Average</span>
                </div>
                <div className="text-lg font-bold text-white text-center py-1">
                  Ô = ⅙ ( Z_0 + Z_1 + Z_2 + Z_3 + Z_4 + Z_5 )
                </div>
                <div className="text-[10px] text-slate-400 text-center leading-relaxed">
                  Averaging Pauli-Z projections over all 6 qubits suppresses individual qubit readout errors and produces expectation value ⟨Ô⟩ ∈ [-1.0, +1.0].
                </div>
              </div>

              {/* Probability Mapping Formula Box */}
              <div className="p-3.5 rounded-xl bg-black/60 border border-emerald-500/30 space-y-2">
                <div className="flex items-center justify-between text-slate-400 text-[10px] uppercase">
                  <span>VEB Probability Mapping</span>
                  <span className="text-emerald-400">Affine Decision Threshold</span>
                </div>
                <div className="text-lg font-bold text-white text-center py-1">
                  P(VEB) = ( ⟨Ô⟩ + 1 ) / 2
                </div>
                <div className="text-[10px] text-slate-400 text-center leading-relaxed">
                  ⟨Ô⟩ = -1.0 maps to P(VEB) = 0.0 (Pure Normal) · ⟨Ô⟩ = +1.0 maps to P(VEB) = 1.0 (Pure VEB). Decision threshold τ = 0.50 corresponds to ⟨Ô⟩ = 0.0.
                </div>
              </div>

              {/* Live Quantum Forward Pass Action */}
              <div className="p-3 rounded-xl bg-nexus-card border border-white/10 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-white block">
                      Live Forward Pass (Selected: {selectedSampleId})
                    </span>
                    <span className="text-[10px] text-slate-400">
                      Executes Qiskit StatevectorEstimator forward pass
                    </span>
                  </div>
                  <button
                    onClick={handleExecuteInference}
                    disabled={isRunningInference}
                    className="px-3 py-1.5 rounded-lg bg-nexus-cyan/20 hover:bg-nexus-cyan/30 text-nexus-cyan border border-nexus-cyan/50 text-xs flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                  >
                    {isRunningInference ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Zap className="w-3.5 h-3.5" />
                    )}
                    <span>Run Forward Pass</span>
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/[0.06]">
                  <div className="p-2 rounded bg-black/40">
                    <span className="text-[10px] text-slate-500 block uppercase">⟨Ô⟩ Expectation</span>
                    <span className="text-base font-bold text-white">
                      {(displayedPauliZ >= 0 ? "+" : "") + displayedPauliZ.toFixed(4)}
                    </span>
                  </div>
                  <div className="p-2 rounded bg-black/40">
                    <span className="text-[10px] text-slate-500 block uppercase">P(VEB) Probability</span>
                    <span
                      className={`text-base font-bold ${
                        displayedProbVeb >= 0.5 ? "text-pink-400" : "text-emerald-400"
                      }`}
                    >
                      {(displayedProbVeb * 100).toFixed(2)}%
                    </span>
                  </div>
                </div>

                {livePrediction && (
                  <div className="text-[10px] text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Forward pass executed via live FastAPI backend ({livePrediction.execution_type})</span>
                  </div>
                )}
              </div>

              {/* Frozen Checkpoint Provenance */}
              <div className="p-3 rounded-xl bg-black/40 border border-white/10 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-white uppercase">
                    Frozen Checkpoint: fold_1_seed_303
                  </span>
                  <StatusBadge variant="cyan" size="sm">Optimal LORO</StatusBadge>
                </div>
                <div className="text-[10px] text-slate-400 leading-relaxed">
                  Trained on Record 106 (100 beats), validated on Record 119 (100 beats). Selected via composite validation score (S = 0.9592). Model weights are frozen; no retraining is performed.
                </div>

                {/* 12 Trainable Weights Drawer */}
                <div className="pt-2">
                  <span className="text-[10px] text-slate-500 uppercase block mb-1">
                    12 Variational Weights (θ_0 .. θ_11 in radians):
                  </span>
                  <div className="grid grid-cols-6 gap-1 text-[9px] text-center">
                    {currentTheta.map((th, idx) => (
                      <div key={idx} className="p-1 rounded bg-white/[0.03] border border-white/5">
                        <span className="text-slate-500 block">θ_{idx}</span>
                        <span className="text-slate-200 font-bold">{th.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Right 6 cols: Ideal vs Noisy Simulation Comparative Benchmark */}
        <div className="lg:col-span-6 space-y-4">
          <GlassCard
            variant="hud"
            showBrackets
            title={
              <div className="flex items-center justify-between w-full flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  <span className="font-mono text-xs uppercase tracking-wider text-white">
                    Ideal vs Noisy Simulation (Held-Out Benchmark)
                  </span>
                </div>
                <StatusBadge variant="neutral" size="sm">N = 100 Test Beats</StatusBadge>
              </div>
            }
            subtitle="Audited evaluation results on held-out test cohort (Records 200 & 208). Comparing ideal statevector vs AerSimulator under depolarizing and readout noise."
          >
            <div className="space-y-4 pt-1">
              {/* Comparative Metrics Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 text-[10px] uppercase">
                      <th className="py-2 px-2">Metric</th>
                      <th className="py-2 px-2 text-nexus-cyan">Ideal VQC (Statevector)</th>
                      <th className="py-2 px-2 text-amber-300">Noisy VQC (AerSimulator)</th>
                      <th className="py-2 px-2 text-right">Delta</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {[
                      { name: "Accuracy", ideal: "76.0%", noisy: "77.0%", delta: "+1.0%", pos: true },
                      { name: "Sensitivity (VEB Recall)", ideal: "100.0%", noisy: "100.0%", delta: "0.0%", pos: null },
                      { name: "Specificity (Normal)", ideal: "52.0%", noisy: "54.0%", delta: "+2.0%", pos: true },
                      { name: "Precision", ideal: "67.57%", noisy: "68.49%", delta: "+0.92%", pos: true },
                      { name: "F1 Score", ideal: "0.8065", noisy: "0.8130", delta: "+0.0065", pos: true },
                      { name: "ROC-AUC", ideal: "0.9988", noisy: "0.9984", delta: "-0.0004", pos: false },
                    ].map((row) => (
                      <tr key={row.name} className="hover:bg-white/[0.02]">
                        <td className="py-2 px-2 font-bold text-slate-300">{row.name}</td>
                        <td className="py-2 px-2 text-nexus-cyan font-bold">{row.ideal}</td>
                        <td className="py-2 px-2 text-amber-300 font-bold">{row.noisy}</td>
                        <td
                          className={`py-2 px-2 text-right font-bold ${
                            row.pos === true
                              ? "text-emerald-400"
                              : row.pos === false
                              ? "text-pink-400"
                              : "text-slate-500"
                          }`}
                        >
                          {row.delta}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Side-by-Side Confusion Matrices */}
              <div className="grid grid-cols-2 gap-3 pt-2">
                {/* Ideal Matrix */}
                <div className="p-3 rounded-xl bg-black/50 border border-nexus-cyan/30 text-center font-mono">
                  <span className="text-[10px] text-nexus-cyan uppercase font-bold block mb-2">
                    Ideal VQC Confusion Matrix
                  </span>
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30">
                      <span className="text-[9px] text-slate-400 block">TN (Normal)</span>
                      <span className="text-base font-bold text-emerald-400">26</span>
                    </div>
                    <div className="p-2 rounded bg-pink-500/10 border border-pink-500/30">
                      <span className="text-[9px] text-slate-400 block">FP</span>
                      <span className="text-base font-bold text-pink-400">24</span>
                    </div>
                    <div className="p-2 rounded bg-slate-800/40 border border-white/5">
                      <span className="text-[9px] text-slate-400 block">FN (Missed)</span>
                      <span className="text-base font-bold text-white">0</span>
                    </div>
                    <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30">
                      <span className="text-[9px] text-slate-400 block">TP (VEB)</span>
                      <span className="text-base font-bold text-emerald-400">50</span>
                    </div>
                  </div>
                  <div className="text-[9px] text-slate-500 mt-2">76 Correct / 24 FP</div>
                </div>

                {/* Noisy Matrix */}
                <div className="p-3 rounded-xl bg-black/50 border border-amber-500/30 text-center font-mono">
                  <span className="text-[10px] text-amber-300 uppercase font-bold block mb-2">
                    Noisy VQC Matrix (4096 Shots)
                  </span>
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30">
                      <span className="text-[9px] text-slate-400 block">TN (Normal)</span>
                      <span className="text-base font-bold text-emerald-400">27</span>
                    </div>
                    <div className="p-2 rounded bg-pink-500/10 border border-pink-500/30">
                      <span className="text-[9px] text-slate-400 block">FP</span>
                      <span className="text-base font-bold text-pink-400">23</span>
                    </div>
                    <div className="p-2 rounded bg-slate-800/40 border border-white/5">
                      <span className="text-[9px] text-slate-400 block">FN (Missed)</span>
                      <span className="text-base font-bold text-white">0</span>
                    </div>
                    <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30">
                      <span className="text-[9px] text-slate-400 block">TP (VEB)</span>
                      <span className="text-base font-bold text-emerald-400">50</span>
                    </div>
                  </div>
                  <div className="text-[9px] text-slate-500 mt-2">77 Correct / 23 FP</div>
                </div>
              </div>

              {/* Research Insight Note */}
              <div className="p-2.5 rounded-lg bg-white/[0.03] border border-white/10 text-[11px] font-mono text-slate-300 leading-relaxed">
                <span className="text-nexus-cyan font-bold">Research Finding:</span> Under depolarizing and readout noise (4096 shots), exactly 1 borderline sample shifted from False Positive to True Negative, slightly raising accuracy to 77.0% while preserving 100% sensitivity (0 false negatives out of 50 VEB beats).
              </div>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* =========================================================================
          SECTION E & F: SIMULATION NOISE SPEC & QUANTUM HARDWARE AWARENESS
         ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 5 cols: Section E - Simulation Noise Model Configuration */}
        <div className="lg:col-span-5 space-y-4">
          <GlassCard
            variant="hud"
            showBrackets
            title={
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-amber-400" />
                <span className="font-mono text-xs uppercase tracking-wider text-white">
                  Simulation Noise Model Configuration
                </span>
              </div>
            }
            subtitle="Qiskit AerSimulator execution parameters. Modeled on typical superconducting device noise characteristics."
          >
            <div className="space-y-3 pt-1 font-mono text-xs">
              <div className="space-y-2">
                <div className="p-2.5 rounded-lg bg-black/40 border border-white/10 flex items-center justify-between">
                  <span className="text-slate-400">Simulator Engine:</span>
                  <span className="text-white font-bold">Qiskit Aer 0.17.2</span>
                </div>

                <div className="p-2.5 rounded-lg bg-black/40 border border-white/10 flex items-center justify-between">
                  <span className="text-slate-400">Measurement Shots:</span>
                  <span className="text-nexus-cyan font-bold">4,096 shots / pass</span>
                </div>

                <div className="p-2.5 rounded-lg bg-black/40 border border-white/10 flex items-center justify-between">
                  <span className="text-slate-400">1-Qubit Depolarizing (p_1q):</span>
                  <span className="text-slate-200">0.001 (0.10%)</span>
                </div>

                <div className="p-2.5 rounded-lg bg-black/40 border border-white/10 flex items-center justify-between">
                  <span className="text-slate-400">2-Qubit CX Depolarizing (p_2q):</span>
                  <span className="text-slate-200">0.005 (0.50%)</span>
                </div>

                <div className="p-2.5 rounded-lg bg-black/40 border border-white/10 flex items-center justify-between">
                  <span className="text-slate-400">Readout Bit-Flip (p_ro):</span>
                  <span className="text-slate-200">0.010 (1.00%)</span>
                </div>
              </div>

              {/* Explicit Simulation Boundary Disclosures */}
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[10px] text-amber-300 space-y-1.5 leading-relaxed">
                <div className="font-bold flex items-center gap-1 text-amber-400 uppercase">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Unmodeled Noise Channels Disclosure:</span>
                </div>
                <ul className="list-disc list-inside space-y-0.5 text-slate-300">
                  <li><strong>Thermal relaxation (T1 / T2*):</strong> NOT simulated in this benchmark.</li>
                  <li><strong>Crosstalk & leakage:</strong> Not modeled in AerSimulator pass.</li>
                  <li><strong>Pulse distortions & drift:</strong> Ideal microwave envelope assumed.</li>
                </ul>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Right 7 cols: Section F - Quantum Hardware Topology Awareness */}
        <div className="lg:col-span-7 space-y-4">
          <GlassCard
            variant="hud"
            showBrackets
            title={
              <div className="flex items-center justify-between w-full flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-nexus-cyan" />
                  <span className="font-mono text-xs uppercase tracking-wider text-white">
                    Hardware Awareness: Processor A vs Processor B
                  </span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">
                  Transpilation Target Comparison
                </span>
              </div>
            }
            subtitle={
              hardwareOverview
                ? `${hardwareOverview.execution_mode} · Target: ${hardwareOverview.target_hardware}`
                : "Evaluation of hardware connectivity constraints. Demonstrates why a 5-qubit linear baseline fails while 9-qubit heavy-hex embeds natively."
            }
          >
            <div className="space-y-4 pt-1 font-mono text-xs">
              {/* Target Selector Tabs */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleTranspile("processor_b")}
                  className={`flex-1 p-2.5 rounded-lg border text-left transition-all cursor-pointer ${
                    selectedTarget === "processor_b"
                      ? "bg-nexus-cyan/20 border-nexus-cyan text-white shadow-glow-cyan-sm"
                      : "bg-black/40 border-white/10 text-slate-400 hover:text-white"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs flex items-center gap-1.5">
                      <span>Processor B (Target)</span>
                      {isTranspiling && selectedTarget === "processor_b" && (
                        <RefreshCw className="w-3 h-3 animate-spin text-nexus-cyan" />
                      )}
                    </span>
                    <StatusBadge variant="cyan" size="sm">9 Qubits</StatusBadge>
                  </div>
                  <div className="text-[10px] text-emerald-400 mt-1">
                    Native Embedding · 0 SWAP Overhead
                  </div>
                </button>

                <button
                  onClick={() => handleTranspile("processor_a")}
                  className={`flex-1 p-2.5 rounded-lg border text-left transition-all cursor-pointer ${
                    selectedTarget === "processor_a"
                      ? "bg-pink-500/20 border-pink-500 text-white shadow-[0_0_12px_rgba(236,72,153,0.3)]"
                      : "bg-black/40 border-white/10 text-slate-400 hover:text-white"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs flex items-center gap-1.5">
                      <span>Processor A (Baseline)</span>
                      {isTranspiling && selectedTarget === "processor_a" && (
                        <RefreshCw className="w-3 h-3 animate-spin text-pink-400" />
                      )}
                    </span>
                    <StatusBadge variant="magenta" size="sm">5 Qubits</StatusBadge>
                  </div>
                  <div className="text-[10px] text-pink-400 mt-1">
                    Capacity Overflow · CircuitTooWide
                  </div>
                </button>
              </div>

              {/* Transpilation Result Card */}
              {transpileResult && (
                <div className="p-3.5 rounded-xl bg-black/60 border border-white/10 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-sm">
                      {transpileResult.processor_name} Transpilation Summary
                    </span>
                    {transpileResult.success ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                        SUCCESS (Depth {transpileResult.depth})
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-pink-500/20 text-pink-400 border border-pink-500/40">
                        {transpileResult.error_type || "CAPACITY OVERFLOW"}
                      </span>
                    )}
                  </div>

                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    {transpileResult.message}
                  </p>

                  {/* Transpilation Metrics Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-white/[0.06] text-center">
                    <div className="p-2 rounded bg-white/[0.03]">
                      <span className="text-[9px] text-slate-500 block uppercase">Physical Qubits</span>
                      <span className="text-white font-bold">{transpileResult.physical_qubits}</span>
                    </div>

                    <div className="p-2 rounded bg-white/[0.03]">
                      <span className="text-[9px] text-slate-500 block uppercase">Depth (No Meas)</span>
                      <span className="text-nexus-cyan font-bold">
                        {transpileResult.depth ?? "N/A"}
                      </span>
                    </div>

                    <div className="p-2 rounded bg-white/[0.03]">
                      <span className="text-[9px] text-slate-500 block uppercase">2Q CX Count</span>
                      <span className="text-violet-300 font-bold">
                        {transpileResult.cx_count ?? "N/A"}
                      </span>
                    </div>

                    <div className="p-2 rounded bg-white/[0.03]">
                      <span className="text-[9px] text-slate-500 block uppercase">SWAP Overhead</span>
                      <span className="text-emerald-400 font-bold">
                        {transpileResult.swap_count !== null ? `${transpileResult.swap_count} SWAP` : "N/A"}
                      </span>
                    </div>
                  </div>

                  {/* Physical Layout Embedding Pill */}
                  {transpileResult.physical_layout && (
                    <div className="flex items-center justify-between text-[10px] pt-1 text-slate-400">
                      <span>Physical Layout Mapping:</span>
                      <span className="text-nexus-cyan font-bold">
                        [{transpileResult.physical_layout.join(", ")}]
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Strict Hardware Non-Fabrication Disclosure */}
              <div className="p-2.5 rounded-lg bg-nexus-blue/10 border border-nexus-blue/30 text-[10px] text-slate-300 leading-relaxed">
                <strong className="text-nexus-cyan">Hardware Execution Disclosure:</strong> Transpilation maps the logical circuit graph to a physical coupling architecture, but does <em>not</em> execute on cryogenic quantum hardware. No physical QPU jobs, device calibrations, coherence measurements, or quantum execution times are claimed or fabricated.
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
};
