import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  ShieldCheck,
  ShieldAlert,
  Cpu,
  Layers,
  Sparkles,
  Terminal,
  Zap,
  RefreshCw,
  Database,
  ArrowRight,
  BarChart3,
  Info,
} from "lucide-react";
import { GlassCard } from "../components/ui/GlassCard";
import { StatusBadge } from "../components/ui/StatusBadge";
import { FROZEN_MODEL } from "../types/scientific";
import type { AppRoute } from "../types/navigation";
import {
  api,
  type PredictResult,
  type BackendHealth,
} from "../services/api";

interface CommandCenterProps {
  onNavigate: (route: AppRoute) => void;
  onOpenDisclosures: () => void;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({
  onNavigate,
  onOpenDisclosures,
}) => {
  // Live State & API Telemetry
  const [runningSampleIndex, setRunningSampleIndex] = useState<number | null>(null);
  const [livePredictions, setLivePredictions] = useState<Record<number, PredictResult>>({});
  const [liveStatus, setLiveStatus] = useState<string | null>(null);
  const [isLiveApi, setIsLiveApi] = useState<boolean>(false);
  const [apiLatencyMs, setApiLatencyMs] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [healthData, setHealthData] = useState<BackendHealth | null>(null);

  // Load backend status and overview
  const loadSystemData = useCallback(async () => {
    setIsLoading(true);
    const start = performance.now();
    try {
      const [overviewRes, healthRes] = await Promise.all([
        api.getOverview(),
        api.checkHealth(),
      ]);
      const elapsed = Math.round(performance.now() - start);
      setApiLatencyMs(elapsed);

      if (overviewRes.isLive && overviewRes.data) {
        setIsLiveApi(true);
      } else {
        setIsLiveApi(false);
      }

      if (healthRes.isOnline && healthRes.data) {
        setHealthData(healthRes.data);
      }
    } catch {
      setIsLiveApi(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSystemData();
  }, [loadSystemData]);

  // Sample inference handler
  const handleRunInference = async (
    sampleIdx: number,
    sampleId: string,
    recordId: number,
    features: {
      pre_rr: number;
      post_rr: number;
      qrs_rms: number;
      qrs_duration: number;
      p2p_amplitude: number;
      spectral_ratio: number;
    }
  ) => {
    setRunningSampleIndex(sampleIdx);
    setLiveStatus(`Evaluating Qiskit StatevectorEstimator forward-pass on Sample ${sampleIdx}...`);
    try {
      const res = await api.predict({
        sample_id: sampleId,
        record_id: recordId,
        features,
      });
      setLivePredictions((prev) => ({ ...prev, [sampleIdx]: res.data }));
      setLiveStatus(
        res.isLive
          ? `Verified via live FastAPI (⟨Z⟩ = ${res.data.pauli_z_expectation.toFixed(4)}, P(VEB) = ${res.data.probability_veb.toFixed(4)})`
          : `Verified offline via frozen checkpoint fold_1_seed_303`
      );
    } catch {
      setLiveStatus("Execution error encountered; audited fallback value preserved.");
    } finally {
      setRunningSampleIndex(null);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      {/* ────────────────────────────────────────────────────────────── */}
      {/* 1. EXECUTIVE OVERVIEW                                          */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10 relative overflow-hidden bg-gradient-to-br from-nexus-navy/90 via-nexus-surface/80 to-nexus-navy/95">
        <div className="absolute top-0 right-0 w-96 h-96 bg-nexus-cyan/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-6 pb-6 border-b border-white/10 relative z-10">
          <div>
            <div className="flex items-center gap-2.5 mb-2 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-wider font-semibold uppercase bg-nexus-cyan/15 text-nexus-cyan border border-nexus-cyan/30 flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 animate-pulse" />
                IBM Quantum Qiskit Fall Fest 2026 • Project Q
              </span>
              <StatusBadge
                variant={isLiveApi ? "cyan" : "neutral"}
                pulse={isLiveApi}
              >
                {isLiveApi
                  ? `Live Backend Connected (${apiLatencyMs}ms REST)`
                  : "Artifact-Backed Offline Fallback"}
              </StatusBadge>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-medium bg-amber-500/10 text-amber-300 border border-amber-500/25">
                Record-Level Separation (Records 106, 119 Dev | 200, 208 Test)
              </span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight flex items-center gap-3">
              NEXUS-OPS Command Center
              <span className="text-xs font-mono font-normal text-slate-400 px-2 py-0.5 rounded bg-white/5 border border-white/10">
                Checkpoint: {FROZEN_MODEL.runId}
              </span>
            </h1>
            <p className="text-slate-400 text-sm mt-1 max-w-3xl leading-relaxed">
              Unified executive research dashboard for the PS-Q1 Quantum Biomedical Signal Classifier.
              Synthesizing deterministic electrocardiogram beat intelligence, 6-qubit variational quantum machine
              learning, hardware transpilation constraints, and rigorous empirical validation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadSystemData}
              disabled={isLoading}
              className="px-3.5 py-2 rounded-xl text-xs font-mono bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              title="Synchronize platform telemetry"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-nexus-cyan" : ""}`} />
              Sync
            </button>
            <button
              onClick={onOpenDisclosures}
              className="px-3.5 py-2 rounded-xl text-xs font-mono bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 flex items-center gap-2 transition-all"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Disclosures
            </button>
          </div>
        </div>

        {/* Top Executive KPI Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5 relative z-10">
          <div className="p-3.5 rounded-xl bg-black/30 border border-white/5">
            <div className="text-[10px] font-mono text-slate-400 uppercase">FROZEN CHECKPOINT</div>
            <div className="text-lg font-bold font-mono text-white mt-1 truncate">{FROZEN_MODEL.runId}</div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">Fold 1 • Seed 303</div>
          </div>

          <div className="p-3.5 rounded-xl bg-black/30 border border-white/5">
            <div className="text-[10px] font-mono text-slate-400 uppercase">VQC TEST ACCURACY</div>
            <div className="text-lg font-bold font-mono text-white mt-1">76.00%</div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">76 / 100 beats (Ideal)</div>
          </div>

          <div className="p-3.5 rounded-xl bg-black/30 border border-emerald-500/20">
            <div className="text-[10px] font-mono text-emerald-400 uppercase">VQC SENSITIVITY</div>
            <div className="text-lg font-bold font-mono text-emerald-300 mt-1">100.00%</div>
            <div className="text-[10px] text-emerald-400/80 font-mono mt-0.5">50 / 50 VEBs (0 FN)</div>
          </div>

          <div className="p-3.5 rounded-xl bg-black/30 border border-white/5">
            <div className="text-[10px] font-mono text-slate-400 uppercase">VQC SPECIFICITY</div>
            <div className="text-lg font-bold font-mono text-white mt-1">52.00%</div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">26 / 50 Normal TN</div>
          </div>

          <div className="p-3.5 rounded-xl bg-black/30 border border-amber-500/20">
            <div className="text-[10px] font-mono text-amber-400 uppercase">VQC ROC-AUC</div>
            <div className="text-lg font-bold font-mono text-amber-300 mt-1">0.9988</div>
            <div className="text-[10px] text-amber-400/80 font-mono mt-0.5">0.9984 under Aer noise</div>
          </div>

          <div className="p-3.5 rounded-xl bg-black/30 border border-white/5">
            <div className="text-[10px] font-mono text-slate-400 uppercase">CLASSICAL LR BASELINE</div>
            <div className="text-lg font-bold font-mono text-white mt-1">92.00%</div>
            <div className="text-[10px] text-slate-400 font-mono mt-0.5">Trained on 200 samples</div>
          </div>
        </div>
      </GlassCard>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* 2 & 3. DATASET INTELLIGENCE & ECG MONITORING                  */}
      {/* ────────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Section 2: Dataset Intelligence Snapshot (5 cols) */}
        <div className="lg:col-span-5">
          <GlassCard className="p-6 border border-white/10 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Database className="w-4 h-4 text-nexus-cyan" />
                  Dataset Intelligence Snapshot
                </h3>
                <button
                  onClick={() => onNavigate("dataset-audit")}
                  className="text-xs text-nexus-cyan hover:underline font-mono flex items-center gap-1"
                >
                  Explore <ArrowRight className="w-3 h-3" />
                </button>
              </div>
              <p className="text-xs text-slate-400 mb-5 leading-relaxed">
                MIT-BIH Arrhythmia Database (PhysioNet v1.0.0) partitioned into development and held-out test sets under strict record-level separation.
              </p>

              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 rounded-lg bg-black/30 border border-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Total Beat Segments:</span>
                  <span className="text-white font-bold">300 (150 Normal / 150 VEB)</span>
                </div>
                <div className="p-3 rounded-lg bg-black/30 border border-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Signal Points Audited:</span>
                  <span className="text-emerald-400 font-bold">108,000 (0 NaN · 0 Inf · 0 Nulls)</span>
                </div>
                <div className="p-3 rounded-lg bg-black/30 border border-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Exclusion Registry:</span>
                  <span className="text-amber-300 font-bold">867 Non-Target Beats Logged</span>
                </div>
                <div className="p-3 rounded-lg bg-black/30 border border-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Test Feature Clamping:</span>
                  <span className="text-amber-300 font-bold">14 / 600 values (13 / 100 beats)</span>
                </div>
              </div>
            </div>

            <div className="mt-5 p-3 rounded-lg bg-white/5 border border-white/10 text-[11px] text-slate-400 font-mono flex items-center justify-between">
              <span>Partitioning Isolation:</span>
              <span className="text-slate-200">Dev (106, 119) | Test (200, 208)</span>
            </div>
          </GlassCard>
        </div>

        {/* Section 3: ECG Monitoring & Sample Forward-Pass (7 cols) */}
        <div className="lg:col-span-7">
          <GlassCard className="p-6 border border-white/10 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Activity className="w-4 h-4 text-nexus-cyan" />
                    ECG Monitoring & Verified Sample Queue
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Continuous Modified Lead II (MLII) at 360 Hz. 360-sample windowing (144 pre-R / 216 post-R).
                  </p>
                </div>
                <button
                  onClick={() => onNavigate("ecg-intelligence")}
                  className="text-xs text-nexus-cyan hover:underline font-mono flex items-center gap-1 shrink-0"
                >
                  Explore <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {liveStatus && (
                <div className="mb-4 p-2.5 rounded-lg bg-nexus-cyan/10 border border-nexus-cyan/30 text-[11px] font-mono text-nexus-cyan flex items-center justify-between">
                  <span>{liveStatus}</span>
                  {runningSampleIndex !== null && <RefreshCw className="w-3 h-3 animate-spin shrink-0" />}
                </div>
              )}

              {/* Sample 1: Normal Sample 14 */}
              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-black/30 border border-white/10 hover:border-emerald-500/40 transition-colors">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-semibold text-white">Sample 14 (Record 200)</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() =>
                          handleRunInference(14, "REC200_B0828_N", 200, {
                            pre_rr: 0.9056,
                            post_rr: 0.975,
                            qrs_rms: 0.5073,
                            qrs_duration: 0.0528,
                            p2p_amplitude: 1.605,
                            spectral_ratio: 0.2191,
                          })
                        }
                        disabled={runningSampleIndex === 14}
                        className="px-2 py-0.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-[10px] font-mono text-emerald-300 border border-emerald-500/30 flex items-center gap-1"
                      >
                        {runningSampleIndex === 14 ? <RefreshCw className="w-2.5 h-2.5 animate-spin" /> : <Zap className="w-2.5 h-2.5" />}
                        Run Live VQC
                      </button>
                      <StatusBadge variant="emerald" size="sm">Normal (N)</StatusBadge>
                    </div>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                    <div>Pauli-Z ⟨Z⟩: <span className="text-white">{livePredictions[14]?.pauli_z_expectation.toFixed(4) || "-0.3603"}</span></div>
                    <div>P(VEB): <span className="text-emerald-400">{livePredictions[14]?.probability_veb.toFixed(4) || "0.3199"}</span></div>
                  </div>
                </div>

                {/* Sample 2: VEB Sample 11 */}
                <div className="p-3 rounded-xl bg-black/30 border border-white/10 hover:border-pink-500/40 transition-colors">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-semibold text-white">Sample 11 (Record 200)</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() =>
                          handleRunInference(11, "REC200_B0693_V", 200, {
                            pre_rr: 0.5056,
                            post_rr: 0.9278,
                            qrs_rms: 1.1176,
                            qrs_duration: 0.0694,
                            p2p_amplitude: 2.945,
                            spectral_ratio: 0.0908,
                          })
                        }
                        disabled={runningSampleIndex === 11}
                        className="px-2 py-0.5 rounded bg-pink-500/10 hover:bg-pink-500/20 text-[10px] font-mono text-pink-300 border border-pink-500/30 flex items-center gap-1"
                      >
                        {runningSampleIndex === 11 ? <RefreshCw className="w-2.5 h-2.5 animate-spin" /> : <Zap className="w-2.5 h-2.5" />}
                        Run Live VQC
                      </button>
                      <StatusBadge variant="magenta" size="sm">VEB (Class V)</StatusBadge>
                    </div>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                    <div>Pauli-Z ⟨Z⟩: <span className="text-white">+{livePredictions[11]?.pauli_z_expectation.toFixed(4) || "+0.4774"}</span></div>
                    <div>P(VEB): <span className="text-pink-400">{livePredictions[11]?.probability_veb.toFixed(4) || "0.7387"}</span></div>
                  </div>
                </div>

                {/* Sample 3: Morphology Shift Sample 82 */}
                <div className="p-3 rounded-xl bg-black/30 border border-amber-500/30 hover:border-amber-500/50 transition-colors">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-semibold text-white">Sample 82 (Record 208)</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() =>
                          handleRunInference(82, "REC208_B2007_N", 208, {
                            pre_rr: 0.4778,
                            post_rr: 0.4917,
                            qrs_rms: 0.5664,
                            qrs_duration: 0.0333,
                            p2p_amplitude: 2.775,
                            spectral_ratio: 0.1861,
                          })
                        }
                        disabled={runningSampleIndex === 82}
                        className="px-2 py-0.5 rounded bg-amber-500/10 hover:bg-amber-500/20 text-[10px] font-mono text-amber-300 border border-amber-500/30 flex items-center gap-1"
                      >
                        {runningSampleIndex === 82 ? <RefreshCw className="w-2.5 h-2.5 animate-spin" /> : <Zap className="w-2.5 h-2.5" />}
                        Run Live VQC
                      </button>
                      <StatusBadge variant="amber" size="sm">False Positive (Shift)</StatusBadge>
                    </div>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                    <div>True: <span className="text-white">Normal</span> | Pred: <span className="text-amber-400">VEB (FP)</span></div>
                    <div>P(VEB): <span className="text-amber-400">{livePredictions[82]?.probability_veb.toFixed(4) || "0.5638"}</span></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-4 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300/90 font-sans flex items-start gap-2">
              <Info className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              <span>Feature <code className="font-mono text-amber-200">post_rr</code> uses the succeeding R-peak and is strictly an offline retrospective feature with ~0.75 s to 1.05 s lookahead latency.</span>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* 4 & 5. QUANTUM AI OPERATIONS & HARDWARE INTELLIGENCE          */}
      {/* ────────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Section 4: Quantum AI Operations Snapshot (6 cols) */}
        <div className="lg:col-span-6">
          <GlassCard className="p-6 border border-white/10 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-nexus-cyan" />
                  Quantum AI Operations
                </h3>
                <button
                  onClick={() => onNavigate("quantum-ai-lab")}
                  className="text-xs text-nexus-cyan hover:underline font-mono flex items-center gap-1"
                >
                  Explore <ArrowRight className="w-3 h-3" />
                </button>
              </div>
              <p className="text-xs text-slate-400 mb-5 leading-relaxed">
                6-qubit Variational Quantum Classifier (VQC) executing deterministic expectation values on Qiskit statevector simulation.
              </p>

              <div className="grid grid-cols-2 gap-3 font-mono text-xs mb-4">
                <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                  <span className="text-slate-400 block text-[10px]">FEATURE ENCODING</span>
                  <span className="text-white font-bold text-sm">6 &times; RY Rotations</span>
                  <span className="text-[10px] text-nexus-cyan block mt-1">Feature range [0, &pi;]</span>
                </div>
                <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                  <span className="text-slate-400 block text-[10px]">ANSATZ ARCHITECTURE</span>
                  <span className="text-white font-bold text-sm">RealAmplitudes (reps=1)</span>
                  <span className="text-[10px] text-purple-300 block mt-1">12 Trainable Parameters</span>
                </div>
                <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                  <span className="text-slate-400 block text-[10px]">ENTANGLEMENT</span>
                  <span className="text-white font-bold text-sm">5 Linear CNOTs</span>
                  <span className="text-[10px] text-slate-400 block mt-1">Nearest-neighbor topology</span>
                </div>
                <div className="p-3 rounded-lg bg-black/30 border border-white/5">
                  <span className="text-slate-400 block text-[10px]">READOUT OBSERVABLE</span>
                  <span className="text-white font-bold text-sm">Average Pauli-Z &lang;O&rang;</span>
                  <span className="text-[10px] text-amber-300 block mt-1">P(V) = (&lang;O&rang; + 1) / 2</span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-xs font-mono text-slate-300 flex items-center justify-between">
              <span>Convergence Optimizer:</span>
              <span className="text-nexus-cyan">PRIMA COBYLA • Final MSE: 0.0770</span>
            </div>
          </GlassCard>
        </div>

        {/* Section 5: Hardware Intelligence Summary (6 cols) */}
        <div className="lg:col-span-6">
          <GlassCard className="p-6 border border-white/10 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-nexus-cyan" />
                  Hardware Topology & Transpilation
                </h3>
                <button
                  onClick={() => onNavigate("hardware-intelligence")}
                  className="text-xs text-nexus-cyan hover:underline font-mono flex items-center gap-1"
                >
                  Explore <ArrowRight className="w-3 h-3" />
                </button>
              </div>
              <p className="text-xs text-slate-400 mb-5 leading-relaxed">
                Comparative transpilation analysis contrasting 5-qubit linear baseline against 9-qubit sparse tree hardware target.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs mb-4">
                {/* Processor A Card */}
                <div className="p-3.5 rounded-xl bg-black/30 border border-rose-500/30">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="font-bold text-white">Processor A (5Q)</span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] bg-rose-500/20 text-rose-300 font-mono">1D Linear</span>
                  </div>
                  <div className="text-rose-400 font-bold text-xs mt-1">CircuitTooWideForTarget</div>
                  <div className="text-[10px] text-slate-400 mt-2 space-y-1">
                    <div>• Physical capacity: 5 qubits</div>
                    <div>• Logical circuit: 6 qubits</div>
                    <div className="text-rose-300">• Capacity boundary enforced</div>
                  </div>
                </div>

                {/* Processor B Card */}
                <div className="p-3.5 rounded-xl bg-black/30 border border-emerald-500/30">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="font-bold text-white">Processor B (9Q)</span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] bg-emerald-500/20 text-emerald-300 font-mono">Heavy-Hex</span>
                  </div>
                  <div className="text-emerald-400 font-bold text-xs mt-1">Transpiled (0 SWAP)</div>
                  <div className="text-[10px] text-slate-400 mt-2 space-y-1">
                    <div>• Transpiled depth: 15 (16 w/ meas)</div>
                    <div>• 2Q CNOT count: 5 CX</div>
                    <div>• Basis ops: 65 (rz:36, sx:24, cx:5)</div>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300/90 font-sans flex items-start gap-2">
              <Info className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              <span>Compilation metrics originate from Qiskit software transpilation (seed 42, opt level 1). No physical QPU executed.</span>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* 6 & 7. PERFORMANCE SNAPSHOT & SYSTEM DIAGNOSTICS              */}
      {/* ────────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Section 6: Performance Snapshot (7 cols) */}
        <div className="lg:col-span-7">
          <GlassCard className="p-6 border border-white/10 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-nexus-cyan" />
                    Model Performance & Benchmark Snapshot
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Empirical held-out test cohort benchmarks across quantum and classical models.
                  </p>
                </div>
                <button
                  onClick={() => onNavigate("performance-observatory")}
                  className="text-xs text-nexus-cyan hover:underline font-mono flex items-center gap-1 shrink-0"
                >
                  Explore <ArrowRight className="w-3 h-3" />
                </button>
              </div>

              {/* Benchmark Summary Table */}
              <div className="overflow-x-auto rounded-xl border border-white/10 bg-black/20 mb-4">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-nexus-navy/60 text-slate-400 text-[10px] uppercase border-b border-white/10">
                    <tr>
                      <th className="py-2.5 px-3">Model</th>
                      <th className="py-2.5 px-2 text-center">Train N</th>
                      <th className="py-2.5 px-2 text-right">Accuracy</th>
                      <th className="py-2.5 px-2 text-right">Sensitivity</th>
                      <th className="py-2.5 px-2 text-right">Specificity</th>
                      <th className="py-2.5 px-3 text-right">ROC-AUC</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    <tr className="hover:bg-white/[0.02]">
                      <td className="py-2.5 px-3 font-semibold text-white">6Q VQC (Ideal Statevector)</td>
                      <td className="py-2.5 px-2 text-center text-nexus-cyan">100</td>
                      <td className="py-2.5 px-2 text-right font-bold text-white">76.00%</td>
                      <td className="py-2.5 px-2 text-right text-emerald-400">100.0%</td>
                      <td className="py-2.5 px-2 text-right text-slate-300">52.00%</td>
                      <td className="py-2.5 px-3 text-right text-amber-300 font-bold">0.9988</td>
                    </tr>
                    <tr className="hover:bg-white/[0.02]">
                      <td className="py-2.5 px-3 font-semibold text-white">6Q VQC (Noisy Aer 4096s)</td>
                      <td className="py-2.5 px-2 text-center text-purple-300">100</td>
                      <td className="py-2.5 px-2 text-right font-bold text-white">77.00%</td>
                      <td className="py-2.5 px-2 text-right text-emerald-400">100.0%</td>
                      <td className="py-2.5 px-2 text-right text-slate-300">54.00%</td>
                      <td className="py-2.5 px-3 text-right text-amber-300 font-bold">0.9984</td>
                    </tr>
                    <tr className="hover:bg-white/[0.02]">
                      <td className="py-2.5 px-3 font-semibold text-slate-300">L2 Logistic Regression</td>
                      <td className="py-2.5 px-2 text-center text-slate-400">200</td>
                      <td className="py-2.5 px-2 text-right font-bold text-emerald-300">92.00%</td>
                      <td className="py-2.5 px-2 text-right text-emerald-400">100.0%</td>
                      <td className="py-2.5 px-2 text-right text-slate-300">84.00%</td>
                      <td className="py-2.5 px-3 text-right text-amber-300 font-bold">0.9960</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-slate-300 space-y-1">
              <span className="font-semibold text-amber-300 block">Training Condition Asymmetry (No Quantum Advantage):</span>
              <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
                The classical baseline was trained on 200 samples (records 106 + 119 combined), whereas the frozen VQC
                checkpoint was trained on 100 samples (Fold 1: record 106 only). Classical ML achieves higher overall accuracy
                (92% vs 76%). Quantum advantage is not claimed.
              </p>
            </div>
          </GlassCard>
        </div>

        {/* Section 7: System Diagnostics (5 cols) */}
        <div className="lg:col-span-5">
          <GlassCard className="p-6 border border-white/10 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-nexus-cyan" />
                  System Diagnostics & Runtime Telemetry
                </h3>
                <StatusBadge variant={isLiveApi ? "cyan" : "neutral"} size="sm">
                  {isLiveApi ? "API ONLINE" : "OFFLINE FALLBACK"}
                </StatusBadge>
              </div>
              <p className="text-xs text-slate-400 mb-5 leading-relaxed">
                Live verification via backend diagnostics endpoints (<code className="text-slate-300 font-mono">/health</code> and <code className="text-slate-300 font-mono">/api/overview</code>).
              </p>

              <div className="space-y-2.5 font-mono text-xs">
                <div className="p-2.5 rounded-lg bg-black/30 border border-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Quantum SDK:</span>
                  <span className="text-white font-semibold">Qiskit {healthData?.qiskit_version || "2.5.2"}</span>
                </div>
                <div className="p-2.5 rounded-lg bg-black/30 border border-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Simulation Engine:</span>
                  <span className="text-white font-semibold">Qiskit Aer {healthData?.aer_version || "0.17.2"}</span>
                </div>
                <div className="p-2.5 rounded-lg bg-black/30 border border-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Execution Mode:</span>
                  <span className="text-nexus-cyan font-semibold truncate max-w-[200px]">
                    {healthData?.execution_mode || "Classical Simulation"}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-black/30 border border-white/5 flex justify-between items-center">
                  <span className="text-slate-400">Physical QPU Accessed:</span>
                  <span className="text-amber-300 font-semibold">False (0 QPU Hours)</span>
                </div>
                <div className="p-2.5 rounded-lg bg-black/30 border border-white/5 flex justify-between items-center">
                  <span className="text-slate-400">REST Round-Trip Ping:</span>
                  <span className="text-nexus-cyan font-semibold">
                    {apiLatencyMs !== null ? `${apiLatencyMs} ms (Localhost)` : "Measuring..."}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-4 text-[10px] font-mono text-slate-500">
              * Note: Local REST ping reflects HTTP network transit, not quantum simulation wall-clock.
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* 8. RESEARCH INTEGRITY & SCIENTIFIC SAFEGUARDS                 */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10 space-y-4 bg-nexus-navy/70">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            Research Integrity & Methodological Safeguards
          </h2>
          <button
            onClick={onOpenDisclosures}
            className="text-xs text-amber-400 hover:underline font-mono"
          >
            Review Comprehensive Disclosures &rarr;
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs font-sans text-slate-300">
          <div className="p-3.5 rounded-xl bg-black/40 border border-white/5 space-y-1.5">
            <span className="font-semibold text-white font-mono block text-[11px]">1. RECORD-LEVEL SEPARATION</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Disjoint training/testing recordings isolate development (106, 119) from held-out test (200, 208).
              Audit reveals 9 partially overlapping window pairs (max overlap: 192 samples). This partitioning does not establish patient-level independence.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-black/40 border border-white/5 space-y-1.5">
            <span className="font-semibold text-white font-mono block text-[11px]">2. RETROSPECTIVE FEATURE</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Feature <code className="font-mono text-amber-200">post_rr</code> requires the subsequent R-peak (R[i+1]),
              introducing a mandatory physiological delay (~0.75 s to 1.05 s). Operates as an offline beat classifier.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-black/40 border border-white/5 space-y-1.5">
            <span className="font-semibold text-white font-mono block text-[11px]">3. CLASSICAL SIMULATION</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              All quantum circuits were evaluated via Qiskit 2.5.2 StatevectorEstimator and Aer 0.17.2 simulation.
              No physical cryogenic QPU hardware or IBM Quantum cloud execution was used.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-black/40 border border-white/5 space-y-1.5">
            <span className="font-semibold text-white font-mono block text-[11px]">4. ACADEMIC PROTOTYPE</span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              NEXUS-OPS is an academic engineering demonstrator developed for the IBM Quantum Qiskit Fall Fest 2026.
              Not certified by regulatory authorities or cleared for medical patient diagnosis.
            </p>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};
