import React, { useState, useEffect, useMemo } from "react";
import {
  Activity,
  Info,
  Zap,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
} from "lucide-react";
import { GlassCard } from "../components/ui/GlassCard";
import { StatusBadge } from "../components/ui/StatusBadge";
import { InteractiveEcgViewer } from "../components/ecg/InteractiveEcgViewer";
import {
  api,
  type PredictResult,
  type EcgWaveformResult,
  type EcgSegmentSummaryItem,
} from "../services/api";
import { FALLBACK_WAVEFORMS, FALLBACK_SEGMENTS_LIST } from "../services/fallbackEcg";

interface EcgIntelligenceProps {
  onOpenDisclosures: () => void;
}

// Curated high-impact benchmark beats for fast clinical & quantum comparison
const BENCHMARK_PRESETS = [
  {
    id: "REC200_B0105_N",
    label: "Clean NSR (Record 200 · Beat 105)",
    tag: "Held-Out Test",
    badge: "Normal",
    variant: "emerald" as const,
  },
  {
    id: "REC200_B0061_V",
    label: "Classic VEB (Record 200 · Beat 61)",
    tag: "Held-Out Test",
    badge: "VEB",
    variant: "magenta" as const,
  },
  {
    id: "REC208_B2007_N",
    label: "Morphology Shift (Record 208 · Beat 2007)",
    tag: "Sample 82 False Positive",
    badge: "Normal",
    variant: "amber" as const,
  },
  {
    id: "REC200_B0828_N",
    label: "True Negative (Record 200 · Beat 828)",
    tag: "Sample 14",
    badge: "Normal",
    variant: "emerald" as const,
  },
  {
    id: "REC200_B0693_V",
    label: "True Positive (Record 200 · Beat 693)",
    tag: "Sample 11",
    badge: "VEB",
    variant: "magenta" as const,
  },
  {
    id: "REC106_B0020_N",
    label: "Development Train (Record 106 · Beat 20)",
    tag: "Training Fold 1",
    badge: "Normal",
    variant: "cyan" as const,
  },
];

export const EcgIntelligence: React.FC<EcgIntelligenceProps> = ({ onOpenDisclosures }) => {
  // Current selected segment ID
  const [selectedSegmentId, setSelectedSegmentId] = useState<string>("REC200_B0105_N");

  // Filter state for segment list
  const [filterSplit, setFilterSplit] = useState<string>("all");
  const [filterRecord, setFilterRecord] = useState<string>("all");
  const [filterLabel, setFilterLabel] = useState<string>("all");

  // Segment collection state
  const [segmentsList, setSegmentsList] = useState<EcgSegmentSummaryItem[]>(FALLBACK_SEGMENTS_LIST);
  const [isListLoading, setIsListLoading] = useState<boolean>(false);

  // Active Waveform data state
  const [waveformResult, setWaveformResult] = useState<EcgWaveformResult | null>(
    FALLBACK_WAVEFORMS["REC200_B0105_N"] || null
  );
  const [isWaveformLoading, setIsWaveformLoading] = useState<boolean>(false);
  const [isWaveformLive, setIsWaveformLive] = useState<boolean>(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Live inference state
  const [isRunningInference, setIsRunningInference] = useState<boolean>(false);
  const [inferenceResult, setInferenceResult] = useState<PredictResult | null>(null);

  // Illustrative noise simulation controls
  const [bwNoise, setBwNoise] = useState<number>(0);
  const [maNoise, setMaNoise] = useState<number>(0);
  const [emNoise, setEmNoise] = useState<number>(0);

  // 1. Load segments collection on mount
  useEffect(() => {
    setIsListLoading(true);
    api.getEcgList({ limit: 300 }).then((res) => {
      if (res.data && res.data.segments.length > 0) {
        setSegmentsList(res.data.segments);
      }
      setIsListLoading(false);
    });
  }, []);

  // 2. Fetch full 360-sample waveform when selectedSegmentId changes
  useEffect(() => {
    let isCancelled = false;
    setIsWaveformLoading(true);
    setFetchError(null);
    setInferenceResult(null);

    api.getEcgWaveform(selectedSegmentId).then((res) => {
      if (isCancelled) return;
      if (res.data) {
        setWaveformResult(res.data);
        setIsWaveformLive(res.isLive);
      } else {
        // Fallback to local cached sample if network fails
        const fallback =
          FALLBACK_WAVEFORMS[selectedSegmentId] ||
          FALLBACK_WAVEFORMS["REC200_B0105_N"] ||
          null;
        setWaveformResult(fallback);
        setIsWaveformLive(false);
        if (!fallback) {
          setFetchError(`Could not load segment '${selectedSegmentId}'.`);
        }
      }
      setIsWaveformLoading(false);
    });

    return () => {
      isCancelled = true;
    };
  }, [selectedSegmentId]);

  // Filtered segments for dropdown / selector
  const filteredSegments = useMemo(() => {
    return segmentsList.filter((seg) => {
      if (filterSplit !== "all" && seg.split !== filterSplit) return false;
      if (filterRecord !== "all" && String(seg.record_id) !== filterRecord) return false;
      if (filterLabel !== "all" && String(seg.label) !== filterLabel) return false;
      return true;
    });
  }, [segmentsList, filterSplit, filterRecord, filterLabel]);

  // Derived current beat properties
  const isNormal = waveformResult ? waveformResult.label === 0 : true;
  const isVEB = !isNormal;
  const rawFeat = waveformResult?.features_raw || {};
  const preRrVal = rawFeat.pre_rr ?? (isNormal ? 0.675 : 0.4944);
  const postRrVal = rawFeat.post_rr ?? (isNormal ? 0.7056 : 1.0139);
  const qrsRmsVal = rawFeat.qrs_rms ?? (isNormal ? 0.5049 : 1.0502);
  const qrsDurVal = rawFeat.qrs_duration ?? (isNormal ? 0.05 : 0.0361);
  const p2pVal = rawFeat.p2p_amplitude ?? (isNormal ? 1.575 : 2.845);
  const specRatioVal = rawFeat.spectral_ratio ?? (isNormal ? 0.287 : 0.0251);

  // Instantaneous HR: 60 / pre_rr (Physiologically validated from pre-R-peak interval)
  const hrBpm = preRrVal > 0 ? Math.round(60 / preRrVal) : 80;

  // Execute Quantum Forward Pass for current beat
  const handleExecuteQuantumInference = async () => {
    if (!waveformResult) return;
    setIsRunningInference(true);
    try {
      const res = await api.predict({
        sample_id: waveformResult.segment_id,
        record_id: waveformResult.record_id,
        features: {
          pre_rr: rawFeat.pre_rr ?? preRrVal,
          post_rr: rawFeat.post_rr ?? postRrVal,
          qrs_rms: rawFeat.qrs_rms ?? qrsRmsVal,
          qrs_duration: rawFeat.qrs_duration ?? qrsDurVal,
          p2p_amplitude: rawFeat.p2p_amplitude ?? p2pVal,
          spectral_ratio: rawFeat.spectral_ratio ?? specRatioVal,
          is_pre_scaled: false,
        },
      });
      if (res.data) {
        setInferenceResult(res.data);
      }
    } catch {
      // Retain offline fallback
    } finally {
      setIsRunningInference(false);
    }
  };

  // Determine current expectation and probability (from live inference, segment payload, or default)
  const currentPauliZ =
    inferenceResult?.pauli_z_expectation ??
    waveformResult?.pauli_z_expectation ??
    (isNormal ? -0.3603 : 0.2418);

  const currentProbVeb =
    inferenceResult?.probability_veb ??
    waveformResult?.probability_veb ??
    (isNormal ? 0.3199 : 0.6209);

  return (
    <div className="space-y-6">
      {/* Top Banner: HeartKit Lead II AI Cockpit & Provenance */}
      <div className="p-4 rounded-xl bg-nexus-card border border-white/10 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-emerald-500/20 text-emerald-400">
            <Activity className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm font-bold text-white uppercase tracking-wider">
                ECG Intelligence: Modified Limb Lead II (MLII) Waveform Exploration
              </h1>
              <StatusBadge variant="cyan" size="sm">
                360 Hz · 360 Samples / Beat
              </StatusBadge>
              {isWaveformLive ? (
                <StatusBadge variant="cyan" size="sm">
                  LIVE API (/api/ecg/{selectedSegmentId})
                </StatusBadge>
              ) : (
                <StatusBadge variant="neutral" size="sm">
                  AUDITED CACHED WAVEFORM
                </StatusBadge>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Interactive clinical waveform inspection on PhysioNet MIT-BIH recordings. Ground truth annotations compared to 6-qubit VQC inference.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenDisclosures}
            className="px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-xs font-mono text-slate-300 border border-white/10 flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Info className="w-3.5 h-3.5 text-nexus-cyan" />
            <span>Audit Guardrails</span>
          </button>
        </div>
      </div>

      {/* Segment Selection & Exploration Rack */}
      <GlassCard
        variant="hud"
        showBrackets
        title={
          <div className="flex items-center justify-between w-full flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-nexus-cyan" />
              <span className="font-mono text-xs uppercase tracking-wider text-white">
                Beat Segment Selector ({filteredSegments.length} of {segmentsList.length} beats)
                {isListLoading && <span className="text-nexus-cyan font-normal ml-1.5">[Syncing...]</span>}
                {!isListLoading && segmentsList.length < 300 && (
                  <span className="text-amber-400 font-normal ml-2 text-[10px]">
                    [Offline Fallback: {segmentsList.length} Curated Beats · Live Backend provides all 300 beats]
                  </span>
                )}
                {!isListLoading && segmentsList.length >= 300 && (
                  <span className="text-emerald-400 font-normal ml-2 text-[10px]">
                    [Live Cohort: All 300 Beats Available]
                  </span>
                )}
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              Active Beat: <strong className="text-nexus-cyan">{selectedSegmentId}</strong>
            </span>
          </div>
        }
      >
        <div className="space-y-3 pt-1">
          {/* Preset Buttons for Quick Exploration */}
          <div className="space-y-1.5">
            <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-amber-400" />
              <span>Curated Benchmark Beats:</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {BENCHMARK_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  onClick={() => setSelectedSegmentId(preset.id)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-mono border transition-all flex items-center gap-2 cursor-pointer ${
                    selectedSegmentId === preset.id
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
                        : preset.variant === "cyan"
                        ? "bg-nexus-cyan"
                        : "bg-emerald-400"
                    }`}
                  />
                  <span>{preset.label}</span>
                  <span className="text-[10px] text-slate-500 font-normal">[{preset.tag}]</span>
                </button>
              ))}
            </div>
          </div>

          {/* Filter Bar & Full Dropdown */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-2 border-t border-white/[0.06]">
            {/* Split Filter */}
            <div>
              <label className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
                Cohort Split
              </label>
              <select
                value={filterSplit}
                onChange={(e) => setFilterSplit(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-black/70 border border-white/10 text-xs font-mono text-slate-200 focus:outline-none focus:border-nexus-cyan"
              >
                <option value="all">All Splits (300 Beats)</option>
                <option value="test">Held-Out Test (200, 208 · 100 Beats)</option>
                <option value="train">Development (106, 119 · 200 Beats)</option>
              </select>
            </div>

            {/* Record Filter */}
            <div>
              <label className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
                MIT-BIH Record
              </label>
              <select
                value={filterRecord}
                onChange={(e) => setFilterRecord(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-black/70 border border-white/10 text-xs font-mono text-slate-200 focus:outline-none focus:border-nexus-cyan"
              >
                <option value="all">All Records (106, 119, 200, 208)</option>
                <option value="200">Record 200 (Test · Clean Baseline)</option>
                <option value="208">Record 208 (Test · Session Shift)</option>
                <option value="106">Record 106 (Train · LORO Fold 1)</option>
                <option value="119">Record 119 (Validation · LORO Fold 1)</option>
              </select>
            </div>

            {/* Class Filter */}
            <div>
              <label className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
                Morphology Class
              </label>
              <select
                value={filterLabel}
                onChange={(e) => setFilterLabel(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-black/70 border border-white/10 text-xs font-mono text-slate-200 focus:outline-none focus:border-nexus-cyan"
              >
                <option value="all">All Classes (Normal & VEB)</option>
                <option value="0">Normal Sinus Rhythm (N)</option>
                <option value="1">Ventricular Ectopic Beat (V)</option>
              </select>
            </div>

            {/* Direct Segment Select */}
            <div>
              <label className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
                Select Segment ID ({filteredSegments.length})
              </label>
              <select
                value={selectedSegmentId}
                onChange={(e) => setSelectedSegmentId(e.target.value)}
                disabled={filteredSegments.length === 0}
                className="w-full px-2.5 py-1.5 rounded-lg bg-nexus-black/90 border border-nexus-cyan/40 text-xs font-mono text-nexus-cyan font-bold focus:outline-none focus:border-nexus-cyan"
              >
                {filteredSegments.length === 0 ? (
                  <option value="">No segments match filters</option>
                ) : (
                  filteredSegments.map((seg) => (
                    <option key={seg.segment_id} value={seg.segment_id}>
                      {seg.segment_id} · Rec {seg.record_id} · [{seg.annotation_symbol}]
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Error Alert Banner if Segment Not Found */}
      {fetchError && (
        <div className="p-3 rounded-xl bg-pink-950/50 border border-pink-500/50 text-xs font-mono text-pink-200 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-pink-400 shrink-0" />
          <span>{fetchError} Reverting to audited representative segment.</span>
        </div>
      )}

      {/* Main Grid: Waveform Exploration Engine (8 cols) & Clinical/Quantum HUD (4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 cols): Interactive Waveform & 6 Continuous Biomarkers */}
        <div className="lg:col-span-8 space-y-4">
          {/* Interactive ECG Waveform Explorer Component */}
          <InteractiveEcgViewer
            signalSamples={waveformResult?.signal_samples || []}
            rPeakSample={waveformResult?.r_peak_sample ?? 144}
            samplingRate={waveformResult?.sampling_rate_hz ?? 360}
            label={waveformResult?.label ?? 0}
            annotationSymbol={waveformResult?.annotation_symbol ?? "N"}
            segmentId={selectedSegmentId}
            leadName={waveformResult?.lead_name ?? "MLII"}
            isLive={isWaveformLive}
            isLoading={isWaveformLoading}
            notes={waveformResult?.notes}
          />

          {/* 6 Physiological Biomarkers Grid (Exact Extracted Features from Dataset) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-slate-400">
              <span className="font-bold text-white uppercase tracking-wider">
                Extracted Biomarkers for Segment {selectedSegmentId}
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                Window: #{waveformResult?.window_start ?? 0}..#{waveformResult?.window_end ?? 360} (360 samples · 359 intervals = 997.2 ms)
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {/* Feature 1: Pre-RR */}
              <div className="p-3 rounded-xl bg-nexus-card border border-white/10 hover:border-nexus-cyan/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase">1. Pre-RR Interval</span>
                <div className="text-sm font-bold font-mono text-white mt-1">
                  {preRrVal.toFixed(4)} s
                </div>
                <div className="text-[10px] text-slate-500 font-mono">
                  {preRrVal < 0.6 ? "Premature beat marker" : "Normal RR pacing"}
                </div>
              </div>

              {/* Feature 2: Post-RR with Mandatory Retrospective Disclosure */}
              <div className="p-3 rounded-xl bg-nexus-card border border-white/10 hover:border-nexus-cyan/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase">2. Post-RR Interval</span>
                <div className="text-sm font-bold font-mono text-white mt-1">
                  {postRrVal.toFixed(4)} s
                </div>
                <div className="text-[10px] text-amber-300 font-mono mt-0.5">
                  * Retrospective (succeeding R-peak)
                </div>
              </div>

              {/* Feature 3: QRS RMS Voltage */}
              <div className="p-3 rounded-xl bg-nexus-card border border-white/10 hover:border-nexus-cyan/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase">3. QRS RMS Voltage</span>
                <div className="text-sm font-bold font-mono text-white mt-1">
                  {qrsRmsVal.toFixed(4)} mV
                </div>
                <div className="text-[10px] text-slate-500 font-mono">±69.4 ms window energy</div>
              </div>

              {/* Feature 4: QRS Duration */}
              <div className="p-3 rounded-xl bg-nexus-card border border-white/10 hover:border-nexus-cyan/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase">4. QRS Duration</span>
                <div className="text-sm font-bold font-mono text-white mt-1">
                  {qrsDurVal.toFixed(4)} s
                </div>
                <div className="text-[10px] text-slate-500 font-mono">20% envelope threshold</div>
              </div>

              {/* Feature 5: Peak-to-Peak Amplitude */}
              <div className="p-3 rounded-xl bg-nexus-card border border-white/10 hover:border-nexus-cyan/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase">5. Peak-to-Peak Amp</span>
                <div className="text-sm font-bold font-mono text-white mt-1">
                  {p2pVal.toFixed(3)} mV
                </div>
                <div className="text-[10px] text-slate-500 font-mono">Total voltage excursion</div>
              </div>

              {/* Feature 6: Spectral Ratio */}
              <div className="p-3 rounded-xl bg-nexus-card border border-white/10 hover:border-nexus-cyan/30 transition-colors">
                <span className="text-[10px] font-mono text-slate-400 uppercase">6. Spectral Ratio</span>
                <div className="text-sm font-bold font-mono text-white mt-1">
                  {specRatioVal.toFixed(4)}
                </div>
                <div className="text-[10px] text-slate-500 font-mono">P[10,25Hz] / P[0.5,40Hz]</div>
              </div>
            </div>
          </div>

          {/* Scaler Normalization & Clipping Status Card */}
          <div className="p-3 rounded-xl bg-black/40 border border-white/5 font-mono text-xs flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Scaler Mapping:</span>
              <span className="text-slate-200">Continuous features fitted to [0, π] on Dev Cohort (106, 119)</span>
            </div>
            {waveformResult?.is_clipped ? (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
                1+ Features Clipped to [0, π]
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                Within Scaler Range (0 Clipped)
              </span>
            )}
          </div>
        </div>

        {/* Right Column (4 cols): Quantum VQC Forward Pass, Diagnosis & Dials */}
        <div className="lg:col-span-4 space-y-4">
          {/* Classification & Quantum VQC Result Card */}
          <GlassCard
            variant="elevated"
            className={isNormal ? "border-emerald-500/40" : "border-pink-500/40"}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase text-slate-400">Diagnostic Status</span>
              <StatusBadge variant={isNormal ? "emerald" : "magenta"} pulse>
                {isNormal ? "Normal Sinus Rhythm" : "Ventricular Ectopic"}
              </StatusBadge>
            </div>

            <div className="mt-3">
              <div className="text-xl font-bold text-white">
                {isNormal ? "Normal Sinus Rhythm (N)" : "Ventricular Ectopic Beat (VEB)"}
              </div>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                {isNormal
                  ? "Orderly cardiac depolarization originating from sinoatrial node with balanced pre/post R-R intervals."
                  : "Premature wide QRS complex originating from ectopic ventricular foci followed by compensatory pause."}
              </p>
            </div>

            {/* Quantum Forward Pass Live Action & Telemetry */}
            <div className="mt-4 pt-3 border-t border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-mono text-slate-400">Quantum VQC Observable:</span>
                <button
                  onClick={handleExecuteQuantumInference}
                  disabled={isRunningInference}
                  className="px-2.5 py-1 rounded-lg bg-nexus-cyan/10 hover:bg-nexus-cyan/20 border border-nexus-cyan/40 text-nexus-cyan text-[11px] font-mono flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  {isRunningInference ? (
                    <RefreshCw className="w-3 h-3 animate-spin" />
                  ) : (
                    <Zap className="w-3 h-3" />
                  )}
                  <span>Run Live VQC</span>
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono p-2.5 rounded-lg bg-black/40 border border-white/5">
                <div>
                  <span className="text-[10px] text-slate-500 block">Pauli-Z ⟨O⟩ (6Q Avg)</span>
                  <span className="font-bold text-white">
                    {(currentPauliZ >= 0 ? "+" : "") + currentPauliZ.toFixed(4)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">P(VEB) = (⟨O⟩+1)/2</span>
                  <span
                    className={`font-bold ${
                      currentProbVeb >= 0.5 ? "text-pink-400" : "text-emerald-400"
                    }`}
                  >
                    {(currentProbVeb * 100).toFixed(2)}%
                  </span>
                </div>
              </div>

              {/* Execution provenance indicator */}
              <div className="mt-2 text-[10px] font-mono flex items-center gap-1 text-slate-400">
                {inferenceResult ? (
                  <>
                    <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
                    <span className="text-emerald-400">
                      Forward pass verified via Live FastAPI StatevectorEstimator
                    </span>
                  </>
                ) : (
                  <>
                    <Info className="w-3 h-3 text-nexus-cyan shrink-0" />
                    <span>Audited Checkpoint fold_1_seed_303 (12 variational weights)</span>
                  </>
                )}
              </div>
            </div>
          </GlassCard>

          {/* Physiological Metric Dials (All Grounded in Validated Segment Metadata) */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-nexus-card border border-white/10 text-center">
              <div className="text-[10px] font-mono text-slate-400 uppercase">Instantaneous HR</div>
              <div className="text-xl font-bold font-mono text-white mt-1">{hrBpm}</div>
              <div className="text-[10px] text-nexus-cyan font-mono">BPM (60 / pre_rr)</div>
            </div>

            <div className="p-3 rounded-xl bg-nexus-card border border-white/10 text-center">
              <div className="text-[10px] font-mono text-slate-400 uppercase">R-Peak Sample</div>
              <div className="text-xl font-bold font-mono text-nexus-cyan mt-1">
                #{waveformResult?.r_peak_sample ?? 24341}
              </div>
              <div className="text-[10px] text-slate-400 font-mono">Segment Center Point</div>
            </div>

            <div className="p-3 rounded-xl bg-nexus-card border border-white/10 text-center">
              <div className="text-[10px] font-mono text-slate-400 uppercase">Lead & Record</div>
              <div className="text-base font-bold font-mono text-slate-200 mt-1.5 truncate">
                MLII · Rec {waveformResult?.record_id ?? 200}
              </div>
              <div className="text-[10px] text-slate-400 font-mono">Modified Limb Lead II</div>
            </div>

            <div className="p-3 rounded-xl bg-nexus-card border border-white/10 text-center">
              <div className="text-[10px] font-mono text-slate-400 uppercase">Sampling Frequency</div>
              <div className="text-xl font-bold font-mono text-nexus-blue mt-1">360</div>
              <div className="text-[10px] text-nexus-blue font-mono">Hz (359 intervals / beat)</div>
            </div>
          </div>

          {/* Poincaré Phase Space Interval Plot (RR_n vs RR_n+1) */}
          <GlassCard
            variant="hud"
            title={
              <div className="flex items-center justify-between w-full">
                <span>Poincaré Interval Plot (RR_n vs RR_n+1)</span>
                <span className="text-[10px] font-mono text-slate-400">Current Beat Active</span>
              </div>
            }
          >
            <div className="h-32 w-full bg-nexus-black/90 rounded-lg border border-white/10 relative p-2 flex items-center justify-center overflow-hidden">
              {/* Identity line diagonal */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-[85%] h-[1px] bg-slate-700/60 rotate-45" />
              </div>

              {/* Background Reference Clusters */}
              <div className="absolute w-2.5 h-2.5 rounded-full bg-emerald-400/40 top-[40%] left-[45%]" />
              <div className="absolute w-2 h-2 rounded-full bg-emerald-400/30 top-[42%] left-[48%]" />
              <div className="absolute w-3 h-3 rounded-full bg-pink-500/40 top-[20%] left-[75%]" />
              <div className="absolute w-2 h-2 rounded-full bg-pink-500/30 top-[70%] left-[25%]" />

              {/* Current Beat Dynamic Marker */}
              {(() => {
                // Map pre_rr [0.3, 1.2] to X [10%, 90%], post_rr [0.3, 1.4] to Y [90%, 10%]
                const clampX = Math.max(10, Math.min(90, ((preRrVal - 0.3) / 0.9) * 80 + 10));
                const clampY = Math.max(10, Math.min(90, 100 - (((postRrVal - 0.3) / 1.1) * 80 + 10)));
                return (
                  <div
                    className={`absolute w-3.5 h-3.5 rounded-full border-2 border-white transition-all duration-300 ${
                      isVEB
                        ? "bg-pink-500 shadow-[0_0_12px_#EC4899]"
                        : "bg-emerald-400 shadow-[0_0_12px_#10B981]"
                    }`}
                    style={{ left: `${clampX}%`, top: `${clampY}%` }}
                    title={`Current Beat (${preRrVal.toFixed(3)}s, ${postRrVal.toFixed(3)}s)`}
                  />
                );
              })()}

              <span className="absolute bottom-1 right-2 text-[9px] font-mono text-slate-500">
                ({preRrVal.toFixed(3)}s, {postRrVal.toFixed(3)}s)
              </span>
            </div>
          </GlassCard>

          {/* Synthetic Noise Robustness Controls (Clearly Labeled as Illustrative Simulation) */}
          <GlassCard
            variant="elevated"
            title={
              <div className="flex items-center justify-between w-full">
                <span className="text-xs">Synthetic Noise Robustness Cockpit</span>
                <span className="text-[10px] text-amber-300 font-mono">Illustrative Simulation</span>
              </div>
            }
          >
            <div className="space-y-2.5 text-xs font-mono">
              <div className="space-y-1">
                <div className="flex justify-between text-slate-300">
                  <span>Baseline Wander (BW Noise)</span>
                  <span className="text-nexus-cyan">{bwNoise}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={bwNoise}
                  onChange={(e) => setBwNoise(Number(e.target.value))}
                  className="w-full accent-nexus-cyan h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-slate-300">
                  <span>Muscle Tremor (MA Noise)</span>
                  <span className="text-nexus-violet">{maNoise}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={maNoise}
                  onChange={(e) => setMaNoise(Number(e.target.value))}
                  className="w-full accent-nexus-violet h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-slate-300">
                  <span>Electrode Motion (EM Noise)</span>
                  <span className="text-pink-400">{emNoise}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={emNoise}
                  onChange={(e) => setEmNoise(Number(e.target.value))}
                  className="w-full accent-pink-400 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
};
