import React, { useState } from "react";
import { Info, Sparkles } from "lucide-react";

export interface CircuitGateInfo {
  type: "ry_encoding" | "ry_var" | "cx" | "pauli_z";
  label: string;
  qubit: number;
  targetQubit?: number;
  paramName?: string;
  paramValue?: number;
  featureName?: string;
  description: string;
}

interface QuantumCircuitViewerProps {
  scaledFeatures?: number[];
  optimalTheta?: number[];
  activeFeatureName?: string;
  onSelectFeature?: (name: string) => void;
}

const FEATURE_MAPPING = [
  { index: 0, name: "pre_rr", label: "Pre-RR Interval", unit: "s", defaultAngle: 1.585 },
  { index: 1, name: "post_rr", label: "Post-RR Interval (*)", unit: "s", defaultAngle: 1.645 },
  { index: 2, name: "qrs_rms", label: "QRS RMS Voltage", unit: "mV", defaultAngle: 0.530 },
  { index: 3, name: "qrs_duration", label: "QRS Duration", unit: "s", defaultAngle: 1.093 },
  { index: 4, name: "p2p_amplitude", label: "Peak-to-Peak Amp", unit: "mV", defaultAngle: 0.612 },
  { index: 5, name: "spectral_ratio", label: "Spectral Ratio", unit: "ratio", defaultAngle: 1.505 },
];

const DEFAULT_THETA = [
  0.4889, -1.2636, -0.4962, -0.9823, -0.8178, -0.7964,
  -0.3341, -0.3669, -0.8661, -1.0348, 0.5614, 0.4214
];

export const QuantumCircuitViewer: React.FC<QuantumCircuitViewerProps> = ({
  scaledFeatures,
  optimalTheta = DEFAULT_THETA,
  activeFeatureName,
  onSelectFeature,
}) => {
  const [hoveredGate, setHoveredGate] = useState<CircuitGateInfo | null>(null);

  // Layout parameters for responsive SVG
  const SVG_WIDTH = 920;
  const SVG_HEIGHT = 380;
  const MARGIN_LEFT = 110;
  const WIRE_SPACING = 52;
  const START_Y = 55;

  // Horizontal column coordinates for each architectural stage
  const COL_ENCODING = 160;   // RY(x_i)
  const COL_VAR_INIT = 280;   // RY(theta_0..5)
  const COL_CX_START = 400;   // 5 CX ladder
  const CX_STEP = 32;         // Staggered CX steps
  const COL_VAR_FINAL = 620;  // RY(theta_6..11)
  const COL_MEASURE = 740;    // Pauli-Z
  const COL_BUS = 820;        // Ensemble Observable Bus

  const getWireY = (q: number) => START_Y + q * WIRE_SPACING;

  return (
    <div className="space-y-3">
      {/* Circuit Metadata Bar & Interactive Hover HUD */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-nexus-card border border-white/10 text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-black/50 border border-white/10">
            <span className="text-slate-400">ARCH:</span>
            <span className="text-nexus-cyan font-bold">6 Qubits</span>
            <span className="text-slate-600">·</span>
            <span className="text-slate-400">ANSATZ:</span>
            <span className="text-emerald-400 font-bold">RealAmplitudes (reps=1)</span>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-black/50 border border-white/10">
            <span className="text-slate-400">ENTANGLEMENT:</span>
            <span className="text-violet-300 font-bold">5 CX (Linear)</span>
            <span className="text-slate-600">·</span>
            <span className="text-slate-400">WEIGHTS:</span>
            <span className="text-pink-400 font-bold">12 θ (Frozen)</span>
          </div>
        </div>

        {/* Hover Inspector Pill */}
        <div className="flex items-center gap-2">
          {hoveredGate ? (
            <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-nexus-blue/20 border border-nexus-blue/50 text-white animate-in fade-in duration-150">
              <Sparkles className="w-3.5 h-3.5 text-nexus-cyan" />
              <span className="font-bold text-nexus-cyan">{hoveredGate.label}:</span>
              <span className="text-slate-200">{hoveredGate.description}</span>
              {hoveredGate.paramValue !== undefined && (
                <span className="px-1.5 py-0.5 rounded bg-black/60 text-amber-300 border border-amber-500/30">
                  {hoveredGate.paramValue.toFixed(4)} rad
                </span>
              )}
            </div>
          ) : (
            <div className="text-slate-500 text-[11px] flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-slate-500" />
              <span>Hover over any quantum gate to inspect rotational angle & unitary action</span>
            </div>
          )}
        </div>
      </div>

      {/* Primary SVG Canvas: 6-Qubit Hardware-Accurate Circuit Diagram */}
      <div className="relative rounded-xl border border-nexus-cyan/30 bg-nexus-black/95 overflow-hidden shadow-2xl p-2">
        <svg
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
          className="w-full h-auto select-none block"
        >
          <defs>
            {/* Gate Gradients */}
            <linearGradient id="encodingGateGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#0891B2" />
              <stop offset="100%" stopColor="#0E7490" />
            </linearGradient>

            <linearGradient id="varGateGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#7C3AED" />
              <stop offset="100%" stopColor="#5B21B6" />
            </linearGradient>

            <linearGradient id="measureGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#059669" />
              <stop offset="100%" stopColor="#047857" />
            </linearGradient>

            {/* Glowing Drop Shadows */}
            <filter id="cyanGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Background Stage Columns (Visual Architectural Bands) */}
          {/* Stage 1: Encoding */}
          <rect
            x={COL_ENCODING - 35}
            y={20}
            width={70}
            height={SVG_HEIGHT - 35}
            rx={8}
            fill="#06B6D4"
            fillOpacity="0.04"
            stroke="#06B6D4"
            strokeOpacity="0.15"
            strokeDasharray="3 3"
          />
          <text
            x={COL_ENCODING}
            y={32}
            textAnchor="middle"
            fill="#06B6D4"
            fontSize="9"
            fontFamily="monospace"
            fontWeight="bold"
          >
            STAGE 1: RY(x) ENCODING
          </text>

          {/* Stage 2: Variational Ansatz Box */}
          <rect
            x={COL_VAR_INIT - 35}
            y={20}
            width={COL_VAR_FINAL - COL_VAR_INIT + 70}
            height={SVG_HEIGHT - 35}
            rx={8}
            fill="#8B5CF6"
            fillOpacity="0.03"
            stroke="#8B5CF6"
            strokeOpacity="0.2"
          />
          <text
            x={(COL_VAR_INIT + COL_VAR_FINAL) / 2}
            y={32}
            textAnchor="middle"
            fill="#A78BFA"
            fontSize="9"
            fontFamily="monospace"
            fontWeight="bold"
          >
            STAGE 2: REALAMPLITUDES VARIATIONAL ANSATZ (reps=1, 12 θ Parameters, 5 CX)
          </text>

          {/* Stage 3: Measurement */}
          <rect
            x={COL_MEASURE - 30}
            y={20}
            width={SVG_WIDTH - COL_MEASURE + 10}
            height={SVG_HEIGHT - 35}
            rx={8}
            fill="#10B981"
            fillOpacity="0.04"
            stroke="#10B981"
            strokeOpacity="0.2"
            strokeDasharray="3 3"
          />
          <text
            x={COL_MEASURE + 25}
            y={32}
            textAnchor="middle"
            fill="#10B981"
            fontSize="9"
            fontFamily="monospace"
            fontWeight="bold"
          >
            STAGE 3: ENSEMBLE OBSERVABLE
          </text>

          {/* 6 Qubit Quantum Wires & State Labels */}
          {FEATURE_MAPPING.map((feat, q) => {
            const y = getWireY(q);
            const isSelected = activeFeatureName === feat.name;

            return (
              <g key={`wire-${q}`}>
                {/* Left Qubit Identifier & State Pill */}
                <g
                  className="cursor-pointer"
                  onClick={() => onSelectFeature && onSelectFeature(feat.name)}
                >
                  <rect
                    x={10}
                    y={y - 18}
                    width={88}
                    height={36}
                    rx={6}
                    fill={isSelected ? "#0F2942" : "#090E1A"}
                    stroke={isSelected ? "#00F0FF" : "rgba(255, 255, 255, 0.12)"}
                    strokeWidth={isSelected ? 1.5 : 1}
                  />
                  <text
                    x={20}
                    y={y - 2}
                    fill={isSelected ? "#00F0FF" : "#F8FAFC"}
                    fontSize="10"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    q[{q}]: |0⟩
                  </text>
                  <text
                    x={20}
                    y={y + 11}
                    fill={isSelected ? "#38BDF8" : "#94A3B8"}
                    fontSize="8.5"
                    fontFamily="monospace"
                  >
                    {feat.name}
                  </text>
                </g>

                {/* Horizontal Superconducting Qubit Rail */}
                <line
                  x1={MARGIN_LEFT}
                  y1={y}
                  x2={COL_MEASURE + 25}
                  y2={y}
                  stroke={isSelected ? "#00F0FF" : "#334155"}
                  strokeWidth={isSelected ? 1.8 : 1.2}
                />

                {/* --- 1. RY Feature Encoding Gate: RY(x_i) --- */}
                {(() => {
                  const angle = scaledFeatures && scaledFeatures[q] !== undefined
                    ? scaledFeatures[q]
                    : feat.defaultAngle;
                  return (
                    <g
                      className="cursor-pointer"
                      onMouseEnter={() =>
                        setHoveredGate({
                          type: "ry_encoding",
                          label: `RY(x_${q}) Encoding Gate`,
                          qubit: q,
                          featureName: feat.name,
                          paramValue: angle,
                          description: `Maps scaled biomarker ${feat.name} to rotation angle on Bloch sphere [0, π].`,
                        })
                      }
                      onMouseLeave={() => setHoveredGate(null)}
                      onClick={() => onSelectFeature && onSelectFeature(feat.name)}
                    >
                      <rect
                        x={COL_ENCODING - 24}
                        y={y - 16}
                        width={48}
                        height={32}
                        rx={5}
                        fill="url(#encodingGateGrad)"
                        stroke="#22D3EE"
                        strokeWidth="1.2"
                        className="hover:filter hover:drop-shadow-[0_0_8px_#00F0FF]"
                      />
                      <text
                        x={COL_ENCODING}
                        y={y - 2}
                        textAnchor="middle"
                        fill="#FFFFFF"
                        fontSize="9"
                        fontFamily="monospace"
                        fontWeight="bold"
                      >
                        RY
                      </text>
                      <text
                        x={COL_ENCODING}
                        y={y + 10}
                        textAnchor="middle"
                        fill="#A5F3FC"
                        fontSize="7.5"
                        fontFamily="monospace"
                      >
                        x[{q}]
                      </text>
                    </g>
                  );
                })()}

                {/* --- 2.1 Initial Variational Rotation: RY(theta_i) --- */}
                {(() => {
                  const thetaVal = optimalTheta[q];
                  return (
                    <g
                      className="cursor-pointer"
                      onMouseEnter={() =>
                        setHoveredGate({
                          type: "ry_var",
                          label: `Ansatz Initial RY(θ_${q})`,
                          qubit: q,
                          paramName: `θ_${q}`,
                          paramValue: thetaVal,
                          description: `Trainable variational parameter θ_${q} (Fold 1 Seed 303 Checkpoint).`,
                        })
                      }
                      onMouseLeave={() => setHoveredGate(null)}
                    >
                      <rect
                        x={COL_VAR_INIT - 24}
                        y={y - 16}
                        width={48}
                        height={32}
                        rx={5}
                        fill="url(#varGateGrad)"
                        stroke="#A78BFA"
                        strokeWidth="1.2"
                        className="hover:filter hover:drop-shadow-[0_0_8px_#8B5CF6]"
                      />
                      <text
                        x={COL_VAR_INIT}
                        y={y - 2}
                        textAnchor="middle"
                        fill="#FFFFFF"
                        fontSize="9"
                        fontFamily="monospace"
                        fontWeight="bold"
                      >
                        RY
                      </text>
                      <text
                        x={COL_VAR_INIT}
                        y={y + 10}
                        textAnchor="middle"
                        fill="#DDD6FE"
                        fontSize="7.5"
                        fontFamily="monospace"
                      >
                        θ_{q}
                      </text>
                    </g>
                  );
                })()}

                {/* --- 2.3 Final Variational Rotation: RY(theta_{i+6}) --- */}
                {(() => {
                  const paramIdx = q + 6;
                  const thetaVal = optimalTheta[paramIdx];
                  return (
                    <g
                      className="cursor-pointer"
                      onMouseEnter={() =>
                        setHoveredGate({
                          type: "ry_var",
                          label: `Ansatz Final RY(θ_${paramIdx})`,
                          qubit: q,
                          paramName: `θ_${paramIdx}`,
                          paramValue: thetaVal,
                          description: `Trainable variational parameter θ_${paramIdx} after entangling ladder.`,
                        })
                      }
                      onMouseLeave={() => setHoveredGate(null)}
                    >
                      <rect
                        x={COL_VAR_FINAL - 24}
                        y={y - 16}
                        width={48}
                        height={32}
                        rx={5}
                        fill="url(#varGateGrad)"
                        stroke="#A78BFA"
                        strokeWidth="1.2"
                        className="hover:filter hover:drop-shadow-[0_0_8px_#8B5CF6]"
                      />
                      <text
                        x={COL_VAR_FINAL}
                        y={y - 2}
                        textAnchor="middle"
                        fill="#FFFFFF"
                        fontSize="9"
                        fontFamily="monospace"
                        fontWeight="bold"
                      >
                        RY
                      </text>
                      <text
                        x={COL_VAR_FINAL}
                        y={y + 10}
                        textAnchor="middle"
                        fill="#DDD6FE"
                        fontSize="7.5"
                        fontFamily="monospace"
                      >
                        θ_{paramIdx}
                      </text>
                    </g>
                  );
                })()}

                {/* --- 3. Pauli-Z Measurement Gate --- */}
                <g
                  className="cursor-pointer"
                  onMouseEnter={() =>
                    setHoveredGate({
                      type: "pauli_z",
                      label: `Observable Component Z_${q}`,
                      qubit: q,
                      description: `Evaluates projection ⟨Z_${q}⟩. Contributes 1/6th to ensemble observable Ô.`,
                    })
                  }
                  onMouseLeave={() => setHoveredGate(null)}
                >
                  <rect
                    x={COL_MEASURE - 18}
                    y={y - 16}
                    width={36}
                    height={32}
                    rx={5}
                    fill="url(#measureGrad)"
                    stroke="#34D399"
                    strokeWidth="1.2"
                  />
                  <text
                    x={COL_MEASURE}
                    y={y + 5}
                    textAnchor="middle"
                    fill="#FFFFFF"
                    fontSize="12"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    Z
                  </text>

                  {/* Measurement connection line to ensemble collector */}
                  <line
                    x1={COL_MEASURE + 18}
                    y1={y}
                    x2={COL_BUS}
                    y2={y}
                    stroke="#10B981"
                    strokeWidth="1.2"
                    strokeDasharray="2 2"
                  />
                  <circle cx={COL_BUS} cy={y} r="3" fill="#10B981" />
                </g>
              </g>
            );
          })}

          {/* --- 2.2 Linear Entanglement Ladder: 5 Staggered CX Gates --- */}
          {/* CX(0->1), CX(1->2), CX(2->3), CX(3->4), CX(4->5) */}
          {[0, 1, 2, 3, 4].map((ctrl) => {
            const target = ctrl + 1;
            const cxX = COL_CX_START + ctrl * CX_STEP;
            const ctrlY = getWireY(ctrl);
            const targetY = getWireY(target);

            return (
              <g
                key={`cx-${ctrl}-${target}`}
                className="cursor-pointer"
                onMouseEnter={() =>
                  setHoveredGate({
                    type: "cx",
                    label: `Entangling CX(${ctrl}, ${target})`,
                    qubit: ctrl,
                    targetQubit: target,
                    description: `Controlled-NOT unitary generating quantum entanglement between q[${ctrl}] and q[${target}].`,
                  })
                }
                onMouseLeave={() => setHoveredGate(null)}
              >
                {/* Vertical Coupling Line */}
                <line
                  x1={cxX}
                  y1={ctrlY}
                  x2={cxX}
                  y2={targetY}
                  stroke="#38BDF8"
                  strokeWidth="1.5"
                />

                {/* Control Dot on Source Qubit */}
                <circle cx={cxX} cy={ctrlY} r="5" fill="#38BDF8" />

                {/* Target Plus-in-Circle on Destination Qubit */}
                <circle
                  cx={cxX}
                  cy={targetY}
                  r="10"
                  fill="#090E1A"
                  stroke="#38BDF8"
                  strokeWidth="1.5"
                  className="hover:stroke-white"
                />
                <line
                  x1={cxX - 7}
                  y1={targetY}
                  x2={cxX + 7}
                  y2={targetY}
                  stroke="#38BDF8"
                  strokeWidth="1.5"
                />
                <line
                  x1={cxX}
                  y1={targetY - 7}
                  x2={cxX}
                  y2={targetY + 7}
                  stroke="#38BDF8"
                  strokeWidth="1.5"
                />
              </g>
            );
          })}

          {/* Observable Ensemble Bus Line & Formula Badge */}
          <line
            x1={COL_BUS}
            y1={getWireY(0)}
            x2={COL_BUS}
            y2={getWireY(5)}
            stroke="#10B981"
            strokeWidth="2.5"
          />

          {/* Ensemble Observable Node */}
          <g transform={`translate(${COL_BUS + 12}, ${START_Y + 2.5 * WIRE_SPACING - 30})`}>
            <rect
              x={0}
              y={0}
              width={75}
              height={60}
              rx={8}
              fill="#062E25"
              stroke="#10B981"
              strokeWidth="1.5"
              className="filter drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]"
            />
            <text
              x={37.5}
              y={18}
              textAnchor="middle"
              fill="#6EE7B7"
              fontSize="9"
              fontFamily="monospace"
              fontWeight="bold"
            >
              OBSERVABLE
            </text>
            <text
              x={37.5}
              y={34}
              textAnchor="middle"
              fill="#FFFFFF"
              fontSize="11"
              fontFamily="monospace"
              fontWeight="bold"
            >
              Ô = ⅙ ∑ Z_i
            </text>
            <text
              x={37.5}
              y={50}
              textAnchor="middle"
              fill="#A7F3D0"
              fontSize="8"
              fontFamily="monospace"
            >
              ⟨Ô⟩ ∈ [-1, +1]
            </text>
          </g>
        </svg>
      </div>

      {/* Structural Schema Legend / Proof of Fidelity */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-400 px-2">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-cyan-600 border border-cyan-400" />
            <span>Feature Encoding (RY)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-purple-700 border border-purple-400" />
            <span>Variational Weights (12 θ)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
            <span className="text-sky-300">Entangling CX (5 linear)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-emerald-700 border border-emerald-400" />
            <span>Pauli-Z Observable (Ô)</span>
          </div>
        </div>

        <div className="text-slate-500 text-[10px]">
          * Exact algorithmic circuit geometry executed in Qiskit EstimatorV2 & AerSimulator.
        </div>
      </div>
    </div>
  );
};
