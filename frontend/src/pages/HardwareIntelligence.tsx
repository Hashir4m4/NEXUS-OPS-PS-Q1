import React, { useState, useEffect, useCallback } from "react";
import {
  Cpu,
  Zap,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Info,
  Layers,
  GitBranch,
  ArrowRightLeft,
  ShieldAlert,
  Network,
  Box,
  CircuitBoard,
} from "lucide-react";
import { GlassCard } from "../components/ui/GlassCard";
import { StatusBadge } from "../components/ui/StatusBadge";
import { api } from "../services/api";
import type { TranspileResult } from "../services/api";

// ──────────────────────────────────────────────────────────────
// VERIFIED HARDWARE CONSTANTS — sourced from processor JSON configs
// ──────────────────────────────────────────────────────────────

/** Processor A: 5-qubit 1D linear chain (processor_A.json) */
const PROC_A = {
  name: "Processor A",
  description: "5-qubit linear nearest-neighbor chain",
  physicalQubits: 5,
  connectivity: "Linear (1D Chain)",
  edges: [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 4],
  ] as [number, number][],
  basisGates: ["rz", "sx", "x", "cx"] as const,
  source: "Updated_Challenge_Kit.pdf (Section 3.1 & 3.4)",
  analogue: "IBM Quantum Falcon r4 / Manila linear subgraphs",
} as const;

/** Processor B: 9-qubit heavy-hex-inspired sparse tree (processor_B.json) */
const PROC_B = {
  name: "Processor B",
  description: "9-qubit heavy-hex-inspired sparse tree execution target",
  physicalQubits: 9,
  connectivity: "Heavy-Hex Sparse Tree",
  edges: [
    [0, 1],
    [1, 2],
    [2, 3],
    [2, 4],
    [4, 5],
    [5, 6],
    [4, 7],
    [7, 8],
  ] as [number, number][],
  basisGates: ["rz", "sx", "x", "cx"] as const,
  logicalMapping: [0, 1, 2, 4, 5, 6] as const,
  ancillaQubits: [3, 7, 8] as const,
  source: "Updated_Challenge_Kit.pdf (Section 3.2 & 3.4)",
  analogue: "IBM Quantum Eagle / Heron heavy-hex subgraphs",
} as const;

/** Verified transpilation metrics for Processor B (from backend) */
const VERIFIED_TRANSPILE_B = {
  depth: 15,
  depthWithMeas: 16,
  cxCount: 5,
  swapCount: 0,
  totalOps: 65,
  totalOpsWithMeas: 71,
  opsBreakdown: { rz: 36, sx: 24, cx: 5 } as Record<string, number>,
} as const;

// ──────────────────────────────────────────────────────────────
// SVG TOPOLOGY DIAGRAM COMPONENT
// ──────────────────────────────────────────────────────────────

interface TopologyNode {
  id: number;
  x: number;
  y: number;
  active: boolean;
  logicalQubit?: string;
}

interface TopologyDiagramProps {
  nodes: TopologyNode[];
  edges: [number, number][];
  activeColor: string;
  inactiveColor: string;
  glowFilter: string;
  hoveredNode: number | null;
  onHoverNode: (id: number | null) => void;
  width?: number;
  height?: number;
}

const TopologyDiagram: React.FC<TopologyDiagramProps> = ({
  nodes,
  edges,
  activeColor,
  inactiveColor,
  glowFilter,
  hoveredNode,
  onHoverNode,
  width = 500,
  height = 260,
}) => {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <svg
      className="w-full h-full"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <filter id="glow-cyan" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-amber" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <marker
          id="arrow-active"
          viewBox="0 0 10 6"
          refX="5"
          refY="3"
          markerWidth="6"
          markerHeight="4"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 3 L 0 6 z" fill={activeColor} opacity="0.5" />
        </marker>
      </defs>

      {/* Edges */}
      {edges.map(([a, b], idx) => {
        const na = nodeMap.get(a);
        const nb = nodeMap.get(b);
        if (!na || !nb) return null;
        const bothActive = na.active && nb.active;
        const isHovered = hoveredNode === a || hoveredNode === b;
        return (
          <line
            key={`edge-${idx}`}
            x1={na.x}
            y1={na.y}
            x2={nb.x}
            y2={nb.y}
            stroke={
              bothActive
                ? isHovered
                  ? activeColor
                  : activeColor
                : inactiveColor
            }
            strokeWidth={bothActive ? (isHovered ? 3.5 : 2.5) : 1.5}
            strokeDasharray={bothActive ? "none" : "4 4"}
            opacity={bothActive ? (isHovered ? 1 : 0.8) : 0.4}
            style={{ transition: "all 0.2s ease" }}
          />
        );
      })}

      {/* Nodes */}
      {nodes.map((node) => {
        const isHovered = hoveredNode === node.id;
        const r = node.active ? (isHovered ? 20 : 17) : 12;
        return (
          <g
            key={`node-${node.id}`}
            onMouseEnter={() => onHoverNode(node.id)}
            onMouseLeave={() => onHoverNode(null)}
            style={{ cursor: "pointer" }}
          >
            {/* Halo ring on hover */}
            {isHovered && node.active && (
              <circle
                cx={node.x}
                cy={node.y}
                r={r + 6}
                fill="none"
                stroke={activeColor}
                strokeWidth="1"
                opacity="0.3"
                className="animate-pulse"
              />
            )}
            <circle
              cx={node.x}
              cy={node.y}
              r={r}
              fill={node.active ? "#090E1A" : "#1E293B"}
              stroke={node.active ? activeColor : "#475569"}
              strokeWidth={node.active ? (isHovered ? 3 : 2.5) : 1}
              filter={node.active ? glowFilter : undefined}
              style={{ transition: "all 0.2s ease" }}
            />
            {/* Physical qubit label */}
            <text
              x={node.x}
              y={node.y + 4}
              textAnchor="middle"
              fill={node.active ? "#FFFFFF" : "#64748B"}
              fontSize={node.active ? "11" : "9"}
              fontFamily="monospace"
              fontWeight="bold"
            >
              P{node.id}
            </text>
            {/* Logical qubit label above active nodes */}
            {node.active && node.logicalQubit && (
              <text
                x={node.x}
                y={node.y - (isHovered ? 26 : 22)}
                textAnchor="middle"
                fill={activeColor}
                fontSize="10"
                fontFamily="monospace"
                fontWeight="600"
                style={{ transition: "all 0.2s ease" }}
              >
                {node.logicalQubit}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
};

// ──────────────────────────────────────────────────────────────
// PROCESSOR A TOPOLOGY NODES (5-qubit linear chain)
// ──────────────────────────────────────────────────────────────

const PROC_A_NODES: TopologyNode[] = [
  { id: 0, x: 70, y: 130, active: true },
  { id: 1, x: 160, y: 130, active: true },
  { id: 2, x: 250, y: 130, active: true },
  { id: 3, x: 340, y: 130, active: true },
  { id: 4, x: 430, y: 130, active: true },
];

// ──────────────────────────────────────────────────────────────
// PROCESSOR B TOPOLOGY NODES (9-qubit heavy-hex sparse tree)
// ──────────────────────────────────────────────────────────────

const PROC_B_NODES: TopologyNode[] = [
  { id: 0, x: 70, y: 65, active: true, logicalQubit: "q₀" },
  { id: 1, x: 160, y: 65, active: true, logicalQubit: "q₁" },
  { id: 2, x: 250, y: 65, active: true, logicalQubit: "q₂" },
  { id: 3, x: 340, y: 65, active: false },
  { id: 4, x: 250, y: 145, active: true, logicalQubit: "q₃" },
  { id: 5, x: 340, y: 145, active: true, logicalQubit: "q₄" },
  { id: 6, x: 430, y: 145, active: true, logicalQubit: "q₅" },
  { id: 7, x: 250, y: 215, active: false },
  { id: 8, x: 340, y: 215, active: false },
];

// ──────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ──────────────────────────────────────────────────────────────

export const HardwareIntelligence: React.FC = () => {
  // State
  const [selectedProcessor, setSelectedProcessor] = useState<
    "processor_b" | "processor_a"
  >("processor_b");
  const [transpileResults, setTranspileResults] = useState<
    Record<string, TranspileResult>
  >({});
  const [isTranspiling, setIsTranspiling] = useState(false);
  const [transpileMessage, setTranspileMessage] = useState<string | null>(null);
  const [transpileSourceA, setTranspileSourceA] = useState<
    "live" | "fallback" | null
  >(null);
  const [transpileSourceB, setTranspileSourceB] = useState<
    "live" | "fallback" | null
  >(null);
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);
  const [comparisonExpanded, setComparisonExpanded] = useState(true);
  const [resourceExpanded, setResourceExpanded] = useState(true);

  // Initial data load
  useEffect(() => {
    const loadInitial = async () => {
      const [resB, resA] = await Promise.all([
        api.transpile("processor_b"),
        api.transpile("processor_a"),
      ]);
      setTranspileResults({
        processor_b: resB.data,
        processor_a: resA.data,
      });
      setTranspileSourceB(resB.isLive ? "live" : "fallback");
      setTranspileSourceA(resA.isLive ? "live" : "fallback");
    };
    loadInitial();
  }, []);

  // Live transpilation handler
  const handleRunTranspile = useCallback(
    async (target: "processor_b" | "processor_a") => {
      setIsTranspiling(true);
      const label =
        target === "processor_b"
          ? "Processor B (9Q Heavy-Hex)"
          : "Processor A (5Q Linear)";
      setTranspileMessage(`Executing Qiskit transpile() pass for ${label}...`);
      try {
        const res = await api.transpile(target);
        setTranspileResults((prev) => ({ ...prev, [target]: res.data }));
        if (target === "processor_b") {
          setTranspileSourceB(res.isLive ? "live" : "fallback");
        } else {
          setTranspileSourceA(res.isLive ? "live" : "fallback");
        }
        setTranspileMessage(
          res.isLive
            ? `✓ Live transpilation via FastAPI backend — ${res.data.processor_name}`
            : `⟳ Verified against saved Qiskit Fall Fest transpilation artifacts`
        );
      } catch {
        setTranspileMessage(
          "✕ Transpiler execution error — displaying cached fallback"
        );
      } finally {
        setIsTranspiling(false);
      }
    },
    []
  );

  const procBResult = transpileResults["processor_b"];
  const procAResult = transpileResults["processor_a"];

  return (
    <div className="space-y-6">
      {/* ══════════════════════════════════════════════════
          SECTION A — HARDWARE COMMAND CENTER
          ══════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ── Processor B Card ── */}
        <div
          onClick={() => setSelectedProcessor("processor_b")}
          className={`group p-5 rounded-xl border transition-all duration-300 cursor-pointer ${
            selectedProcessor === "processor_b"
              ? "bg-nexus-blue/15 border-nexus-cyan shadow-glow-cyan-sm ring-1 ring-nexus-cyan/20"
              : "bg-nexus-card border-white/10 hover:border-nexus-cyan/40 hover:bg-nexus-card/80"
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-nexus-cyan/10 border border-nexus-cyan/30">
                <Cpu className="w-4.5 h-4.5 text-nexus-cyan" />
              </div>
              <div>
                <span className="font-bold text-white text-sm tracking-wide">
                  Processor B
                </span>
                <span className="text-[10px] text-nexus-cyan ml-2 font-mono">
                  PRIMARY TARGET
                </span>
              </div>
            </div>
            <StatusBadge variant="cyan" size="sm" pulse>
              9 Physical Qubits
            </StatusBadge>
          </div>

          <p className="text-xs text-slate-300 mb-3 leading-relaxed">
            Heavy-hex-inspired sparse tree topology with 8 bidirectional
            coupling edges. Full 6-qubit classifier embedding with zero SWAP
            routing overhead.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
            <div className="p-2 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-500 block mb-0.5">
                Physical Layout
              </span>
              <div className="text-emerald-400 font-bold text-[11px]">
                [{PROC_B.logicalMapping.join(",")}]
              </div>
            </div>
            <div className="p-2 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-500 block mb-0.5">
                Transpiled Depth
              </span>
              <div className="text-white font-bold text-[11px]">
                {procBResult?.depth ?? VERIFIED_TRANSPILE_B.depth} (
                {procBResult?.depth_with_measurements ??
                  VERIFIED_TRANSPILE_B.depthWithMeas}{" "}
                w/ meas)
              </div>
            </div>
            <div className="p-2 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-500 block mb-0.5">
                2Q Gates / SWAPs
              </span>
              <div className="text-nexus-cyan font-bold text-[11px]">
                {procBResult?.cx_count ?? VERIFIED_TRANSPILE_B.cxCount} CX / 0
                SWAP
              </div>
            </div>
            <div className="p-2 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-500 block mb-0.5">
                Ancilla Qubits
              </span>
              <div className="text-slate-400 font-bold text-[11px]">
                [{PROC_B.ancillaQubits.join(", ")}] idle
              </div>
            </div>
          </div>
        </div>

        {/* ── Processor A Card ── */}
        <div
          onClick={() => setSelectedProcessor("processor_a")}
          className={`group p-5 rounded-xl border transition-all duration-300 cursor-pointer ${
            selectedProcessor === "processor_a"
              ? "bg-amber-500/15 border-amber-400 shadow-glow-amber ring-1 ring-amber-400/20"
              : "bg-nexus-card border-white/10 hover:border-amber-400/40 hover:bg-nexus-card/80"
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <Cpu className="w-4.5 h-4.5 text-amber-400" />
              </div>
              <div>
                <span className="font-bold text-white text-sm tracking-wide">
                  Processor A
                </span>
                <span className="text-[10px] text-amber-400 ml-2 font-mono">
                  CAPACITY REFERENCE
                </span>
              </div>
            </div>
            <StatusBadge variant="amber" size="sm">
              5 Physical Qubits
            </StatusBadge>
          </div>

          <p className="text-xs text-slate-300 mb-3 leading-relaxed">
            Linear nearest-neighbor chain (0–1–2–3–4). The 6-logical-qubit
            classifier circuit cannot be directly mapped to this 5-qubit target.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-xs">
            <div className="p-2 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-500 block mb-0.5">
                Qubit Capacity
              </span>
              <div className="text-amber-300 font-bold text-[11px]">
                5 Phys / 6 Logical
              </div>
            </div>
            <div className="p-2 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-500 block mb-0.5">
                Transpile Result
              </span>
              <div className="text-rose-400 font-bold text-[10px] leading-tight">
                {procAResult?.error_type ?? "CircuitTooWideForTarget"}
              </div>
            </div>
            <div className="p-2 rounded-lg bg-black/40 border border-white/5">
              <span className="text-[10px] text-slate-500 block mb-0.5">
                Integrity Finding
              </span>
              <div className="text-emerald-400 font-bold text-[10px]">
                Zero Feature Deletion
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Simulation disclosure banner */}
      <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 flex items-start gap-2.5">
        <ShieldAlert className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
        <div className="text-[11px] text-slate-300 leading-relaxed">
          <span className="font-semibold text-amber-300">
            Hardware Simulation Disclosure:{" "}
          </span>
          Processor A and Processor B are{" "}
          <span className="text-white font-medium">
            configured transpilation targets
          </span>
          , not physical IBM Quantum QPU connections. All circuit compilation and
          execution uses Qiskit's software transpiler and Aer classical
          simulator. No cryogenic quantum hardware was accessed or executed
          against.
        </div>
      </div>

      {/* ══════════════════════════════════════════════════
          SECTIONS B & C — TOPOLOGY EXPLORER & COMPILATION
          ══════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Topology Visualization (8 cols) */}
        <div className="lg:col-span-8">
          <GlassCard
            variant="hud"
            showBrackets
            title={
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <Network className="w-4 h-4 text-nexus-cyan" />
                  <span>
                    {selectedProcessor === "processor_b"
                      ? "Processor B: 9-Qubit Heavy-Hex Topology"
                      : "Processor A: 5-Qubit Linear Chain"}
                  </span>
                </div>
                <StatusBadge
                  variant={
                    selectedProcessor === "processor_b" ? "cyan" : "amber"
                  }
                >
                  {selectedProcessor === "processor_b"
                    ? "Embedded (0 SWAPs)"
                    : "Capacity Overflow"}
                </StatusBadge>
              </div>
            }
            subtitle={
              selectedProcessor === "processor_b"
                ? "Physical qubits [0, 1, 2, 4, 5, 6] form a connected sub-tree hosting the 6-qubit VQC without SWAP routing."
                : "A 6-qubit circuit cannot be directly mapped to 5 physical qubits without discarding clinical features."
            }
            action={
              <button
                onClick={() => handleRunTranspile(selectedProcessor)}
                disabled={isTranspiling}
                className="px-3 py-1.5 rounded-lg bg-nexus-cyan/10 hover:bg-nexus-cyan/20 border border-nexus-cyan/40 text-nexus-cyan text-xs font-mono flex items-center gap-1.5 transition-all duration-200 disabled:opacity-50"
                title="Execute Qiskit transpile() pass live on Python backend"
              >
                {isTranspiling ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Zap className="w-3.5 h-3.5" />
                )}
                <span>Run Live Transpile</span>
              </button>
            }
          >
            {/* Transpilation status message */}
            {transpileMessage && (
              <div className="mb-3 p-2.5 rounded-lg bg-nexus-cyan/5 border border-nexus-cyan/20 text-[10px] font-mono text-nexus-cyan flex items-center justify-between">
                <span>{transpileMessage}</span>
                {isTranspiling && (
                  <RefreshCw className="w-3 h-3 animate-spin shrink-0" />
                )}
              </div>
            )}

            {/* SVG Topology Diagram */}
            <div className="h-72 w-full bg-nexus-black/90 rounded-xl border border-white/10 relative p-4 overflow-hidden">
              {selectedProcessor === "processor_b" ? (
                <>
                  <TopologyDiagram
                    nodes={PROC_B_NODES}
                    edges={PROC_B.edges}
                    activeColor="#00F0FF"
                    inactiveColor="#334155"
                    glowFilter="url(#glow-cyan)"
                    hoveredNode={hoveredNode}
                    onHoverNode={setHoveredNode}
                    height={260}
                  />
                  {/* Legend */}
                  <div className="absolute bottom-3 left-3 flex gap-4 text-[10px] font-mono">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-nexus-cyan shadow-[0_0_6px_#00F0FF]" />
                      <span className="text-slate-400">
                        Mapped (Logical → Physical)
                      </span>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-slate-600 border border-slate-500" />
                      <span className="text-slate-500">Ancilla (Idle)</span>
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <TopologyDiagram
                    nodes={PROC_A_NODES}
                    edges={PROC_A.edges}
                    activeColor="#F59E0B"
                    inactiveColor="#475569"
                    glowFilter="url(#glow-amber)"
                    hoveredNode={hoveredNode}
                    onHoverNode={setHoveredNode}
                    height={260}
                  />
                  {/* Capacity exceeded overlay */}
                  <div className="absolute bottom-4 left-0 right-0 flex justify-center">
                    <div className="px-4 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-mono flex items-center gap-2">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>
                        6-Qubit VQC exceeds 5 physical qubit capacity
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Hovered node detail */}
            {hoveredNode !== null && (
              <div className="mt-3 p-2.5 rounded-lg bg-white/[0.03] border border-white/10 font-mono text-[11px]">
                {selectedProcessor === "processor_b" ? (
                  (() => {
                    const node = PROC_B_NODES.find(
                      (n) => n.id === hoveredNode
                    );
                    if (!node) return null;
                    const mappingIdx = PROC_B.logicalMapping.indexOf(
                      hoveredNode as 0 | 1 | 2 | 4 | 5 | 6
                    );
                    const neighbors = PROC_B.edges
                      .filter(([a, b]) => a === hoveredNode || b === hoveredNode)
                      .map(([a, b]) => (a === hoveredNode ? b : a));
                    return (
                      <div className="flex flex-wrap gap-x-6 gap-y-1">
                        <span className="text-slate-400">
                          Physical:{" "}
                          <span className="text-white">P{hoveredNode}</span>
                        </span>
                        <span className="text-slate-400">
                          Status:{" "}
                          <span
                            className={
                              node.active
                                ? "text-nexus-cyan"
                                : "text-slate-500"
                            }
                          >
                            {node.active ? "Mapped" : "Ancilla (idle)"}
                          </span>
                        </span>
                        {mappingIdx >= 0 && (
                          <span className="text-slate-400">
                            Logical:{" "}
                            <span className="text-nexus-cyan">
                              q{mappingIdx}
                            </span>
                          </span>
                        )}
                        <span className="text-slate-400">
                          Neighbors:{" "}
                          <span className="text-white">
                            [{neighbors.join(", ")}]
                          </span>
                        </span>
                        <span className="text-slate-400">
                          Degree:{" "}
                          <span className="text-white">{neighbors.length}</span>
                        </span>
                      </div>
                    );
                  })()
                ) : (
                  <div className="flex flex-wrap gap-x-6 gap-y-1">
                    <span className="text-slate-400">
                      Physical:{" "}
                      <span className="text-white">P{hoveredNode}</span>
                    </span>
                    <span className="text-slate-400">
                      Connectivity:{" "}
                      <span className="text-amber-300">
                        Linear nearest-neighbor
                      </span>
                    </span>
                    <span className="text-slate-400">
                      Neighbors:{" "}
                      <span className="text-white">
                        [
                        {PROC_A.edges
                          .filter(
                            ([a, b]) =>
                              a === hoveredNode || b === hoveredNode
                          )
                          .map(([a, b]) => (a === hoveredNode ? b : a))
                          .join(", ")}
                        ]
                      </span>
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Challenge compliance note */}
            <div className="mt-3 p-3 rounded-lg bg-white/[0.02] border border-white/8 text-[11px] text-slate-400 leading-relaxed">
              <span className="font-semibold text-slate-300">
                Challenge Compliance:{" "}
              </span>
              {selectedProcessor === "processor_b"
                ? "Processor B provides sufficient physical qubits for native 6-qubit embedding. The Qiskit SABRE routing algorithm successfully maps all logical qubits to physical qubits [0, 1, 2, 4, 5, 6] without introducing any SWAP gates."
                : "Per Updated Challenge Kit Section 3.1, the project does not discard continuous physiological features to artificially fit the circuit onto Processor A. Processor B serves as the primary execution target."}
            </div>
          </GlassCard>
        </div>

        {/* Compilation Metrics Panel (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          {/* ── Transpilation Metrics ── */}
          <GlassCard
            variant="hud"
            title={
              <div className="flex items-center gap-2">
                <CircuitBoard className="w-4 h-4 text-nexus-cyan" />
                <span>Compilation Metrics</span>
              </div>
            }
            subtitle={
              selectedProcessor === "processor_b"
                ? "Processor B transpilation results"
                : "Processor A compilation status"
            }
            badge={
              <StatusBadge
                variant={
                  selectedProcessor === "processor_b" ? "emerald" : "amber"
                }
                size="sm"
                dot={false}
              >
                {selectedProcessor === "processor_b"
                  ? transpileSourceB === "live"
                    ? "LIVE"
                    : "CACHED"
                  : transpileSourceA === "live"
                    ? "LIVE"
                    : "CACHED"}
              </StatusBadge>
            }
          >
            {selectedProcessor === "processor_b" ? (
              <div className="space-y-2 font-mono text-xs">
                {[
                  {
                    label: "Target Basis Gates",
                    value: PROC_B.basisGates.join(", "),
                    color: "text-nexus-cyan",
                  },
                  {
                    label: "Transpiled Depth",
                    value: `${procBResult?.depth ?? VERIFIED_TRANSPILE_B.depth} (${procBResult?.depth_with_measurements ?? VERIFIED_TRANSPILE_B.depthWithMeas} w/ meas)`,
                    color: "text-white",
                  },
                  {
                    label: "Total Operations",
                    value: `${procBResult?.total_ops ?? VERIFIED_TRANSPILE_B.totalOps} (${VERIFIED_TRANSPILE_B.totalOpsWithMeas} w/ meas)`,
                    color: "text-white",
                  },
                  {
                    label: "Single-Qubit Gates",
                    value: `rz: ${VERIFIED_TRANSPILE_B.opsBreakdown.rz}, sx: ${VERIFIED_TRANSPILE_B.opsBreakdown.sx}`,
                    color: "text-slate-300",
                  },
                  {
                    label: "Two-Qubit (CX) Gates",
                    value: `${procBResult?.cx_count ?? VERIFIED_TRANSPILE_B.cxCount} CX`,
                    color: "text-nexus-blue font-bold",
                  },
                  {
                    label: "SWAP Routing Overhead",
                    value: `${procBResult?.swap_count ?? VERIFIED_TRANSPILE_B.swapCount} SWAPs`,
                    color: "text-emerald-400 font-bold",
                  },
                  {
                    label: "Physical Layout",
                    value: `[${(procBResult?.physical_layout ?? PROC_B.logicalMapping).join(", ")}]`,
                    color: "text-emerald-400",
                  },
                ].map(({ label, value, color }) => (
                  <div
                    key={label}
                    className="p-2.5 rounded-lg bg-black/40 border border-white/5 flex justify-between items-center"
                  >
                    <span className="text-slate-400">{label}</span>
                    <span className={color}>{value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-4 rounded-lg bg-rose-500/5 border border-rose-500/20 text-center">
                  <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto mb-2" />
                  <div className="font-mono text-xs text-rose-400 font-bold mb-1">
                    {procAResult?.error_type ?? "CircuitTooWideForTarget"}
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    {procAResult?.message ??
                      "Circuit width (6 qubits) exceeds physical capacity (5 qubits)."}
                  </p>
                </div>
                <div className="space-y-2 font-mono text-xs">
                  <div className="p-2.5 rounded-lg bg-black/40 border border-white/5 flex justify-between items-center">
                    <span className="text-slate-400">Physical Qubits</span>
                    <span className="text-amber-300 font-bold">5</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/40 border border-white/5 flex justify-between items-center">
                    <span className="text-slate-400">Logical Required</span>
                    <span className="text-white font-bold">6</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/40 border border-white/5 flex justify-between items-center">
                    <span className="text-slate-400">Qubit Deficit</span>
                    <span className="text-rose-400 font-bold">−1</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/40 border border-white/5 flex justify-between items-center">
                    <span className="text-slate-400">Connectivity</span>
                    <span className="text-amber-300">Linear (1D)</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-black/40 border border-white/5 flex justify-between items-center">
                    <span className="text-slate-400">Basis Gates</span>
                    <span className="text-slate-300">
                      {PROC_A.basisGates.join(", ")}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </GlassCard>

          {/* ── Connectivity Summary ── */}
          <GlassCard
            variant="hud"
            title={
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-violet-400" />
                <span>Connectivity Graph</span>
              </div>
            }
            subtitle={
              selectedProcessor === "processor_b"
                ? "8 bidirectional edges"
                : "4 bidirectional edges"
            }
          >
            <div className="space-y-1.5 font-mono text-xs">
              {(selectedProcessor === "processor_b"
                ? PROC_B.edges
                : PROC_A.edges
              ).map(([a, b], idx) => {
                const isActive =
                  selectedProcessor === "processor_b"
                    ? (
                        PROC_B.logicalMapping as readonly number[]
                      ).includes(a) &&
                      (
                        PROC_B.logicalMapping as readonly number[]
                      ).includes(b)
                    : true;
                return (
                  <div
                    key={idx}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded ${
                      isActive
                        ? "bg-nexus-cyan/5 border border-nexus-cyan/15"
                        : "bg-white/[0.02] border border-white/5"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span
                        className={
                          isActive ? "text-nexus-cyan" : "text-slate-500"
                        }
                      >
                        P{a}
                      </span>
                      <ArrowRightLeft
                        className={`w-3 h-3 ${isActive ? "text-nexus-cyan/60" : "text-slate-600"}`}
                      />
                      <span
                        className={
                          isActive ? "text-nexus-cyan" : "text-slate-500"
                        }
                      >
                        P{b}
                      </span>
                    </span>
                    <span
                      className={`text-[10px] ${isActive ? "text-emerald-400" : "text-slate-600"}`}
                    >
                      {isActive ? "Active" : "Unused"}
                    </span>
                  </div>
                );
              })}
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════
          SECTION D — INTERACTIVE TOPOLOGY COMPARISON
          ══════════════════════════════════════════════════ */}
      <GlassCard
        variant="hud"
        title={
          <div
            className="flex items-center justify-between w-full cursor-pointer"
            onClick={() => setComparisonExpanded(!comparisonExpanded)}
          >
            <div className="flex items-center gap-2">
              <ArrowRightLeft className="w-4 h-4 text-violet-400" />
              <span>Processor A vs Processor B — Compilation Comparison</span>
            </div>
            <span className="text-xs text-slate-500 font-mono">
              {comparisonExpanded ? "▼" : "▶"}
            </span>
          </div>
        }
        subtitle="Side-by-side transpilation and hardware compatibility analysis"
      >
        {comparisonExpanded && (
          <>
            {/* Comparison Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-2 px-3 text-slate-400 font-medium">
                      Property
                    </th>
                    <th className="text-center py-2 px-3 text-amber-400 font-medium">
                      <div className="flex items-center justify-center gap-1.5">
                        <Cpu className="w-3 h-3" />
                        Processor A
                      </div>
                    </th>
                    <th className="text-center py-2 px-3 text-nexus-cyan font-medium">
                      <div className="flex items-center justify-center gap-1.5">
                        <Cpu className="w-3 h-3" />
                        Processor B
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[
                    {
                      prop: "Physical Qubits",
                      a: "5",
                      b: "9",
                      aClass: "text-amber-300",
                      bClass: "text-nexus-cyan",
                    },
                    {
                      prop: "Connectivity",
                      a: "Linear (1D Chain)",
                      b: "Heavy-Hex Sparse Tree",
                      aClass: "text-slate-300",
                      bClass: "text-slate-300",
                    },
                    {
                      prop: "Coupling Edges",
                      a: "4",
                      b: "8",
                      aClass: "text-slate-300",
                      bClass: "text-slate-300",
                    },
                    {
                      prop: "6-Qubit Embedding",
                      a: "✕ Capacity Overflow",
                      b: "✓ Native Embedding",
                      aClass: "text-rose-400",
                      bClass: "text-emerald-400",
                    },
                    {
                      prop: "Compilation Status",
                      a: "CircuitTooWideForTarget",
                      b: "Transpilation Successful",
                      aClass: "text-rose-400",
                      bClass: "text-emerald-400",
                    },
                    {
                      prop: "CX Gate Count",
                      a: "—",
                      b: String(
                        procBResult?.cx_count ?? VERIFIED_TRANSPILE_B.cxCount
                      ),
                      aClass: "text-slate-600",
                      bClass: "text-nexus-cyan font-bold",
                    },
                    {
                      prop: "SWAP Overhead",
                      a: "—",
                      b: String(
                        procBResult?.swap_count ??
                          VERIFIED_TRANSPILE_B.swapCount
                      ),
                      aClass: "text-slate-600",
                      bClass: "text-emerald-400 font-bold",
                    },
                    {
                      prop: "Circuit Depth",
                      a: "—",
                      b: `${procBResult?.depth ?? VERIFIED_TRANSPILE_B.depth} / ${procBResult?.depth_with_measurements ?? VERIFIED_TRANSPILE_B.depthWithMeas}`,
                      aClass: "text-slate-600",
                      bClass: "text-white",
                    },
                    {
                      prop: "Total Operations",
                      a: "—",
                      b: String(
                        procBResult?.total_ops ??
                          VERIFIED_TRANSPILE_B.totalOps
                      ),
                      aClass: "text-slate-600",
                      bClass: "text-white",
                    },
                    {
                      prop: "Physical Layout",
                      a: "—",
                      b: `[${(procBResult?.physical_layout ?? PROC_B.logicalMapping).join(", ")}]`,
                      aClass: "text-slate-600",
                      bClass: "text-emerald-400",
                    },
                    {
                      prop: "Basis Gates",
                      a: PROC_A.basisGates.join(", "),
                      b: PROC_B.basisGates.join(", "),
                      aClass: "text-slate-300",
                      bClass: "text-slate-300",
                    },
                    {
                      prop: "QPU Execution",
                      a: "None (Simulated Target)",
                      b: "None (Simulated Target)",
                      aClass: "text-slate-500 italic",
                      bClass: "text-slate-500 italic",
                    },
                  ].map(({ prop, a, b, aClass, bClass }) => (
                    <tr key={prop} className="hover:bg-white/[0.02]">
                      <td className="py-2 px-3 text-slate-300 font-medium">
                        {prop}
                      </td>
                      <td className={`py-2 px-3 text-center ${aClass}`}>
                        {a}
                      </td>
                      <td className={`py-2 px-3 text-center ${bClass}`}>
                        {b}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Visual comparison summary */}
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/15">
                <div className="flex items-center gap-2 mb-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  <span className="text-xs font-semibold text-amber-300">
                    Processor A Outcome
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  The current 6-logical-qubit classifier circuit cannot be
                  directly compiled onto Processor A's 5 physical qubits. The
                  Qiskit transpiler rejects the circuit with{" "}
                  <code className="text-rose-400 bg-rose-500/10 px-1 rounded text-[10px]">
                    CircuitTooWideForTarget
                  </code>{" "}
                  before any routing is attempted.
                </p>
              </div>
              <div className="p-3 rounded-lg bg-nexus-cyan/5 border border-nexus-cyan/15">
                <div className="flex items-center gap-2 mb-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-xs font-semibold text-nexus-cyan">
                    Processor B Outcome
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  All 6 logical qubits embed cleanly onto physical qubits [0, 1,
                  2, 4, 5, 6]. The sparse-tree connectivity supports the linear
                  entanglement ladder without any additional SWAP gates,
                  resulting in 5 native CX operations and depth 15.
                </p>
              </div>
            </div>
          </>
        )}
      </GlassCard>

      {/* ══════════════════════════════════════════════════
          SECTION E — LIVE TRANSPILATION DIAGNOSTICS
          ══════════════════════════════════════════════════ */}
      <GlassCard
        variant="hud"
        title={
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-nexus-cyan" />
            <span>Live Transpilation Diagnostics</span>
          </div>
        }
        subtitle="Execute Qiskit transpile() against both targets and inspect compiler output"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Processor A Diagnostic */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-amber-400 font-semibold">
                Processor A (5Q)
              </span>
              <button
                onClick={() => handleRunTranspile("processor_a")}
                disabled={isTranspiling}
                className="px-2 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-400 text-[10px] font-mono flex items-center gap-1 transition-colors disabled:opacity-50"
              >
                {isTranspiling ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : (
                  <Zap className="w-3 h-3" />
                )}
                Test Compile
              </button>
            </div>
            <div className="p-3 rounded-lg bg-black/50 border border-white/8 font-mono text-[11px] space-y-1.5">
              <div className="flex justify-between">
                <span className="text-slate-500">status</span>
                <span className="text-rose-400 font-bold">FAILED</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">error_type</span>
                <span className="text-rose-400">
                  {procAResult?.error_type ?? "CircuitTooWideForTarget"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">physical_qubits</span>
                <span className="text-amber-300">
                  {procAResult?.physical_qubits ?? 5}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">logical_qubits</span>
                <span className="text-white">
                  {procAResult?.logical_qubits ?? 6}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">capacity_exceeded</span>
                <span className="text-rose-400">true</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">is_physical_qpu</span>
                <span className="text-slate-400">false</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">data_source</span>
                <span
                  className={
                    transpileSourceA === "live"
                      ? "text-emerald-400"
                      : "text-slate-400"
                  }
                >
                  {transpileSourceA === "live" ? "Live API" : "Cached Artifact"}
                </span>
              </div>
              <div className="pt-1.5 border-t border-white/5">
                <span className="text-slate-500 text-[10px]">message: </span>
                <span className="text-slate-400 text-[10px]">
                  {procAResult?.message ??
                    "Circuit width (6 qubits) exceeds physical capacity (5 qubits)."}
                </span>
              </div>
            </div>
          </div>

          {/* Processor B Diagnostic */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-nexus-cyan font-semibold">
                Processor B (9Q)
              </span>
              <button
                onClick={() => handleRunTranspile("processor_b")}
                disabled={isTranspiling}
                className="px-2 py-1 rounded bg-nexus-cyan/10 hover:bg-nexus-cyan/20 border border-nexus-cyan/30 text-nexus-cyan text-[10px] font-mono flex items-center gap-1 transition-colors disabled:opacity-50"
              >
                {isTranspiling ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : (
                  <Zap className="w-3 h-3" />
                )}
                Test Compile
              </button>
            </div>
            <div className="p-3 rounded-lg bg-black/50 border border-white/8 font-mono text-[11px] space-y-1.5">
              <div className="flex justify-between">
                <span className="text-slate-500">status</span>
                <span className="text-emerald-400 font-bold">SUCCESS</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">depth</span>
                <span className="text-white">
                  {procBResult?.depth ?? VERIFIED_TRANSPILE_B.depth}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">depth_with_meas</span>
                <span className="text-white">
                  {procBResult?.depth_with_measurements ??
                    VERIFIED_TRANSPILE_B.depthWithMeas}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">cx_count</span>
                <span className="text-nexus-cyan font-bold">
                  {procBResult?.cx_count ?? VERIFIED_TRANSPILE_B.cxCount}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">swap_count</span>
                <span className="text-emerald-400 font-bold">
                  {procBResult?.swap_count ?? VERIFIED_TRANSPILE_B.swapCount}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">total_ops</span>
                <span className="text-white">
                  {procBResult?.total_ops ?? VERIFIED_TRANSPILE_B.totalOps}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">physical_layout</span>
                <span className="text-emerald-400">
                  [
                  {(
                    procBResult?.physical_layout ?? PROC_B.logicalMapping
                  ).join(", ")}
                  ]
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">is_physical_qpu</span>
                <span className="text-slate-400">false</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">data_source</span>
                <span
                  className={
                    transpileSourceB === "live"
                      ? "text-emerald-400"
                      : "text-slate-400"
                  }
                >
                  {transpileSourceB === "live" ? "Live API" : "Cached Artifact"}
                </span>
              </div>
              <div className="pt-1.5 border-t border-white/5">
                <span className="text-slate-500 text-[10px]">ops: </span>
                <span className="text-slate-300 text-[10px]">
                  {Object.entries(
                    procBResult?.ops ?? VERIFIED_TRANSPILE_B.opsBreakdown
                  )
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(", ")}
                </span>
              </div>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* ══════════════════════════════════════════════════
          SECTION F — QUANTUM RESOURCE ANALYSIS
          ══════════════════════════════════════════════════ */}
      <GlassCard
        variant="hud"
        title={
          <div
            className="flex items-center justify-between w-full cursor-pointer"
            onClick={() => setResourceExpanded(!resourceExpanded)}
          >
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-violet-400" />
              <span>Quantum Resource Analysis</span>
            </div>
            <span className="text-xs text-slate-500 font-mono">
              {resourceExpanded ? "▼" : "▶"}
            </span>
          </div>
        }
        subtitle="Understanding logical-to-physical mapping, connectivity constraints, and transpilation overhead"
      >
        {resourceExpanded && (
          <div className="space-y-4">
            {/* Concept cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {/* Logical vs Physical Qubits */}
              <div className="p-4 rounded-lg bg-gradient-to-br from-violet-500/5 to-transparent border border-violet-500/15">
                <div className="flex items-center gap-2 mb-2">
                  <Box className="w-4 h-4 text-violet-400" />
                  <span className="text-xs font-semibold text-violet-300">
                    Logical vs Physical Qubits
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-2">
                  The VQC classifier uses{" "}
                  <span className="text-white font-medium">
                    6 logical qubits
                  </span>{" "}
                  (one per clinical feature). Physical hardware provides a fixed
                  number of qubits with constrained connectivity. If the
                  physical qubit count is less than the logical circuit width,
                  the circuit cannot be compiled at all.
                </p>
                <div className="flex items-center gap-2 text-[10px] font-mono">
                  <span className="text-amber-300">Proc A: 5 phys</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-nexus-cyan">Proc B: 9 phys</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-white">VQC: 6 logical</span>
                </div>
              </div>

              {/* Connectivity Constraints */}
              <div className="p-4 rounded-lg bg-gradient-to-br from-nexus-cyan/5 to-transparent border border-nexus-cyan/15">
                <div className="flex items-center gap-2 mb-2">
                  <Network className="w-4 h-4 text-nexus-cyan" />
                  <span className="text-xs font-semibold text-nexus-cyan">
                    Connectivity Constraints
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-2">
                  Two-qubit CX gates can only execute between{" "}
                  <span className="text-white font-medium">
                    physically connected
                  </span>{" "}
                  qubits. If a circuit requires a CX between non-adjacent
                  qubits, the transpiler must insert SWAP gates to move qubit
                  states closer, adding overhead.
                </p>
                <div className="flex items-center gap-2 text-[10px] font-mono">
                  <span className="text-amber-300">Proc A: 4 edges</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-nexus-cyan">Proc B: 8 edges</span>
                </div>
              </div>

              {/* SWAP Gate Overhead */}
              <div className="p-4 rounded-lg bg-gradient-to-br from-emerald-500/5 to-transparent border border-emerald-500/15">
                <div className="flex items-center gap-2 mb-2">
                  <ArrowRightLeft className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-semibold text-emerald-300">
                    SWAP Gate Implications
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed mb-2">
                  Each SWAP gate decomposes into{" "}
                  <span className="text-white font-medium">3 CX gates</span>,
                  significantly increasing circuit depth and noise exposure.
                  Processor B's heavy-hex topology avoids all SWAPs for this
                  circuit, yielding only{" "}
                  <span className="text-emerald-400 font-bold">
                    5 native CX
                  </span>{" "}
                  gates with{" "}
                  <span className="text-emerald-400 font-bold">0 SWAPs</span>.
                </p>
                <div className="flex items-center gap-2 text-[10px] font-mono">
                  <span className="text-emerald-400">
                    0 SWAPs → 0 extra CX
                  </span>
                </div>
              </div>
            </div>

            {/* Circuit depth analysis */}
            <div className="p-4 rounded-lg bg-white/[0.02] border border-white/8">
              <div className="flex items-center gap-2 mb-3">
                <Layers className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-semibold text-blue-300">
                  Circuit Depth & Hardware Compatibility
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[11px]">
                <div>
                  <p className="text-slate-400 leading-relaxed mb-2">
                    Circuit depth determines how many sequential gate layers are
                    required. Lower depth reduces decoherence risk on real
                    hardware (where $T_1$ and $T_2$ relaxation times are
                    finite).
                  </p>
                  <p className="text-slate-400 leading-relaxed">
                    Processor B achieves{" "}
                    <span className="text-white font-medium">depth 15</span>{" "}
                    (without measurements) for the transpiled 6-qubit VQC. This
                    is the critical-path length through the circuit's
                    decomposition into native basis gates ({PROC_B.basisGates.join(
                      ", "
                    )}
                    ).
                  </p>
                </div>
                <div>
                  <p className="text-slate-400 leading-relaxed mb-2">
                    The operation breakdown shows how the logical circuit
                    compiles into native instructions:
                  </p>
                  <div className="space-y-1.5 font-mono">
                    {Object.entries(VERIFIED_TRANSPILE_B.opsBreakdown).map(
                      ([gate, count]) => {
                        const maxCount = Math.max(
                          ...Object.values(VERIFIED_TRANSPILE_B.opsBreakdown)
                        );
                        const pct = (count / maxCount) * 100;
                        return (
                          <div key={gate} className="space-y-0.5">
                            <div className="flex justify-between text-[10px]">
                              <span className="text-slate-400 uppercase">
                                {gate}
                              </span>
                              <span className="text-white">{count} gates</span>
                            </div>
                            <div className="h-1.5 bg-black/40 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${gate === "cx" ? "bg-nexus-cyan" : "bg-violet-500/60"}`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      }
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Final hardware integrity note */}
            <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/15 flex items-start gap-2.5">
              <Info className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
              <p className="text-[11px] text-slate-400 leading-relaxed">
                <span className="font-semibold text-amber-300">
                  Hardware Integrity Summary:{" "}
                </span>
                All transpilation metrics on this page originate from Qiskit's
                software transpiler (
                <code className="text-slate-300 bg-white/5 px-1 rounded text-[10px]">
                  qiskit.transpile()
                </code>
                ) and are deterministic when using seed{" "}
                <code className="text-slate-300 bg-white/5 px-1 rounded text-[10px]">
                  42
                </code>{" "}
                and optimization level{" "}
                <code className="text-slate-300 bg-white/5 px-1 rounded text-[10px]">
                  1
                </code>
                . No physical quantum hardware execution occurred. Processor A
                and Processor B are configured simulation targets sourced from
                the Updated Challenge Kit specification, not live connections to
                IBM Quantum devices.
              </p>
            </div>
          </div>
        )}
      </GlassCard>
    </div>
  );
};
