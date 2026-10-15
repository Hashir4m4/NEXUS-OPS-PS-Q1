import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  Cpu,
  BarChart3,
  Layers,
  ShieldAlert,
  Info,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  TrendingUp,
  Percent,
  Sliders,
  Database,
} from "lucide-react";
import { GlassCard } from "../components/ui/GlassCard";
import { StatusBadge } from "../components/ui/StatusBadge";
import { api } from "../services/api";

// ──────────────────────────────────────────────────────────────
// VERIFIED EXPERIMENT ARTIFACT DATA
// Sourced strictly from:
// - results/classical_baseline.json (Milestone 4 Classical ML Baselines)
// - results/noisy_simulation_results.json (Qiskit Aer 0.17.2, 4096 shots)
// - results/vqc_architecture_decisions.json (Fold 1 Seed 303 Frozen Checkpoint)
// ──────────────────────────────────────────────────────────────

export interface ModelMetricDetails {
  id: string;
  name: string;
  category: "quantum_ideal" | "quantum_noisy" | "classical_baseline";
  architecture: string;
  trainingSamples: number;
  testSamples: number;
  accuracy: number;
  sensitivity: number;
  specificity: number;
  precision: number;
  f1: number;
  rocAuc: number;
  ece: number;
  confusionMatrix: {
    tn: number;
    fp: number;
    fn: number;
    tp: number;
  };
  sourceArtifact: string;
  notes: string;
}

const VERIFIED_MODELS: Record<string, ModelMetricDetails> = {
  vqc_ideal: {
    id: "vqc_ideal",
    name: "6-Qubit VQC (Ideal Statevector)",
    category: "quantum_ideal",
    architecture: "Variational Quantum Classifier (6 RY + RealAmplitudes reps=1, 12 params)",
    trainingSamples: 100, // Fold 1 (Record 106)
    testSamples: 100, // Records 200, 208
    accuracy: 0.76,
    sensitivity: 1.0,
    specificity: 0.52,
    precision: 0.6757, // 50 / (50 + 24) = 0.675675...
    f1: 0.8065, // 2*50 / (2*50 + 24 + 0) = 0.8064516...
    rocAuc: 0.9988,
    ece: 0.335,
    confusionMatrix: { tn: 26, fp: 24, fn: 0, tp: 50 },
    sourceArtifact: "results/vqc_training_runs.json & results/vqc_architecture_decisions.json",
    notes:
      "StatevectorEstimator forward pass with infinite shots. Zero false negatives on the held-out research cohort.",
  },
  vqc_noisy: {
    id: "vqc_noisy",
    name: "6-Qubit VQC (Noisy Aer 4096 Shots)",
    category: "quantum_noisy",
    architecture: "Qiskit Aer 0.17.2 EstimatorV2 (1Q 0.001, CX 0.005, Readout 0.010, 4096 shots)",
    trainingSamples: 100,
    testSamples: 100,
    accuracy: 0.77,
    sensitivity: 1.0,
    specificity: 0.54,
    precision: 0.6849, // 50 / (50 + 23) = 0.6849315...
    f1: 0.813, // 2*50 / (2*50 + 23 + 0) = 0.813008...
    rocAuc: 0.9984,
    ece: 0.3382,
    confusionMatrix: { tn: 27, fp: 23, fn: 0, tp: 50 },
    sourceArtifact: "results/noisy_simulation_results.json",
    notes:
      "Measurement-based AerSimulator with depolarizing and readout noise. Zero false negatives on held-out test cohort.",
  },
  logistic_regression: {
    id: "logistic_regression",
    name: "L2 Logistic Regression",
    category: "classical_baseline",
    architecture: "Linear Classifier (C=1.0, penalty=l2, solver=lbfgs)",
    trainingSamples: 200, // Records 106 + 119 combined
    testSamples: 100,
    accuracy: 0.92,
    sensitivity: 1.0,
    specificity: 0.84,
    precision: 0.8621,
    f1: 0.9259,
    rocAuc: 0.996,
    ece: 0.082,
    confusionMatrix: { tn: 42, fp: 8, fn: 0, tp: 50 },
    sourceArtifact: "results/classical_baseline.json",
    notes:
      "Trained on 200 samples (asymmetric condition compared to VQC 100-sample fold). Zero false negatives on test cohort.",
  },
  svm_rbf: {
    id: "svm_rbf",
    name: "Support Vector Machine (RBF)",
    category: "classical_baseline",
    architecture: "Kernel Support Vector Classifier (C=1.0, kernel=rbf, gamma=scale)",
    trainingSamples: 200,
    testSamples: 100,
    accuracy: 0.91,
    sensitivity: 1.0,
    specificity: 0.82,
    precision: 0.8475,
    f1: 0.9174,
    rocAuc: 0.996,
    ece: 0.091,
    confusionMatrix: { tn: 41, fp: 9, fn: 0, tp: 50 },
    sourceArtifact: "results/classical_baseline.json",
    notes:
      "Nonlinear kernel baseline trained on 200 samples. Zero false negatives on held-out test cohort.",
  },
  random_forest: {
    id: "random_forest",
    name: "Random Forest (100 Trees)",
    category: "classical_baseline",
    architecture: "Decision Tree Ensemble (n_estimators=100, max_depth=5, min_samples_split=4)",
    trainingSamples: 200,
    testSamples: 100,
    accuracy: 0.77,
    sensitivity: 1.0,
    specificity: 0.54,
    precision: 0.6849,
    f1: 0.813,
    rocAuc: 0.9864, // Exact verified value: 0.9863999999999999
    ece: 0.224,
    confusionMatrix: { tn: 27, fp: 23, fn: 0, tp: 50 },
    sourceArtifact: "results/classical_baseline.json",
    notes:
      "Ensemble baseline trained on 200 samples. Exactly 0.9864 ROC-AUC from results/classical_baseline.json.",
  },
};

export const PerformanceObservatory: React.FC = () => {
  // Navigation & filter state
  const [activeModelKey, setActiveModelKey] = useState<string>("vqc_ideal");
  const [metricSort, setMetricSort] = useState<"accuracy" | "f1" | "rocAuc" | "sensitivity" | "precision">("accuracy");
  const [vqcMode, setVqcMode] = useState<"ideal" | "noisy">("ideal");

  // API connectivity & data
  const [isLiveApi, setIsLiveApi] = useState<boolean>(false);
  const [apiLatencyMs, setApiLatencyMs] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const activeModel = VERIFIED_MODELS[activeModelKey] || VERIFIED_MODELS.vqc_ideal;

  // Fetch live API data
  const loadPerformanceData = useCallback(async () => {
    setIsLoading(true);
    const start = performance.now();
    try {
      const res = await api.getPerformanceOverview();
      const elapsed = Math.round(performance.now() - start);
      setApiLatencyMs(elapsed);
      if (res.isLive && res.data) {
        setIsLiveApi(true);
      } else {
        setIsLiveApi(false);
      }
    } catch {
      setIsLiveApi(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPerformanceData();
  }, [loadPerformanceData]);

  // Sync VQC mode toggle with active model
  const handleVqcModeToggle = (mode: "ideal" | "noisy") => {
    setVqcMode(mode);
    setActiveModelKey(mode === "ideal" ? "vqc_ideal" : "vqc_noisy");
  };

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION A: PERFORMANCE COMMAND CENTER                         */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10 relative overflow-hidden bg-gradient-to-br from-nexus-navy/90 via-nexus-surface/80 to-nexus-navy/95">
        <div className="absolute top-0 right-0 w-96 h-96 bg-nexus-cyan/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-6 pb-6 border-b border-white/10 relative z-10">
          <div>
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-wider font-semibold uppercase bg-nexus-cyan/15 text-nexus-cyan border border-nexus-cyan/30 flex items-center gap-1.5">
                <Activity className="w-3 h-3 animate-pulse" />
                Phase 5 • Milestone 4 Evaluation
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
                Leave-One-Record-Out Test Cohort (N=100)
              </span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight flex items-center gap-3">
              Performance Observatory
              <span className="text-xs font-mono font-normal text-slate-400 px-2 py-0.5 rounded bg-white/5 border border-white/10">
                Fold 1 Seed 303
              </span>
            </h1>
            <p className="text-slate-400 text-sm mt-1 max-w-3xl leading-relaxed">
              Research-grade performance analytics contrasting the frozen 6-qubit Variational Quantum
              Classifier under ideal statevector and noisy Aer simulation against rigorously audited
              classical machine-learning baselines.
            </p>
          </div>

          {/* Quick Actions & Ideal/Noisy Toggle */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="inline-flex p-1 rounded-xl bg-black/40 border border-white/10">
              <button
                onClick={() => handleVqcModeToggle("ideal")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  vqcMode === "ideal"
                    ? "bg-nexus-cyan text-black font-semibold shadow-glow-cyan-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                VQC Ideal (Statevector)
              </button>
              <button
                onClick={() => handleVqcModeToggle("noisy")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  vqcMode === "noisy"
                    ? "bg-violet-500 text-white font-semibold shadow-glow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                VQC Noisy (Aer 4096s)
              </button>
            </div>

            <button
              onClick={loadPerformanceData}
              disabled={isLoading}
              className="px-3 py-1.5 rounded-xl text-xs font-mono bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              title="Refresh performance overview"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-nexus-cyan" : ""}`} />
              Sync
            </button>
          </div>
        </div>

        {/* Primary KPI Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5 relative z-10">
          {/* Accuracy */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/5 hover:border-nexus-cyan/30 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>ACCURACY</span>
              <Percent className="w-3.5 h-3.5 text-nexus-cyan opacity-60 group-hover:opacity-100" />
            </div>
            <div className="text-2xl font-bold text-white tracking-tight">
              {vqcMode === "ideal" ? "76.00%" : "77.00%"}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1 font-mono">
              <span className="text-slate-300">{vqcMode === "ideal" ? "76 / 100" : "77 / 100"}</span>
              <span>test beats</span>
            </div>
          </div>

          {/* Sensitivity (Recall) */}
          <div className="p-4 rounded-xl bg-black/30 border border-emerald-500/20 hover:border-emerald-500/40 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>SENSITIVITY (RECALL)</span>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-400 tracking-tight">
              100.00%
            </div>
            <div className="text-[10px] text-emerald-400/80 mt-1 font-mono">
              50 / 50 VEB identified (0 FN)
            </div>
          </div>

          {/* Specificity */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/5 hover:border-nexus-cyan/30 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>SPECIFICITY</span>
              <Sliders className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <div className="text-2xl font-bold text-white tracking-tight">
              {vqcMode === "ideal" ? "52.00%" : "54.00%"}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              {vqcMode === "ideal" ? "26 / 50 Normal TN" : "27 / 50 Normal TN"}
            </div>
          </div>

          {/* Precision */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/5 hover:border-nexus-cyan/30 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>PRECISION (PPV)</span>
              <TrendingUp className="w-3.5 h-3.5 text-nexus-cyan opacity-60" />
            </div>
            <div className="text-2xl font-bold text-white tracking-tight">
              {vqcMode === "ideal" ? "67.57%" : "68.49%"}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              {vqcMode === "ideal" ? "50 / 74 predicted V" : "50 / 73 predicted V"}
            </div>
          </div>

          {/* F1 Score */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/5 hover:border-nexus-cyan/30 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>F1 SCORE</span>
              <BarChart3 className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-purple-300 tracking-tight">
              {vqcMode === "ideal" ? "0.8065" : "0.8130"}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              Harmonic mean P & R
            </div>
          </div>

          {/* ROC-AUC */}
          <div className="p-4 rounded-xl bg-black/30 border border-amber-500/20 hover:border-amber-500/40 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>ROC-AUC (RANK DISCRIM.)</span>
              <Activity className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-amber-300 tracking-tight">
              {vqcMode === "ideal" ? "0.9988" : "0.9984"}
            </div>
            <div className="text-[10px] text-amber-400/80 mt-1 font-mono">
              Scalar metric comparison
            </div>
          </div>
        </div>

        {/* Real-time Hardware / Backend Status Sub-strip */}
        <div className="mt-4 pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 font-mono">
          <div className="flex items-center gap-3">
            <span className="text-slate-400">Target Processor:</span>
            <span className="text-white font-medium">IBM Quantum Processor B (9Q Heavy-Hex)</span>
            <span className="text-slate-500">•</span>
            <span className="text-slate-400">Simulation Engine:</span>
            <span className="text-nexus-cyan">Qiskit 2.5.2 Statevector & Aer 0.17.2</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-amber-400 flex items-center gap-1 text-[11px]">
              <Info className="w-3 h-3" />
              Classical simulation only (no physical cryogenic QPU accessed)
            </span>
          </div>
        </div>
      </GlassCard>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION B: MODEL BENCHMARK OBSERVATORY                        */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
              <BarChart3 className="w-5 h-5 text-nexus-cyan" />
              Model Benchmark Observatory
            </h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Comparative benchmark across quantum architectures and classical baselines on the held-out test cohort.
            </p>
          </div>

          {/* Metric Sort Selector */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Sort by:</span>
            {(["accuracy", "f1", "rocAuc", "sensitivity", "precision"] as const).map((metric) => (
              <button
                key={metric}
                onClick={() => setMetricSort(metric)}
                className={`px-2.5 py-1 rounded-lg uppercase text-[11px] transition-all ${
                  metricSort === metric
                    ? "bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/40"
                    : "bg-white/5 text-slate-400 hover:text-white"
                }`}
              >
                {metric === "rocAuc" ? "ROC-AUC" : metric}
              </button>
            ))}
          </div>
        </div>

        {/* SCIENTIFIC QUALIFICATION NOTICE (MANDATORY) */}
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 mb-6 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
          <div className="text-xs text-slate-300 leading-relaxed">
            <span className="font-semibold text-amber-300 block mb-1">
              Scientific Qualification — Training Condition Asymmetry & No Quantum Advantage Claim:
            </span>
            The classical ML baselines (Logistic Regression, SVM-RBF, Random Forest) were trained on{" "}
            <strong className="text-white">200 development samples</strong> (MIT-BIH Records 106 and 119 combined),
            whereas the frozen 6-qubit VQC checkpoint was trained strictly on{" "}
            <strong className="text-white">100 samples</strong> (Fold 1: Record 106 only). This is an illustrative,
            unmatched benchmark. NEXUS-OPS does <strong className="text-amber-200">NOT claim quantum advantage</strong>{" "}
            or clinical superiority; classical models demonstrate higher overall accuracy (92% vs 76%) under matched
            features.
          </div>
        </div>

        {/* Benchmark Table */}
        <div className="overflow-x-auto rounded-xl border border-white/10 bg-black/20">
          <table className="w-full text-left text-xs">
            <thead className="bg-nexus-navy/60 text-slate-400 font-mono uppercase text-[10px] tracking-wider border-b border-white/10">
              <tr>
                <th className="py-3 px-4">Model Architecture</th>
                <th className="py-3 px-3 text-center">Train N</th>
                <th className="py-3 px-3 text-right">Accuracy</th>
                <th className="py-3 px-3 text-right">Sensitivity</th>
                <th className="py-3 px-3 text-right">Specificity</th>
                <th className="py-3 px-3 text-right">Precision</th>
                <th className="py-3 px-3 text-right">F1 Score</th>
                <th className="py-3 px-3 text-right">ROC-AUC</th>
                <th className="py-3 px-3 text-center">Calibration ECE</th>
                <th className="py-3 px-4 text-center">Select</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono">
              {Object.values(VERIFIED_MODELS)
                .sort((a, b) => b[metricSort] - a[metricSort])
                .map((m) => {
                  const isSelected = activeModelKey === m.id;
                  const isQuantum = m.category.startsWith("quantum");
                  return (
                    <tr
                      key={m.id}
                      onClick={() => setActiveModelKey(m.id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-nexus-cyan/10 hover:bg-nexus-cyan/15"
                          : "hover:bg-white/5"
                      }`}
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          {isQuantum ? (
                            <Cpu className="w-4 h-4 text-nexus-cyan shrink-0" />
                          ) : (
                            <Database className="w-4 h-4 text-slate-400 shrink-0" />
                          )}
                          <div>
                            <span className={`font-semibold ${isSelected ? "text-nexus-cyan" : "text-white"}`}>
                              {m.name}
                            </span>
                            <div className="text-[10px] text-slate-400 font-sans">{m.architecture}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-center text-slate-400">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] ${m.trainingSamples === 100 ? "bg-nexus-cyan/15 text-nexus-cyan" : "bg-white/10 text-slate-300"}`}>
                          {m.trainingSamples}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-white">
                        {(m.accuracy * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-3 text-right text-emerald-400 font-medium">
                        {(m.sensitivity * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-3 text-right text-slate-300">
                        {(m.specificity * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-3 text-right text-slate-300">
                        {(m.precision * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-3 text-right text-purple-300 font-medium">
                        {m.f1.toFixed(4)}
                      </td>
                      <td className="py-3 px-3 text-right text-amber-300 font-bold">
                        {m.rocAuc.toFixed(4)}
                      </td>
                      <td className="py-3 px-3 text-center text-slate-400">
                        {m.ece.toFixed(4)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveModelKey(m.id);
                          }}
                          className={`px-2.5 py-1 rounded text-[11px] font-sans font-medium transition-all ${
                            isSelected
                              ? "bg-nexus-cyan text-black font-semibold"
                              : "bg-white/5 text-slate-400 hover:text-white"
                          }`}
                        >
                          {isSelected ? "Inspecting" : "Inspect"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>

        {/* Data Source Footnote */}
        <div className="mt-3 text-[11px] text-slate-400 flex items-center justify-between font-mono">
          <span>Source: results/classical_baseline.json & results/noisy_simulation_results.json</span>
          <span className="text-nexus-cyan">Artifact-Backed Source of Truth (Bit-Exact)</span>
        </div>
      </GlassCard>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION C & D: CONFUSION MATRIX & ROC/METRIC ANALYSIS         */}
      {/* ────────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* SECTION C: CONFUSION MATRIX INTELLIGENCE (5 COLS) */}
        <div className="lg:col-span-5">
          <GlassCard className="p-6 border border-white/10 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-nexus-cyan" />
                  Confusion Matrix Intelligence
                </h3>
                <span className="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-white/5 border border-white/10">
                  {activeModel.name}
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-6">
                Evaluated on held-out test cohort (50 Normal, 50 VEB beats from MIT-BIH records 200 & 208).
              </p>

              {/* 2x2 Matrix Grid */}
              <div className="max-w-xs mx-auto mb-6">
                <div className="text-center text-[10px] font-mono text-slate-400 uppercase tracking-widest mb-2">
                  Predicted Class
                </div>
                <div className="flex">
                  <div className="w-8 flex items-center justify-center -rotate-90 text-[10px] font-mono text-slate-400 uppercase tracking-widest">
                    Actual
                  </div>
                  <div className="flex-1 space-y-2">
                    {/* Header Columns */}
                    <div className="grid grid-cols-2 gap-2 text-center text-[11px] font-mono text-slate-400">
                      <div>Normal (N)</div>
                      <div>VEB (V)</div>
                    </div>

                    {/* Row 1: Actual Normal */}
                    <div className="grid grid-cols-2 gap-2">
                      {/* True Negative */}
                      <div className="p-4 rounded-xl bg-nexus-cyan/10 border border-nexus-cyan/30 text-center hover:scale-[1.02] transition-transform group">
                        <div className="text-[10px] font-mono text-nexus-cyan uppercase">True Negative (TN)</div>
                        <div className="text-3xl font-bold text-white my-1 font-mono">
                          {activeModel.confusionMatrix.tn}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {((activeModel.confusionMatrix.tn / 50) * 100).toFixed(0)}% Normal Correct
                        </div>
                      </div>

                      {/* False Positive */}
                      <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-center hover:scale-[1.02] transition-transform group">
                        <div className="text-[10px] font-mono text-rose-400 uppercase">False Positive (FP)</div>
                        <div className="text-3xl font-bold text-rose-300 my-1 font-mono">
                          {activeModel.confusionMatrix.fp}
                        </div>
                        <div className="text-[10px] text-rose-400/80 font-mono">
                          Type I Error (Overcall)
                        </div>
                      </div>
                    </div>

                    {/* Row 2: Actual VEB */}
                    <div className="grid grid-cols-2 gap-2">
                      {/* False Negative */}
                      <div className={`p-4 rounded-xl text-center hover:scale-[1.02] transition-transform group ${
                        activeModel.confusionMatrix.fn === 0
                          ? "bg-emerald-500/10 border border-emerald-500/40"
                          : "bg-red-500/10 border border-red-500/40"
                      }`}>
                        <div className="text-[10px] font-mono text-emerald-400 uppercase">False Negative (FN)</div>
                        <div className="text-3xl font-bold text-emerald-300 my-1 font-mono">
                          {activeModel.confusionMatrix.fn}
                        </div>
                        <div className="text-[10px] text-emerald-400/80 font-mono">
                          Type II Error (Missed VEB)
                        </div>
                      </div>

                      {/* True Positive */}
                      <div className="p-4 rounded-xl bg-nexus-cyan/15 border border-nexus-cyan/40 text-center hover:scale-[1.02] transition-transform group">
                        <div className="text-[10px] font-mono text-nexus-cyan uppercase">True Positive (TP)</div>
                        <div className="text-3xl font-bold text-white my-1 font-mono">
                          {activeModel.confusionMatrix.tp}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          100% VEB Detected
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Zero False Negatives Research Finding */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 text-xs">
              <div className="flex items-center gap-2 text-emerald-400 font-mono font-semibold mb-1">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                Zero False Negatives in Research Cohort (FN = 0)
              </div>
              <p className="text-slate-400 leading-relaxed text-[11px]">
                Across all evaluated models (both quantum simulators and classical baselines), exactly zero
                ventricular ectopic beats were missed (Sensitivity = 100.00%) on the 100-sample held-out cohort.
                The primary divergence is in False Positives (Normal beats classified as VEB), where Logistic
                Regression produces only 8 FP compared to 24 FP in the Ideal VQC.
              </p>
            </div>
          </GlassCard>
        </div>

        {/* SECTION D: ROC & METRIC RADAR/COMPARISON (7 COLS) */}
        <div className="lg:col-span-7">
          <GlassCard className="p-6 border border-white/10 h-full flex flex-col justify-between">
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-nexus-cyan" />
                    ROC-AUC & Classification Metric Analysis
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Scalar metric comparison across models without fabricated continuous trajectory curves.
                  </p>
                </div>
                <span className="px-2.5 py-1 rounded-full text-[10px] font-mono bg-nexus-cyan/10 text-nexus-cyan border border-nexus-cyan/30 self-start">
                  Scalar Scores Verified
                </span>
              </div>

              {/* Scientific Disclosure on ROC Curves */}
              <div className="p-3 rounded-lg bg-black/40 border border-white/5 mb-5 flex items-start gap-2.5">
                <Info className="w-4 h-4 text-nexus-cyan mt-0.5 shrink-0" />
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  <strong className="text-slate-300">Methodological Note: </strong>
                  Full continuous ROC coordinate trajectories (FPR vs TPR sweeps) are not stored in the
                  frozen experiment JSONs. In accordance with scientific integrity guidelines, NEXUS-OPS renders
                  audited <strong className="text-white">scalar metric comparisons</strong> rather than reconstructing
                  artificial ROC curves.
                </p>
              </div>

              {/* Metric Breakdown Bars for Active Model */}
              <div className="space-y-4 mb-6">
                {[
                  { label: "ROC-AUC Score", value: activeModel.rocAuc, pct: activeModel.rocAuc * 100, color: "bg-amber-400", textCol: "text-amber-300" },
                  { label: "Classification Accuracy", value: activeModel.accuracy, pct: activeModel.accuracy * 100, color: "bg-nexus-cyan", textCol: "text-nexus-cyan" },
                  { label: "Sensitivity (Recall)", value: activeModel.sensitivity, pct: activeModel.sensitivity * 100, color: "bg-emerald-400", textCol: "text-emerald-400" },
                  { label: "Specificity", value: activeModel.specificity, pct: activeModel.specificity * 100, color: "bg-blue-400", textCol: "text-blue-300" },
                  { label: "Precision", value: activeModel.precision, pct: activeModel.precision * 100, color: "bg-purple-400", textCol: "text-purple-300" },
                  { label: "F1 Score", value: activeModel.f1, pct: activeModel.f1 * 100, color: "bg-fuchsia-400", textCol: "text-fuchsia-300" },
                ].map((bar) => (
                  <div key={bar.label} className="space-y-1">
                    <div className="flex justify-between items-center text-xs font-mono">
                      <span className="text-slate-400">{bar.label}</span>
                      <span className={`font-bold ${bar.textCol}`}>
                        {bar.label.includes("Score") || bar.label.includes("ROC")
                          ? bar.value.toFixed(4)
                          : `${bar.pct.toFixed(2)}%`}
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-black/40 overflow-hidden border border-white/5">
                      <div
                        className={`h-full rounded-full ${bar.color} transition-all duration-500`}
                        style={{ width: `${bar.pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Threshold & Calibration Disclosure */}
            <div className="p-3.5 rounded-xl bg-black/30 border border-white/10 text-xs">
              <div className="text-[11px] font-mono text-slate-300 font-semibold mb-1 flex items-center justify-between">
                <span>Decision Boundary: P(VEB) &ge; 0.5000</span>
                <span className="text-slate-500">ECE: {activeModel.ece.toFixed(4)}</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Binary classification applies the fixed canonical threshold of 0.5. Although ROC-AUC achieves
                exceptional discrimination ({activeModel.rocAuc.toFixed(4)}), the VQC suffers from probability
                compression near the decision boundary (ECE = {activeModel.ece.toFixed(4)}), reflecting calibration
                misalignment rather than poor ranking ability.
              </p>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION E: QUANTUM CIRCUIT COMPLEXITY & HARDWARE TARGETING    */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
              <Cpu className="w-5 h-5 text-nexus-cyan" />
              Quantum Circuit Performance & Complexity Architecture
            </h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Detailed structural decomposition of the 6-qubit VQC and execution routing across target quantum processors.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded text-[11px] font-mono bg-white/5 text-slate-300 border border-white/10">
              Ansatz: RealAmplitudes (reps=1)
            </span>
            <span className="px-2.5 py-1 rounded text-[11px] font-mono bg-nexus-cyan/15 text-nexus-cyan border border-nexus-cyan/30">
              12 Trainable Weights
            </span>
          </div>
        </div>

        {/* 3-Column Complexity Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
          {/* Column 1: Logical Circuit Blueprint */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/10 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-nexus-cyan font-semibold flex items-center gap-1.5">
                <Layers className="w-4 h-4" />
                Logical Architecture
              </span>
              <span className="text-slate-400">6 Logical Qubits</span>
            </div>
            <ul className="text-xs space-y-2 text-slate-300 divide-y divide-white/5 font-mono">
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Feature Encoding:</span>
                <span className="text-white">6 &times; RY Rotations</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Ansatz Rotations:</span>
                <span className="text-white">12 &times; RY Gates</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Entanglement Scheme:</span>
                <span className="text-nexus-cyan">Linear (5 CNOT Gates)</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Readout Observable:</span>
                <span className="text-white">Average Pauli-Z &lang;Z&rang;</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Probability Mapping:</span>
                <span className="text-amber-300 font-bold">P(V) = (&lang;Z&rang; + 1) / 2</span>
              </li>
            </ul>
          </div>

          {/* Column 2: Processor B (Transpilation Success) */}
          <div className="p-4 rounded-xl bg-black/30 border border-emerald-500/30 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-emerald-400 font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                Processor B Transpilation
              </span>
              <span className="text-emerald-300">Native Embedding</span>
            </div>
            <ul className="text-xs space-y-2 text-slate-300 divide-y divide-white/5 font-mono">
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Hardware Target:</span>
                <span className="text-white">9-Qubit Heavy-Hex Tree</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Transpiled Depth:</span>
                <span className="text-white">15 (16 w/ measurements)</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">2Q CNOT Count:</span>
                <span className="text-emerald-400 font-bold">5 CX (0 SWAP Overhead)</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Total Basis Ops:</span>
                <span className="text-white">65 (rz:36, sx:24, cx:5)</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Physical Layout:</span>
                <span className="text-slate-300">[0, 1, 2, 4, 5, 6]</span>
              </li>
            </ul>
          </div>

          {/* Column 3: Processor A (Capacity Exceeded) */}
          <div className="p-4 rounded-xl bg-black/30 border border-rose-500/30 space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-rose-400 font-semibold flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" />
                Processor A Capacity
              </span>
              <span className="text-rose-300">Capacity Reference</span>
            </div>
            <ul className="text-xs space-y-2 text-slate-300 divide-y divide-white/5 font-mono">
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Hardware Target:</span>
                <span className="text-white">5-Qubit 1D Linear Chain</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Capacity Status:</span>
                <span className="text-rose-400 font-bold">CircuitTooWideForTarget</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Qubit Deficit:</span>
                <span className="text-rose-300">6 logical vs 5 physical</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Transpilation Outcome:</span>
                <span className="text-slate-400">Execution Bounded</span>
              </li>
              <li className="pt-2 flex justify-between">
                <span className="text-slate-400">Challenge Kit Section:</span>
                <span className="text-slate-300">Section 3.1 & 3.4 Conformance</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Transpiled Gate Composition Bar */}
        <div className="p-4 rounded-xl bg-black/40 border border-white/5 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-300">Processor B Transpiled Basis Gate Distribution (Total 65 Ops)</span>
            <span className="text-slate-400">Basis: rz, sx, cx</span>
          </div>
          <div className="h-3 rounded-full bg-black/60 overflow-hidden flex border border-white/10">
            <div style={{ width: `${(36 / 65) * 100}%` }} className="bg-nexus-cyan h-full" title="36 RZ rotations (55.4%)" />
            <div style={{ width: `${(24 / 65) * 100}%` }} className="bg-purple-500 h-full" title="24 SX gates (36.9%)" />
            <div style={{ width: `${(5 / 65) * 100}%` }} className="bg-amber-400 h-full" title="5 CX gates (7.7%)" />
          </div>
          <div className="flex items-center gap-6 text-[11px] font-mono text-slate-400 pt-1">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-nexus-cyan" />
              <span>RZ Rotations: 36 (55.4%)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
              <span>SX Gates: 24 (36.9%)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
              <span>CX Two-Qubit: 5 (7.7%, 0 SWAP)</span>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION F: DIAGNOSTICS, DISCLOSURES & EXECUTION LIMITATIONS   */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            Scientific Disclosures & Performance Diagnostics
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Full compliance reporting, noise configuration parameters, and unmeasured telemetry boundary statements.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Sub-panel 1: Aer Noise Model Specifications */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/10 space-y-3">
            <h4 className="text-xs font-mono font-bold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-nexus-cyan" />
              Qiskit Aer Noise Configuration
            </h4>
            <div className="text-xs text-slate-300 space-y-2 font-mono">
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">1-Qubit Depolarizing Error:</span>
                <span className="text-white font-semibold">0.001 (0.10%)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">2-Qubit CX Depolarizing Error:</span>
                <span className="text-white font-semibold">0.005 (0.50%)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Readout Measurement Error:</span>
                <span className="text-white font-semibold">0.010 (1.00%)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Simulator Shots:</span>
                <span className="text-nexus-cyan font-semibold">4,096 Shots</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">T1 / T2 Thermal Relaxation:</span>
                <span className="text-amber-300 font-semibold">Not Simulated</span>
              </div>
            </div>
            <div className="p-2.5 rounded bg-white/5 text-[10px] text-slate-400 leading-relaxed font-sans">
              Noise parameters reflect conservative IBM Quantum Eagle-generation gate error envelopes.
              Shot noise is evaluated on the final classification expectation without continuous decoherence.
            </div>
          </div>

          {/* Sub-panel 2: Computational Execution Measurements ("Not Measured") */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/10 space-y-3">
            <h4 className="text-xs font-mono font-bold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-purple-400" />
              Hardware Telemetry Boundary & Unmeasured Quantities
            </h4>
            <div className="text-xs text-slate-300 space-y-2 font-mono">
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Physical QPU Execution Time:</span>
                <span className="text-slate-400 italic">Not measured (Classical Sim)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Cryostat Temperature:</span>
                <span className="text-slate-400 italic">Not measured (No Physical QPU)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">QPU Queue Latency:</span>
                <span className="text-slate-400 italic">Not measured (Local Execution)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Real-time GPU / RAM Telemetry:</span>
                <span className="text-slate-400 italic">Not measured</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Client REST Network Round-Trip:</span>
                <span className="text-nexus-cyan font-semibold">
                  {apiLatencyMs !== null ? `${apiLatencyMs} ms (Localhost)` : "Measuring..."}
                </span>
              </div>
            </div>
            <div className="p-2.5 rounded bg-white/5 text-[10px] text-slate-400 leading-relaxed font-sans">
              Hardware runtime measurements are strictly omitted rather than filled with illustrative values.
              The only active timing is the true REST network latency between frontend and backend.
            </div>
          </div>
        </div>

        {/* Mandatory Research Integrity Disclosure Banner */}
        <div className="p-4 rounded-xl bg-nexus-navy/80 border border-white/10 flex items-start gap-3">
          <Info className="w-5 h-5 text-nexus-cyan shrink-0 mt-0.5" />
          <div className="text-xs text-slate-300 leading-relaxed space-y-1.5">
            <div className="font-semibold text-white">
              Dataset Partitioning & Clinical Prototype Disclaimer
            </div>
            <p className="text-slate-400">
              Model selection was finalized on checkpoint <strong className="text-slate-200">fold_1_seed_303</strong>.
              Training was performed strictly on MIT-BIH Record 106, validation on Record 119, and testing on Records 200 and 208.
              While this Leave-One-Record-Out protocol eliminates beat-level data leakage between training and evaluation,
              it does not guarantee generalizability across broader patient populations. NEXUS-OPS is an academic engineering
              demonstrator developed for the IBM Quantum Qiskit Fall Fest 2026 and is not certified for clinical patient diagnostics.
            </p>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};
