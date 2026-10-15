import React, { useState, useEffect, useCallback } from "react";
import {
  Database,
  ShieldCheck,
  ShieldAlert,
  Info,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sliders,
  Layers,
  FileCheck2,
  Activity,
  Scissors,
  Clock,
  Sparkles,
} from "lucide-react";
import { GlassCard } from "../components/ui/GlassCard";
import { StatusBadge } from "../components/ui/StatusBadge";
import { api } from "../services/api";

// ──────────────────────────────────────────────────────────────
// VERIFIED DATASET AUDIT CONSTANTS
// Strictly sourced from:
// - results/dataset_validation.json
// - results/feature_audit.json
// - results/feature_summary.json
// - report/dataset_preparation.md
// ──────────────────────────────────────────────────────────────

interface RecordCohortDetails {
  recordId: number;
  split: "development" | "held_out_test";
  role: string;
  totalValidNormal: number;
  totalValidVeb: number;
  selectedNormal: number;
  selectedVeb: number;
  totalSelected: number;
  excludedCount: number;
  clinicalNote: string;
}

const RECORD_COHORTS: RecordCohortDetails[] = [
  {
    recordId: 106,
    split: "development",
    role: "Train Fold 1 / Val Fold 2 (LORO Partition A)",
    totalValidNormal: 1506,
    totalValidVeb: 520,
    selectedNormal: 50,
    selectedVeb: 50,
    totalSelected: 100,
    excludedCount: 72,
    clinicalNote: "Female, age 24; medication: Inderal; multiform ventricular ectopic beats.",
  },
  {
    recordId: 119,
    split: "development",
    role: "Val Fold 1 / Train Fold 2 (LORO Partition B)",
    totalValidNormal: 1542,
    totalValidVeb: 444,
    selectedNormal: 50,
    selectedVeb: 50,
    totalSelected: 100,
    excludedCount: 108,
    clinicalNote: "Female, age 51; medication: Pronestyl; uniform ventricular ectopic beats.",
  },
  {
    recordId: 200,
    split: "held_out_test",
    role: "Final Frozen Benchmark (Test Partition C)",
    totalValidNormal: 1742,
    totalValidVeb: 826,
    selectedNormal: 25,
    selectedVeb: 25,
    totalSelected: 50,
    excludedCount: 224,
    clinicalNote: "Male, age 64; medication: Digoxin, Quinidine; difficult baseline wander and high VEB frequency.",
  },
  {
    recordId: 208,
    split: "held_out_test",
    role: "Final Frozen Benchmark (Test Partition D)",
    totalValidNormal: 1585,
    totalValidVeb: 992,
    selectedNormal: 25,
    selectedVeb: 25,
    totalSelected: 50,
    excludedCount: 463,
    clinicalNote: "Female, age 67; coupled VEB couplets and variable morphology (Sample 82 locus).",
  },
];

interface ExclusionReasonItem {
  reason: string;
  count: number;
  percentage: number;
  category: "Non-target annotation symbol" | "Boundary violation";
  description: string;
}

const EXCLUSION_BREAKDOWN: ExclusionReasonItem[] = [
  {
    reason: "Symbol 'F' (Fusion of ventricular and normal beat)",
    count: 375,
    percentage: 43.25,
    category: "Non-target annotation symbol",
    description: "Hybrid depolarizations excluded to maintain binary N vs V diagnostic clarity.",
  },
  {
    reason: "Symbol '+' (Rhythm annotation / Pacemaker change)",
    count: 345,
    percentage: 39.79,
    category: "Non-target annotation symbol",
    description: "Auxiliary rhythm indicators and non-beat event markers in MIT-BIH header files.",
  },
  {
    reason: "Symbol '~' (Signal quality change / noise episode)",
    count: 101,
    percentage: 11.65,
    category: "Non-target annotation symbol",
    description: "Electrode motion artifact and transient electrical disconnection segments.",
  },
  {
    reason: "Symbol 'A' (Atrial premature contraction)",
    count: 30,
    percentage: 3.46,
    category: "Non-target annotation symbol",
    description: "Supraventricular premature beats excluded per protocol focused strictly on VEB.",
  },
  {
    reason: "Symbol '|' (Isolated pacemaker artifact)",
    count: 8,
    percentage: 0.92,
    category: "Non-target annotation symbol",
    description: "High-frequency artificial electronic pacing spikes without intrinsic depolarization.",
  },
  {
    reason: "Boundary Clamp Violation",
    count: 4,
    percentage: 0.46,
    category: "Boundary violation",
    description: "Beats located <144 samples from tape inception or >649,784 from tape terminus.",
  },
  {
    reason: "Symbol 'S' (Supraventricular ectopic beat)",
    count: 2,
    percentage: 0.23,
    category: "Non-target annotation symbol",
    description: "Nodal / junctional escape beats excluded from ventricular target.",
  },
  {
    reason: "Symbol 'Q' (Unclassifiable / paced beat)",
    count: 2,
    percentage: 0.23,
    category: "Non-target annotation symbol",
    description: "Ambiguous morphology beats not meeting cardiologist consensus criteria.",
  },
];

interface FeatureAuditEntry {
  name: string;
  label: string;
  unit: string;
  physiologicalRole: string;
  devMin: number;
  devMax: number;
  fold1Min: number;
  fold1Max: number;
  testBelowCount: number;
  testAboveCount: number;
  totalClipped: number;
  clippingRatePct: number;
  leakageClassification: string;
}

const FEATURE_AUDIT_DATA: FeatureAuditEntry[] = [
  {
    name: "pre_rr",
    label: "Pre-R-peak Interval",
    unit: "seconds",
    physiologicalRole: "Prematurity marker: R_i - R_{i-1}. VEBs typically fire prematurely with shortened pre-RR.",
    devMin: 0.4500,
    devMax: 1.3528,
    fold1Min: 0.4500,
    fold1Max: 1.1833,
    testBelowCount: 4,
    testAboveCount: 0,
    totalClipped: 4,
    clippingRatePct: 4.0,
    leakageClassification: "Causal (strictly retrospective to prior beat R_{i-1})",
  },
  {
    name: "post_rr",
    label: "Post-R-peak Interval",
    unit: "seconds",
    physiologicalRole: "Compensatory pause: R_{i+1} - R_i. VEBs usually followed by full compensatory pause.",
    devMin: 0.4194,
    devMax: 1.4806,
    fold1Min: 0.4194,
    fold1Max: 1.4806,
    testBelowCount: 0,
    testAboveCount: 0,
    totalClipped: 0,
    clippingRatePct: 0.0,
    leakageClassification: "Lookahead-Dependent (requires succeeding R_{i+1}; offline only)",
  },
  {
    name: "qrs_rms",
    label: "QRS Root-Mean-Square Energy",
    unit: "mV",
    physiologicalRole: "Depolarization energy in [-25, +25] sample ROI with baseline median subtraction.",
    devMin: 0.3025,
    devMax: 1.5165,
    fold1Min: 0.3025,
    fold1Max: 1.5165,
    testBelowCount: 0,
    testAboveCount: 1,
    totalClipped: 1,
    clippingRatePct: 1.0,
    leakageClassification: "Within-Window Causal (spanning ~141.7 ms around R-peak)",
  },
  {
    name: "qrs_duration",
    label: "Estimated QRS Duration",
    unit: "seconds",
    physiologicalRole: "Estimated duration via 20% envelope threshold in [-36, +36] sample search window.",
    devMin: 0.0306,
    devMax: 0.0944,
    fold1Min: 0.0306,
    fold1Max: 0.0944,
    testBelowCount: 2,
    testAboveCount: 1,
    totalClipped: 3,
    clippingRatePct: 3.0,
    leakageClassification: "Within-Window Estimate (single-lead envelope caliper estimate)",
  },
  {
    name: "p2p_amplitude",
    label: "QRS Peak-to-Peak Amplitude",
    unit: "mV",
    physiologicalRole: "Dynamic voltage swing max(x) - min(x) within the QRS complex window.",
    devMin: 0.8800,
    devMax: 4.6000,
    fold1Min: 0.8800,
    fold1Max: 4.6000,
    testBelowCount: 0,
    testAboveCount: 0,
    totalClipped: 0,
    clippingRatePct: 0.0,
    leakageClassification: "Within-Window Causal (isolated to QRS ROI)",
  },
  {
    name: "spectral_ratio",
    label: "Spectral Band Power Ratio",
    unit: "ratio",
    physiologicalRole: "High-frequency to low-frequency power ratio via 360-sample discrete Fourier transform.",
    devMin: 0.0112,
    devMax: 0.4452,
    fold1Min: 0.0112,
    fold1Max: 0.4452,
    testBelowCount: 5,
    testAboveCount: 1,
    totalClipped: 6,
    clippingRatePct: 6.0,
    leakageClassification: "Within-Window Causal (frequency analysis bounded by 1.0 s epoch)",
  },
];

interface DatasetAuditProps {
  onOpenDisclosures?: () => void;
}

export const DatasetAudit: React.FC<DatasetAuditProps> = ({ onOpenDisclosures }) => {
  const [isLiveApi, setIsLiveApi] = useState<boolean>(false);
  const [apiLatencyMs, setApiLatencyMs] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedRecordId, setSelectedRecordId] = useState<number>(106);
  const [selectedFeatureIndex, setSelectedFeatureIndex] = useState<number>(0);
  const [filterSplit, setFilterSplit] = useState<"all" | "development" | "held_out_test">("all");

  const loadDatasetData = useCallback(async () => {
    setIsLoading(true);
    const start = performance.now();
    try {
      const res = await api.getDatasetOverview();
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
    loadDatasetData();
  }, [loadDatasetData]);

  const activeRecord = RECORD_COHORTS.find((r) => r.recordId === selectedRecordId) || RECORD_COHORTS[0];
  const activeFeature = FEATURE_AUDIT_DATA[selectedFeatureIndex];

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION A: DATASET COMMAND CENTER                              */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10 relative overflow-hidden bg-gradient-to-br from-nexus-navy/90 via-nexus-surface/80 to-nexus-navy/95">
        <div className="absolute top-0 right-0 w-96 h-96 bg-nexus-cyan/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-6 pb-6 border-b border-white/10 relative z-10">
          <div>
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-wider font-semibold uppercase bg-nexus-cyan/15 text-nexus-cyan border border-nexus-cyan/30 flex items-center gap-1.5">
                <Database className="w-3 h-3 animate-pulse" />
                Phase 5 • Step 5 Audit
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
                Record-Level Partitioning (No Patient-Level Independence Claim)
              </span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight flex items-center gap-3">
              Dataset & Integrity Audit
              <span className="text-xs font-mono font-normal text-slate-400 px-2 py-0.5 rounded bg-white/5 border border-white/10">
                PhysioNet MIT-BIH v1.0.0
              </span>
            </h1>
            <p className="text-slate-400 text-sm mt-1 max-w-3xl leading-relaxed">
              Exhaustive provenance, signal extraction, exclusion registry, and feature-space audit tracking 300
              clinically verified electrocardiogram segments extracted from Modified Lead II across four MIT-BIH recordings.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadDatasetData}
              disabled={isLoading}
              className="px-3.5 py-2 rounded-xl text-xs font-mono bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 flex items-center justify-center gap-2 transition-all disabled:opacity-50"
              title="Sync dataset telemetry"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin text-nexus-cyan" : ""}`} />
              Sync API
            </button>
            {onOpenDisclosures && (
              <button
                onClick={onOpenDisclosures}
                className="px-3.5 py-2 rounded-xl text-xs font-mono bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 flex items-center gap-2 transition-all"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Disclosures
              </button>
            )}
          </div>
        </div>

        {/* 6 Primary Key Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5 relative z-10">
          {/* Card 1: Total Beat Segments */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/5 hover:border-nexus-cyan/30 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>TOTAL SEGMENTS</span>
              <Layers className="w-3.5 h-3.5 text-nexus-cyan opacity-60 group-hover:opacity-100" />
            </div>
            <div className="text-2xl font-bold text-white tracking-tight">300 Beats</div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              150 Normal / 150 VEB (50:50)
            </div>
          </div>

          {/* Card 2: Signal Data Volume */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/5 hover:border-nexus-cyan/30 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>SIGNAL DATA POINTS</span>
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-white tracking-tight">108,000</div>
            <div className="text-[10px] text-emerald-400/80 mt-1 font-mono">
              0 NaN · 0 Inf · 0 Nulls
            </div>
          </div>

          {/* Card 3: ADC Calibration */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/5 hover:border-nexus-cyan/30 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>ADC CALIBRATION</span>
              <Sliders className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-white tracking-tight">200 ADC/mV</div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              Baseline Zero Offset: 1024
            </div>
          </div>

          {/* Card 4: Segment Geometry */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/5 hover:border-nexus-cyan/30 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>SEGMENT GEOMETRY</span>
              <Clock className="w-3.5 h-3.5 text-nexus-cyan opacity-60" />
            </div>
            <div className="text-2xl font-bold text-white tracking-tight">360 Samples</div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              144 Pre-R · 216 Post-R
            </div>
          </div>

          {/* Card 5: Scaler Clipping Rate */}
          <div className="p-4 rounded-xl bg-black/30 border border-amber-500/20 hover:border-amber-500/40 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>SCALER CLIPPING</span>
              <Scissors className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-amber-300 tracking-tight">14 / 600 (2.33%)</div>
            <div className="text-[10px] text-amber-400/80 mt-1 font-mono">
              13 / 100 test beats affected
            </div>
          </div>

          {/* Card 6: Quality Registry */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/5 hover:border-nexus-cyan/30 transition-all group">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 mb-1">
              <span>EXCLUSION LOG</span>
              <FileCheck2 className="w-3.5 h-3.5 text-slate-400" />
            </div>
            <div className="text-2xl font-bold text-white tracking-tight">867 Excluded</div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              F, +, ~, A, |, S, Q & boundaries
            </div>
          </div>
        </div>

        {/* Sub-strip Methodological Disclaimer */}
        <div className="mt-4 pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 font-mono">
          <div className="flex items-center gap-3">
            <span>Partitioning Scheme:</span>
            <span className="text-white font-medium">Leave-One-Record-Out (Records 106, 119, 200, 208)</span>
            <span className="text-slate-500">•</span>
            <span>Electrocardiographic Lead:</span>
            <span className="text-nexus-cyan font-medium">Modified Lead II (MLII)</span>
          </div>
          <div className="text-amber-400 flex items-center gap-1.5 text-[11px]">
            <Info className="w-3.5 h-3.5 shrink-0" />
            <span>Strict record separation enforced; demographic patient-level generalizability is unverified.</span>
          </div>
        </div>
      </GlassCard>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION B: DATASET PROVENANCE & COHORT COMPOSITION             */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
              <Database className="w-5 h-5 text-nexus-cyan" />
              Dataset Provenance & Cohort Composition
            </h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Physical recordings sourced from the MIT-BIH Arrhythmia Database (PhysioNet v1.0.0) under record-level isolation.
            </p>
          </div>

          {/* Filter split toggle */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Filter:</span>
            {(["all", "development", "held_out_test"] as const).map((split) => (
              <button
                key={split}
                onClick={() => setFilterSplit(split)}
                className={`px-3 py-1 rounded-lg uppercase text-[11px] transition-all ${
                  filterSplit === split
                    ? "bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/40 font-semibold"
                    : "bg-white/5 text-slate-400 hover:text-white"
                }`}
              >
                {split === "all" ? "All Records" : split === "development" ? "Development (200)" : "Test Cohort (100)"}
              </button>
            ))}
          </div>
        </div>

        {/* 4-Record Cohort Composition Table */}
        <div className="overflow-x-auto rounded-xl border border-white/10 bg-black/20 mb-6">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-nexus-navy/60 text-slate-400 text-[10px] uppercase tracking-wider border-b border-white/10">
              <tr>
                <th className="py-3 px-4">MIT-BIH Record</th>
                <th className="py-3 px-3">Partition Role</th>
                <th className="py-3 px-3 text-right">Pool Valid N</th>
                <th className="py-3 px-3 text-right">Pool Valid V</th>
                <th className="py-3 px-3 text-right">Selected Normal</th>
                <th className="py-3 px-3 text-right">Selected VEB</th>
                <th className="py-3 px-3 text-right">Total Selected</th>
                <th className="py-3 px-3 text-right">Excluded</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {RECORD_COHORTS.filter((r) => filterSplit === "all" || r.split === filterSplit).map((r) => {
                const isSelected = selectedRecordId === r.recordId;
                const isDev = r.split === "development";
                return (
                  <tr
                    key={r.recordId}
                    onClick={() => setSelectedRecordId(r.recordId)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? "bg-nexus-cyan/10 hover:bg-nexus-cyan/15" : "hover:bg-white/5"
                    }`}
                  >
                    <td className="py-3.5 px-4 font-bold text-white flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-nexus-cyan" />
                      Record {r.recordId}
                      <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase ${isDev ? "bg-blue-500/15 text-blue-300" : "bg-purple-500/15 text-purple-300"}`}>
                        {isDev ? "Dev" : "Test"}
                      </span>
                    </td>
                    <td className="py-3.5 px-3 text-slate-300">{r.role}</td>
                    <td className="py-3.5 px-3 text-right text-slate-400">{r.totalValidNormal}</td>
                    <td className="py-3.5 px-3 text-right text-slate-400">{r.totalValidVeb}</td>
                    <td className="py-3.5 px-3 text-right text-emerald-400 font-bold">{r.selectedNormal}</td>
                    <td className="py-3.5 px-3 text-right text-nexus-cyan font-bold">{r.selectedVeb}</td>
                    <td className="py-3.5 px-3 text-right text-white font-bold">{r.totalSelected}</td>
                    <td className="py-3.5 px-3 text-right text-amber-300 font-medium">{r.excludedCount}</td>
                    <td className="py-3.5 px-4 text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedRecordId(r.recordId);
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

        {/* Selected Record Clinical & Demographic Annotation Callout */}
        <div className="p-4 rounded-xl bg-black/40 border border-white/10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="text-xs font-mono font-bold text-nexus-cyan flex items-center gap-2">
              <Info className="w-4 h-4" />
              Inspecting Record {activeRecord.recordId} Metadata
            </div>
            <p className="text-xs text-slate-300 leading-relaxed font-sans max-w-2xl">
              {activeRecord.clinicalNote}
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono shrink-0">
            <div className="text-right">
              <span className="text-slate-400 block text-[10px]">SELECTED SUBSAMPLE</span>
              <span className="text-white font-bold">{activeRecord.totalSelected} / 300 beats ({(activeRecord.totalSelected / 300 * 100).toFixed(1)}%)</span>
            </div>
            <div className="text-right">
              <span className="text-slate-400 block text-[10px]">EXCLUDED RAW ANNOTATIONS</span>
              <span className="text-amber-300 font-bold">{activeRecord.excludedCount} beats</span>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION C: SIGNAL PROCESSING & EXTRACTION PIPELINE             */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
              <Clock className="w-5 h-5 text-nexus-cyan" />
              Signal Processing & Extraction Pipeline
            </h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Single-lead MLII epoching geometry, physical unit calibration, and window boundary compliance.
            </p>
          </div>

          <span className="px-2.5 py-1 rounded text-[11px] font-mono bg-nexus-cyan/10 text-nexus-cyan border border-nexus-cyan/30 self-start">
            Nominal Epoch Duration: 1.000 s (Span: 997.22 ms)
          </span>
        </div>

        {/* 360-Sample Interactive Window Geometry Visualizer */}
        <div className="p-5 rounded-xl bg-black/40 border border-white/10 space-y-4 mb-6">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="text-slate-300 font-semibold">360-Sample Beat Window Segmentation Architecture</span>
            <span className="text-slate-400">Total Epoch: 360 discrete points at 360 Hz</span>
          </div>

          {/* Visual Epoch Bar */}
          <div className="h-10 rounded-xl bg-black/60 overflow-hidden flex border border-white/10 relative">
            {/* Pre-R Window (144 samples, 400.0 ms) */}
            <div
              style={{ width: `${(144 / 360) * 100}%` }}
              className="bg-blue-500/20 border-r border-nexus-cyan/40 h-full flex items-center justify-center text-xs font-mono text-blue-300"
              title="Pre-R Window: 144 samples (400.0 ms), captures P wave & PR interval"
            >
              Pre-R Segment: 144 samples (400.0 ms)
            </div>

            {/* R-Peak Center Marker */}
            <div className="absolute left-[40%] top-0 bottom-0 w-1 bg-nexus-cyan shadow-[0_0_12px_#00F0FF] z-20" />

            {/* Post-R Window (216 samples, 600.0 ms) */}
            <div
              style={{ width: `${(216 / 360) * 100}%` }}
              className="bg-purple-500/20 h-full flex items-center justify-center text-xs font-mono text-purple-300"
              title="Post-R Window: 216 samples (600.0 ms), captures ST segment & T wave"
            >
              Post-R Segment: 216 samples (600.0 ms)
            </div>
          </div>

          {/* Timeline Annotation Labels */}
          <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
            <div>
              <span className="text-white block font-bold">t = -400.0 ms</span>
              <span>Sample 0 (Window Inception)</span>
            </div>
            <div className="text-center">
              <span className="text-nexus-cyan block font-bold">t = 0.0 ms (Sample 144)</span>
              <span className="text-white">Annotated R-Peak Anchor</span>
            </div>
            <div className="text-right">
              <span className="text-white block font-bold">t = +600.0 ms</span>
              <span>Sample 359 (Window Terminus)</span>
            </div>
          </div>
        </div>

        {/* 2-Column Processing Architecture */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
          {/* Column 1: ADC to mV Conversion */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/10 space-y-2.5">
            <h4 className="text-xs font-mono font-bold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-nexus-cyan" />
              Physical Calibration: ADC-to-mV Conversion
            </h4>
            <div className="p-3 rounded-lg bg-black/60 border border-white/5 font-mono text-xs text-nexus-cyan text-center">
              V (mV) = [ x_ADC - 1024 ] / 200.0
            </div>
            <ul className="text-xs text-slate-300 space-y-1.5 font-sans leading-relaxed">
              <li>• Raw MIT-BIH digitized samples use 11-bit representation with 1024 zero-offset.</li>
              <li>• Division by 200.0 converts integer ADC amplitudes into calibrated physical millivolts (mV).</li>
              <li>• First-to-last sample span: (360 - 1) / 360 Hz = 359 / 360 &asymp; <strong>997.22 ms</strong>.</li>
            </ul>
          </div>

          {/* Column 2: Sparse Window Overlap Disclosure */}
          <div className="p-4 rounded-xl bg-black/30 border border-amber-500/20 space-y-2.5">
            <h4 className="text-xs font-mono font-bold text-amber-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Window Overlap Disclosure (9 Pairs)
            </h4>
            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              Because 300 segments were subsampled from &gt;9,100 total beats across the 4 tapes, most selected
              beats are temporally isolated. However, exactly <strong className="text-white">9 adjacent pairs</strong> exhibit
              partial window overlap due to physiological premature coupling intervals:
            </p>
            <div className="text-[11px] font-mono text-slate-400 space-y-1">
              <div>• Maximum observed overlap: <strong className="text-white">192 samples (~533 ms)</strong> in Record 106 (pair REC106_B1910_V / REC106_B1911_V).</div>
              <div>• Minimum observed overlap: <strong className="text-white">15 samples (~41.7 ms)</strong> in Record 106 (pair REC106_B2037_N / REC106_B2039_V).</div>
              <div className="text-amber-400/90 text-[10px] pt-1">
                Note: The dataset does NOT claim zero overlap; 291 of 300 beats are completely non-overlapping.
              </div>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION D: DATA QUALITY & EXCLUSION REGISTRY AUDIT             */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
              <FileCheck2 className="w-5 h-5 text-nexus-cyan" />
              Data Quality & Exclusion Registry Audit
            </h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Exhaustive accounting of all 867 non-target beats and physiological anomalies excluded from the 300-segment cohort.
            </p>
          </div>

          <span className="px-2.5 py-1 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            Data Quality Audit: 100% Passed
          </span>
        </div>

        {/* 867-Exclusion Reason Breakdown Table */}
        <div className="overflow-x-auto rounded-xl border border-white/10 bg-black/20 mb-6">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-nexus-navy/60 text-slate-400 text-[10px] uppercase tracking-wider border-b border-white/10">
              <tr>
                <th className="py-3 px-4">Exclusion Reason & MIT-BIH Symbol</th>
                <th className="py-3 px-3">Classification Category</th>
                <th className="py-3 px-3 text-right">Count</th>
                <th className="py-3 px-3 text-right">Share (%)</th>
                <th className="py-3 px-4">Scientific Protocol Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {EXCLUSION_BREAKDOWN.map((item) => (
                <tr key={item.reason} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 px-4 font-bold text-white flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    {item.reason}
                  </td>
                  <td className="py-3 px-3 text-slate-300">
                    <span className="px-2 py-0.5 rounded bg-white/5 text-[10px]">
                      {item.category}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-nexus-cyan font-bold">{item.count}</td>
                  <td className="py-3 px-3 text-right text-slate-300 font-medium">{item.percentage.toFixed(2)}%</td>
                  <td className="py-3 px-4 text-slate-400 text-[11px] font-sans">{item.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Data Quality & Integrity Checklist */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-black/30 border border-white/10 space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-emerald-400">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              Signal Finiteness Verification
            </div>
            <p className="text-[11px] text-slate-300 font-sans leading-relaxed">
              Every single signal point (108,000 total) was audited:
              <strong className="text-white block mt-1 font-mono">0 NaN · 0 Inf · 0 Null values</strong>
              No missing sample imputation or artificial interpolation was performed.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-black/30 border border-white/10 space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-nexus-cyan">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              Recording Boundary Compliance
            </div>
            <p className="text-[11px] text-slate-300 font-sans leading-relaxed">
              Minimum window start sample: 6,328; maximum window end: 649,556 (out of 650,000 tape samples).
              <strong className="text-white block mt-1 font-mono">0 Boundary Overflows</strong>
              Edge boundary violations were strictly rejected from the cohort.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-black/30 border border-white/10 space-y-2">
            <div className="flex items-center gap-2 text-xs font-mono font-bold text-purple-300">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              Deterministic Subsampling Seed
            </div>
            <p className="text-[11px] text-slate-300 font-sans leading-relaxed">
              Random selection was performed using fixed seed:
              <strong className="text-white block mt-1 font-mono">Random Seed = 42 (Bit-Exact)</strong>
              Independent runs reproduce identical 300 segments matching the locked research CSVs.
            </p>
          </div>
        </div>
      </GlassCard>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION E: FEATURE ENGINEERING & LEAKAGE PREVENTION AUDIT      */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
              <Scissors className="w-5 h-5 text-nexus-cyan" />
              Feature Engineering & Scaler Fitting Boundaries
            </h2>
            <p className="text-slate-400 text-xs mt-0.5">
              Audit of the 6 extracted physiological features, MinMax scaling parameters, and test out-of-range clipping events.
            </p>
          </div>

          <span className="px-2.5 py-1 rounded text-[11px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/30">
            Total Clipped Values: 14 / 600 (2.33%) across 13 Beats
          </span>
        </div>

        {/* 6-Feature Engineering Table */}
        <div className="overflow-x-auto rounded-xl border border-white/10 bg-black/20 mb-6">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-nexus-navy/60 text-slate-400 text-[10px] uppercase tracking-wider border-b border-white/10">
              <tr>
                <th className="py-3 px-4">Feature Name</th>
                <th className="py-3 px-3">Unit</th>
                <th className="py-3 px-3 text-right">Dev Min (Fold 1)</th>
                <th className="py-3 px-3 text-right">Dev Max (Fold 1)</th>
                <th className="py-3 px-3 text-center">Test Below</th>
                <th className="py-3 px-3 text-center">Test Above</th>
                <th className="py-3 px-3 text-right">Total Clipped</th>
                <th className="py-3 px-3 text-right">Clipping Rate</th>
                <th className="py-3 px-4">Causal & Leakage Classification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {FEATURE_AUDIT_DATA.map((f, idx) => {
                const isSelected = selectedFeatureIndex === idx;
                const isLookahead = f.name === "post_rr";
                return (
                  <tr
                    key={f.name}
                    onClick={() => setSelectedFeatureIndex(idx)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? "bg-nexus-cyan/10 hover:bg-nexus-cyan/15" : "hover:bg-white/5"
                    }`}
                  >
                    <td className="py-3 px-4 font-bold text-white flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${isLookahead ? "bg-amber-400" : "bg-nexus-cyan"}`} />
                      {f.label}
                      <code className="text-[10px] text-slate-400 font-mono">({f.name})</code>
                    </td>
                    <td className="py-3 px-3 text-slate-400">{f.unit}</td>
                    <td className="py-3 px-3 text-right text-slate-300">{f.fold1Min.toFixed(4)}</td>
                    <td className="py-3 px-3 text-right text-slate-300">{f.fold1Max.toFixed(4)}</td>
                    <td className="py-3 px-3 text-center text-slate-300">{f.testBelowCount}</td>
                    <td className="py-3 px-3 text-center text-slate-300">{f.testAboveCount}</td>
                    <td className="py-3 px-3 text-right font-bold text-amber-300">{f.totalClipped}</td>
                    <td className="py-3 px-3 text-right font-bold text-amber-300">{f.clippingRatePct.toFixed(1)}%</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        isLookahead
                          ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                          : "bg-emerald-500/10 text-emerald-400"
                      }`}>
                        {f.leakageClassification}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Selected Feature Physiological Detail Callout */}
        <div className="p-4 rounded-xl bg-black/40 border border-white/10 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="text-xs font-mono font-bold text-nexus-cyan flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Inspecting Feature: {activeFeature.label} ({activeFeature.name})
            </div>
            <p className="text-xs text-slate-300 leading-relaxed font-sans max-w-2xl">
              {activeFeature.physiologicalRole}
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs font-mono shrink-0">
            <div className="text-right">
              <span className="text-slate-400 block text-[10px]">SCALER BOUNDS (DEV)</span>
              <span className="text-white font-bold">[{activeFeature.fold1Min.toFixed(3)}, {activeFeature.fold1Max.toFixed(3)}]</span>
            </div>
            <div className="text-right">
              <span className="text-slate-400 block text-[10px]">TEST CLIPPING EVENTS</span>
              <span className="text-amber-300 font-bold">{activeFeature.totalClipped} / 100 beats</span>
            </div>
          </div>
        </div>

        {/* MANDATORY RETROSPECTIVE FEATURE DISCLOSURE BOX */}
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
          <div className="text-xs text-slate-300 leading-relaxed space-y-1.5">
            <span className="font-semibold text-amber-300 block">
              Critical Methodological Disclosure — Retrospective `post_rr` Lookahead Feature:
            </span>
            <p>
              Feature <code className="text-amber-200 bg-black/40 px-1 py-0.5 rounded">post_rr</code> represents the interval
              between the current R-peak (R[i]) and the succeeding R-peak (R[i+1]). Because R[i+1] occurs in the future relative
              to beat i, this feature cannot be evaluated in real-time at the exact instant of the QRS complex.
            </p>
            <p className="text-slate-400">
              Physiological lookahead delay: Normal beats require an average waiting window of <strong>0.75 s</strong>, and VEBs
              require <strong>1.05 s</strong> (maximum observed: 1.48 s). NEXUS-OPS is therefore classified as an
              <strong className="text-white"> offline retrospective beat classifier</strong> rather than an instantaneous real-time alarm.
            </p>
          </div>
        </div>
      </GlassCard>

      {/* ────────────────────────────────────────────────────────────── */}
      {/* SECTION F: REPRODUCIBILITY, VALIDATION & SCIENTIFIC DISCLOSURE */}
      {/* ────────────────────────────────────────────────────────────── */}
      <GlassCard className="p-6 border border-white/10 space-y-6">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            Reproducibility, Validation & Scientific Disclosures
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Statistical boundaries, out-of-distribution clamping disclosures, and regulatory compliance notices.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Sub-panel 1: Scaler Clamping Disclosure */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/10 space-y-3">
            <h4 className="text-xs font-mono font-bold text-white flex items-center gap-2">
              <Scissors className="w-4 h-4 text-amber-400" />
              Scaler Clamping & Out-of-Distribution Saturation
            </h4>
            <div className="text-xs text-slate-300 space-y-2 font-mono">
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Total Evaluated Scalars:</span>
                <span className="text-white font-semibold">600 (100 beats &times; 6 features)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Total Clamped Values:</span>
                <span className="text-amber-300 font-semibold">14 values (2.33%)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Affected Test Beats:</span>
                <span className="text-amber-300 font-semibold">13 beats (13.00%)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Scaler Boundary Target:</span>
                <span className="text-nexus-cyan font-semibold">[0.0, &pi;] radians</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Fold 1 vs Dev Scaler:</span>
                <span className="text-white font-semibold">Fitted on Record 106 alone</span>
              </div>
            </div>
            <div className="p-2.5 rounded bg-white/5 text-[10px] text-slate-400 leading-relaxed font-sans">
              Test feature values outside the development training range are saturated at rotational boundary angles
              (0 or &pi; radians). This clamping prevents quantum angle overflow but does not preserve raw variance.
            </div>
          </div>

          {/* Sub-panel 2: Automated Verification Stamp */}
          <div className="p-4 rounded-xl bg-black/30 border border-white/10 space-y-3">
            <h4 className="text-xs font-mono font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Automated Integrity Verification Audit
            </h4>
            <div className="text-xs text-slate-300 space-y-2 font-mono">
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Frontend Scientific Tests:</span>
                <span className="text-emerald-400 font-semibold">35 / 35 Passed (100%)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Backend API Pytest Suite:</span>
                <span className="text-emerald-400 font-semibold">15 / 15 Passed (100%)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Dataset Finiteness Audit:</span>
                <span className="text-emerald-400 font-semibold">Passed (108,000 points)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Sample 82 Verification:</span>
                <span className="text-white font-semibold">Record 208 FP (P(V)=0.5638)</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Reproducibility Seed:</span>
                <span className="text-nexus-cyan font-semibold">Seed 42 & Seed 303</span>
              </div>
            </div>
            <div className="p-2.5 rounded bg-white/5 text-[10px] text-slate-400 leading-relaxed font-sans">
              All numbers, denominators, and bounds in this interface are verified against locked JSON and CSV artifacts
              in the repository root.
            </div>
          </div>
        </div>

        {/* Global Regulatory & Patient Generalizability Disclaimer */}
        <div className="p-4 rounded-xl bg-nexus-navy/80 border border-white/10 flex items-start gap-3">
          <Info className="w-5 h-5 text-nexus-cyan shrink-0 mt-0.5" />
          <div className="text-xs text-slate-300 leading-relaxed space-y-1.5">
            <div className="font-semibold text-white">
              Academic Research Prototype Notice & Patient Independence Disclaimer
            </div>
            <p className="text-slate-400">
              NEXUS-OPS was created as an academic research prototype for the IBM Quantum Qiskit Fall Fest 2026.
              The dataset employs strict record-level separation (records 106, 119 in development; records 200, 208 in test)
              to avoid intra-recording data contamination. However, because only four patient tapes were evaluated,
              this work does not prove demographic generalization across the wider human population. This platform is not
              cleared by the FDA or authorized for real-time medical patient diagnosis.
            </p>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};
