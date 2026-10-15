import React, { useState, useRef, useMemo } from "react";
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Crosshair,
  ChevronLeft,
  ChevronRight,
  Grid,
  Ruler,
} from "lucide-react";

interface InteractiveEcgViewerProps {
  signalSamples: number[];
  rPeakSample: number;
  samplingRate?: number;
  label: number;
  annotationSymbol: string;
  segmentId: string;
  leadName?: string;
  isLive?: boolean;
  isLoading?: boolean;
  notes?: string;
}

export const InteractiveEcgViewer: React.FC<InteractiveEcgViewerProps> = ({
  signalSamples,
  rPeakSample = 144,
  samplingRate = 360,
  label,
  annotationSymbol,
  segmentId,
  leadName = "MLII",
  isLive = false,
  isLoading = false,
  notes,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Zoom & Pan state
  const [zoomLevel, setZoomLevel] = useState<number>(1.0); // 1.0x to 5.0x
  const [panIndex, setPanIndex] = useState<number>(0); // Start sample index for visible window

  // Grid theme: "cyber" or "clinical"
  const [gridTheme, setGridTheme] = useState<"cyber" | "clinical">("cyber");

  // Caliper measurement tool: click 2 points to measure dt and dV
  const [caliperActive, setCaliperActive] = useState<boolean>(false);
  const [caliperP1, setCaliperP1] = useState<{ index: number; timeMs: number; voltageMv: number } | null>(null);
  const [caliperP2, setCaliperP2] = useState<{ index: number; timeMs: number; voltageMv: number } | null>(null);

  // Hover inspection cursor
  const [hoveredSample, setHoveredSample] = useState<{
    index: number;
    timeMs: number;
    voltageMv: number;
    offsetFromRMs: number;
    svgX: number;
    svgY: number;
  } | null>(null);

  const totalSamples = signalSamples.length > 0 ? signalSamples.length : 360;
  const isVEB = label === 1;

  // Visible sample window calculation based on zoom and pan
  const visibleCount = Math.max(36, Math.min(totalSamples, Math.round(totalSamples / zoomLevel)));
  const maxPan = Math.max(0, totalSamples - visibleCount);
  const clampedPan = Math.max(0, Math.min(maxPan, panIndex));
  const endIndex = Math.min(totalSamples - 1, clampedPan + visibleCount - 1);

  // Voltage range calculation with padding
  const { minVoltage, maxVoltage, voltageSpan } = useMemo(() => {
    if (!signalSamples || signalSamples.length === 0) {
      return { minVoltage: -1.0, maxVoltage: 2.0, voltageSpan: 3.0 };
    }
    const visibleSlice = signalSamples.slice(clampedPan, endIndex + 1);
    const minVal = Math.min(...visibleSlice);
    const maxVal = Math.max(...visibleSlice);
    const padding = Math.max(0.2, (maxVal - minVal) * 0.15);
    const vMin = Math.floor((minVal - padding) * 2) / 2; // Snap to 0.5 mV steps
    const vMax = Math.ceil((maxVal + padding) * 2) / 2;
    return {
      minVoltage: vMin,
      maxVoltage: vMax,
      voltageSpan: Math.max(1.0, vMax - vMin),
    };
  }, [signalSamples, clampedPan, endIndex]);

  // SVG Dimension Constants
  const SVG_WIDTH = 900;
  const SVG_HEIGHT = 280;
  const PADDING_LEFT = 60;
  const PADDING_RIGHT = 30;
  const PADDING_TOP = 25;
  const PADDING_BOTTOM = 40;
  const PLOT_WIDTH = SVG_WIDTH - PADDING_LEFT - PADDING_RIGHT;
  const PLOT_HEIGHT = SVG_HEIGHT - PADDING_TOP - PADDING_BOTTOM;

  // Coordinate mapping functions
  const sampleToX = (sampleIdx: number) => {
    if (visibleCount <= 1) return PADDING_LEFT;
    const fraction = (sampleIdx - clampedPan) / (visibleCount - 1);
    return PADDING_LEFT + fraction * PLOT_WIDTH;
  };

  const voltageToY = (volts: number) => {
    const fraction = (volts - minVoltage) / voltageSpan;
    return SVG_HEIGHT - PADDING_BOTTOM - fraction * PLOT_HEIGHT;
  };

  const xToSample = (svgX: number) => {
    const clampedX = Math.max(PADDING_LEFT, Math.min(SVG_WIDTH - PADDING_RIGHT, svgX));
    const fraction = (clampedX - PADDING_LEFT) / PLOT_WIDTH;
    const sampleIdx = Math.round(clampedPan + fraction * (visibleCount - 1));
    return Math.max(0, Math.min(totalSamples - 1, sampleIdx));
  };

  // Generate SVG path for the visible waveform
  const waveformPath = useMemo(() => {
    if (!signalSamples || signalSamples.length === 0) return "";
    let d = "";
    for (let i = clampedPan; i <= endIndex; i++) {
      const x = sampleToX(i);
      const y = voltageToY(signalSamples[i]);
      d += `${i === clampedPan ? "M" : "L"} ${x.toFixed(2)},${y.toFixed(2)} `;
    }
    return d;
  }, [signalSamples, clampedPan, endIndex, minVoltage, voltageSpan]);

  // Generate Grid lines (Standard ECG Medical Paper: 0.5 mV and 0.1 mV / 200 ms and 40 ms)
  const gridLines = useMemo(() => {
    const horizontal: { y: number; voltage: number; isMajor: boolean }[] = [];
    const vertical: { x: number; sampleIdx: number; timeMs: number; isMajor: boolean }[] = [];

    // Horizontal Voltage lines every 0.1 mV, major every 0.5 mV
    const startV = Math.ceil(minVoltage / 0.1) * 0.1;
    for (let v = startV; v <= maxVoltage + 0.05; v += 0.1) {
      const roundedV = Math.round(v * 10) / 10;
      const isMajor = Math.abs(roundedV % 0.5) < 0.01 || Math.abs(roundedV % 0.5 - 0.5) < 0.01;
      const y = voltageToY(roundedV);
      if (y >= PADDING_TOP && y <= SVG_HEIGHT - PADDING_BOTTOM) {
        horizontal.push({ y, voltage: roundedV, isMajor });
      }
    }

    // Vertical Time lines every 40 ms (14.4 samples), major every 200 ms (72 samples)
    for (let i = 0; i < totalSamples; i += 14.4) {
      const roundedIdx = Math.round(i);
      if (roundedIdx >= clampedPan && roundedIdx <= endIndex) {
        const timeMs = (roundedIdx / samplingRate) * 1000;
        const isMajor = Math.abs((timeMs % 200)) < 15 || Math.abs(timeMs % 200 - 200) < 15;
        vertical.push({
          x: sampleToX(roundedIdx),
          sampleIdx: roundedIdx,
          timeMs: Math.round(timeMs),
          isMajor,
        });
      }
    }

    return { horizontal, vertical };
  }, [minVoltage, maxVoltage, clampedPan, endIndex, samplingRate, voltageSpan]);

  // Handle SVG Mouse Move for Inspection and Calipers
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!signalSamples || signalSamples.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const svgX = (clientX / rect.width) * SVG_WIDTH;

    if (svgX < PADDING_LEFT || svgX > SVG_WIDTH - PADDING_RIGHT) {
      setHoveredSample(null);
      return;
    }

    const sampleIdx = xToSample(svgX);
    const voltageMv = signalSamples[sampleIdx];
    const timeMs = (sampleIdx / samplingRate) * 1000;
    const offsetFromRMs = ((sampleIdx - rPeakSample) / samplingRate) * 1000;
    const exactSvgX = sampleToX(sampleIdx);
    const exactSvgY = voltageToY(voltageMv);

    setHoveredSample({
      index: sampleIdx,
      timeMs,
      voltageMv,
      offsetFromRMs,
      svgX: exactSvgX,
      svgY: exactSvgY,
    });
  };

  const handleMouseLeave = () => {
    setHoveredSample(null);
  };

  // Handle Caliper clicks
  const handleSvgClick = () => {
    if (!caliperActive || !hoveredSample) return;
    if (!caliperP1) {
      setCaliperP1({
        index: hoveredSample.index,
        timeMs: hoveredSample.timeMs,
        voltageMv: hoveredSample.voltageMv,
      });
    } else if (!caliperP2) {
      setCaliperP2({
        index: hoveredSample.index,
        timeMs: hoveredSample.timeMs,
        voltageMv: hoveredSample.voltageMv,
      });
    } else {
      // Reset calipers to point 1 on next click
      setCaliperP1({
        index: hoveredSample.index,
        timeMs: hoveredSample.timeMs,
        voltageMv: hoveredSample.voltageMv,
      });
      setCaliperP2(null);
    }
  };

  // Zoom preset helper
  const handleSetZoom = (level: number) => {
    const clampedLevel = Math.max(1.0, Math.min(5.0, level));
    setZoomLevel(clampedLevel);

    // Keep R-peak in view if zooming in
    const newVisible = Math.round(totalSamples / clampedLevel);
    const targetPan = Math.max(0, Math.min(totalSamples - newVisible, rPeakSample - Math.round(newVisible / 2)));
    setPanIndex(targetPan);
  };

  const handleCenterRPeak = () => {
    const newPan = Math.max(0, Math.min(maxPan, rPeakSample - Math.round(visibleCount / 2)));
    setPanIndex(newPan);
  };

  const handleReset = () => {
    setZoomLevel(1.0);
    setPanIndex(0);
    setCaliperP1(null);
    setCaliperP2(null);
  };

  // Color schemes
  const traceColor = isVEB ? "#EC4899" : "#00F0FF";
  const glowFilter = isVEB
    ? "drop-shadow(0px 0px 8px rgba(236, 72, 153, 0.8))"
    : "drop-shadow(0px 0px 8px rgba(0, 240, 255, 0.8))";

  const gridColorMajor =
    gridTheme === "clinical" ? "rgba(239, 68, 68, 0.35)" : "rgba(0, 240, 255, 0.15)";
  const gridColorMinor =
    gridTheme === "clinical" ? "rgba(239, 68, 68, 0.12)" : "rgba(255, 255, 255, 0.04)";

  // Caliper delta calculations
  const caliperDelta = useMemo(() => {
    if (!caliperP1 || !caliperP2) return null;
    const dt = Math.abs(caliperP2.timeMs - caliperP1.timeMs);
    const dv = Math.abs(caliperP2.voltageMv - caliperP1.voltageMv);
    const dSamples = Math.abs(caliperP2.index - caliperP1.index);
    const bpm = dt > 0 ? Math.round(60000 / dt) : 0;
    // Distinguish plausible cardiac cycles (300-2000 ms, 30-200 BPM) from arbitrary intervals (QRS, PR, etc.)
    const isPlausibleRrInterval = dt >= 300 && dt <= 2000;
    return { dt, dv, dSamples, bpm, isPlausibleRrInterval };
  }, [caliperP1, caliperP2]);

  return (
    <div className="space-y-3" ref={containerRef}>
      {/* Top Interactive Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 p-3 rounded-xl bg-nexus-card border border-white/10 text-xs font-mono">
        {/* Left: Waveform Identity & Lead */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-black/50 border border-white/10">
            <span className="text-slate-400">LEAD:</span>
            <span className="text-nexus-cyan font-bold">{leadName}</span>
            <span className="text-slate-600">·</span>
            <span className="text-slate-400">FS:</span>
            <span className="text-emerald-400 font-bold">{samplingRate} Hz</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-black/50 border border-white/10">
            <span className="text-slate-400">VISIBLE:</span>
            <span className="text-white font-bold">
              {((visibleCount / samplingRate) * 1000).toFixed(0)} ms
            </span>
            <span className="text-slate-500">({visibleCount} samples)</span>
          </div>

          {isLive ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/40">
              <span className="w-1.5 h-1.5 rounded-full bg-nexus-cyan animate-pulse" />
              API LIVE (/api/ecg/{segmentId})
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
              API CACHED (Audited Waveform)
            </span>
          )}
        </div>

        {/* Right: Zoom & Inspection Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Zoom Buttons */}
          <div className="flex items-center rounded-lg bg-black/60 border border-white/10 p-0.5">
            <button
              onClick={() => handleSetZoom(zoomLevel - 0.5)}
              disabled={zoomLevel <= 1.0}
              className="p-1.5 hover:text-nexus-cyan disabled:opacity-30 disabled:hover:text-inherit transition-colors cursor-pointer"
              title="Zoom Out (-)"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-2 font-bold text-nexus-cyan text-[11px] min-w-[36px] text-center">
              {zoomLevel.toFixed(1)}x
            </span>
            <button
              onClick={() => handleSetZoom(zoomLevel + 0.5)}
              disabled={zoomLevel >= 5.0}
              className="p-1.5 hover:text-nexus-cyan disabled:opacity-30 disabled:hover:text-inherit transition-colors cursor-pointer"
              title="Zoom In (+)"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Preset Buttons */}
          <div className="hidden sm:flex items-center gap-1">
            {[1.0, 2.0, 4.0].map((preset) => (
              <button
                key={preset}
                onClick={() => handleSetZoom(preset)}
                className={`px-2 py-1 rounded text-[10px] cursor-pointer transition-colors ${
                  Math.abs(zoomLevel - preset) < 0.1
                    ? "bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/40"
                    : "bg-white/[0.04] text-slate-400 hover:text-white"
                }`}
              >
                {preset === 1.0 ? "1x (Full)" : preset === 2.0 ? "2x (500ms)" : "4x (QRS)"}
              </button>
            ))}
          </div>

          {/* Center R-Peak */}
          <button
            onClick={handleCenterRPeak}
            className="px-2 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-[11px] flex items-center gap-1 border border-white/10 cursor-pointer"
            title="Pan to center of R-Peak"
          >
            <Crosshair className="w-3 h-3 text-nexus-cyan" />
            <span>Center R</span>
          </button>

          {/* Caliper Tool Toggle */}
          <button
            onClick={() => {
              setCaliperActive(!caliperActive);
              if (caliperActive) {
                setCaliperP1(null);
                setCaliperP2(null);
              }
            }}
            className={`px-2 py-1 rounded text-[11px] flex items-center gap-1 border cursor-pointer transition-colors ${
              caliperActive
                ? "bg-nexus-violet/30 border-nexus-violet text-nexus-violet shadow-glow-violet-sm"
                : "bg-white/[0.04] border-white/10 text-slate-400 hover:text-white"
            }`}
            title="Click to toggle caliper measurement between 2 points"
          >
            <Ruler className="w-3 h-3" />
            <span>{caliperActive ? "Calipers Active" : "Calipers"}</span>
          </button>

          {/* Grid Toggle */}
          <button
            onClick={() => setGridTheme(gridTheme === "cyber" ? "clinical" : "cyber")}
            className="p-1.5 rounded bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-white border border-white/10 cursor-pointer"
            title={`Switch to ${gridTheme === "cyber" ? "Clinical ECG Paper Grid" : "Cyber HUD Grid"}`}
          >
            <Grid className={`w-3.5 h-3.5 ${gridTheme === "clinical" ? "text-pink-400" : "text-nexus-cyan"}`} />
          </button>

          {/* Reset */}
          <button
            onClick={handleReset}
            className="p-1.5 rounded bg-white/[0.04] hover:bg-white/[0.08] text-slate-400 hover:text-white border border-white/10 cursor-pointer"
            title="Reset Zoom & Pan (1.0x)"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Waveform Canvas Container */}
      <div className="relative rounded-xl border border-nexus-cyan/30 bg-nexus-black/95 overflow-hidden shadow-2xl">
        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 z-40 bg-nexus-black/75 backdrop-blur-xs flex items-center justify-center">
            <div className="flex items-center gap-2 font-mono text-xs text-nexus-cyan">
              <span className="w-3 h-3 rounded-full border-2 border-nexus-cyan border-t-transparent animate-spin" />
              <span>Fetching live 360-sample waveform from /api/ecg/{segmentId}...</span>
            </div>
          </div>
        )}

        {/* Live Cursor Inspection Floating HUD */}
        {hoveredSample && (
          <div
            className="absolute top-2.5 right-3 z-30 pointer-events-none px-3 py-2 rounded-lg bg-black/90 border border-nexus-cyan/40 backdrop-blur-md shadow-xl font-mono text-[11px] flex items-center gap-4 animate-in fade-in duration-100"
          >
            <div>
              <span className="text-slate-500 block text-[9px]">SAMPLE</span>
              <span className="text-white font-bold">#{hoveredSample.index}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[9px]">TIME (t)</span>
              <span className="text-nexus-cyan font-bold">{hoveredSample.timeMs.toFixed(1)} ms</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[9px]">VOLTAGE (V)</span>
              <span
                className={`font-bold ${
                  hoveredSample.voltageMv >= 0 ? "text-emerald-400" : "text-pink-400"
                }`}
              >
                {(hoveredSample.voltageMv >= 0 ? "+" : "") + hoveredSample.voltageMv.toFixed(3)} mV
              </span>
            </div>
            <div>
              <span className="text-slate-500 block text-[9px]">Δt TO R-PEAK</span>
              <span className="text-violet-300 font-bold">
                {(hoveredSample.offsetFromRMs >= 0 ? "+" : "") + hoveredSample.offsetFromRMs.toFixed(1)} ms
              </span>
            </div>
          </div>
        )}

        {/* Caliper Measurement Result Banner */}
        {caliperDelta && (
          <div className="absolute bottom-12 left-16 z-30 px-3 py-1.5 rounded-lg bg-violet-950/90 border border-violet-500/50 backdrop-blur-md font-mono text-[11px] text-violet-200 flex items-center gap-3 shadow-lg">
            <span className="font-bold text-white flex items-center gap-1">
              <Ruler className="w-3 h-3 text-nexus-violet" />
              <span>Caliper Measurement:</span>
            </span>
            <span>
              Δt: <strong className="text-nexus-cyan">{caliperDelta.dt.toFixed(1)} ms</strong> ({caliperDelta.dSamples} samples)
            </span>
            <span>
              ΔV: <strong className="text-pink-400">{caliperDelta.dv.toFixed(3)} mV</strong>
            </span>
            {caliperDelta.isPlausibleRrInterval ? (
              <span className="text-emerald-300 border-l border-violet-700/60 pl-2">
                Equiv. Rate (if R-R cycle): <strong>{caliperDelta.bpm} BPM</strong>
              </span>
            ) : (
              <span className="text-slate-400 border-l border-violet-700/60 pl-2 text-[10px]">
                Arbitrary Interval (not an R-R cycle)
              </span>
            )}
            <button
              onClick={() => {
                setCaliperP1(null);
                setCaliperP2(null);
              }}
              className="text-[10px] text-violet-400 hover:text-white underline ml-1 cursor-pointer"
            >
              Clear
            </button>
          </div>
        )}

        {/* Primary Interactive SVG Canvas */}
        <svg
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
          className="w-full h-auto cursor-crosshair select-none block"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          onClick={handleSvgClick}
        >
          <defs>
            {/* Linear Glow Gradients */}
            <linearGradient id="normalGlow" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#00F0FF" />
              <stop offset="50%" stopColor="#10B981" />
              <stop offset="100%" stopColor="#00F0FF" />
            </linearGradient>

            <linearGradient id="vebGlow" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#EC4899" />
              <stop offset="50%" stopColor="#F43F5E" />
              <stop offset="100%" stopColor="#8B5CF6" />
            </linearGradient>

            {/* Minor grid pattern */}
            <pattern
              id="gridSubdivision"
              width="14.4"
              height="10"
              patternUnits="userSpaceOnUse"
            >
              <line
                x1="0"
                y1="0"
                x2="14.4"
                y2="0"
                stroke={gridColorMinor}
                strokeWidth="0.5"
              />
              <line
                x1="0"
                y1="0"
                x2="0"
                y2="10"
                stroke={gridColorMinor}
                strokeWidth="0.5"
              />
            </pattern>
          </defs>

          {/* Background medical grid fill */}
          <rect
            x={PADDING_LEFT}
            y={PADDING_TOP}
            width={PLOT_WIDTH}
            height={PLOT_HEIGHT}
            fill="url(#gridSubdivision)"
          />

          {/* Horizontal Voltage Grid Lines & Labels */}
          {gridLines.horizontal.map((line, idx) => (
            <g key={`h-${idx}`}>
              <line
                x1={PADDING_LEFT}
                y1={line.y}
                x2={SVG_WIDTH - PADDING_RIGHT}
                y2={line.y}
                stroke={
                  line.voltage === 0.0
                    ? "rgba(0, 240, 255, 0.45)"
                    : line.isMajor
                    ? gridColorMajor
                    : gridColorMinor
                }
                strokeWidth={line.voltage === 0.0 ? "1.2" : line.isMajor ? "0.8" : "0.4"}
                strokeDasharray={line.voltage === 0.0 ? "4 2" : undefined}
              />
              {/* Voltage Tick Label on Left Y-Axis */}
              {line.isMajor && (
                <text
                  x={PADDING_LEFT - 8}
                  y={line.y + 3.5}
                  textAnchor="end"
                  fill={line.voltage === 0.0 ? "#00F0FF" : "#94A3B8"}
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight={line.voltage === 0.0 ? "bold" : "normal"}
                >
                  {(line.voltage >= 0 ? "+" : "") + line.voltage.toFixed(1)} mV
                </text>
              )}
            </g>
          ))}

          {/* Vertical Time Grid Lines & Labels */}
          {gridLines.vertical.map((line, idx) => (
            <g key={`v-${idx}`}>
              <line
                x1={line.x}
                y1={PADDING_TOP}
                x2={line.x}
                y2={SVG_HEIGHT - PADDING_BOTTOM}
                stroke={line.isMajor ? gridColorMajor : gridColorMinor}
                strokeWidth={line.isMajor ? "0.8" : "0.4"}
              />
              {/* Time Tick Label on Bottom X-Axis */}
              {line.isMajor && (
                <text
                  x={line.x}
                  y={SVG_HEIGHT - PADDING_BOTTOM + 16}
                  textAnchor="middle"
                  fill="#94A3B8"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {(line.timeMs / 1000).toFixed(2)}s
                </text>
              )}
            </g>
          ))}

          {/* Zero baseline indicator mark on axis */}
          <line
            x1={PADDING_LEFT - 4}
            y1={voltageToY(0.0)}
            x2={PADDING_LEFT}
            y2={voltageToY(0.0)}
            stroke="#00F0FF"
            strokeWidth="2"
          />

          {/* R-Peak Detection Marker Line */}
          {rPeakSample >= clampedPan && rPeakSample <= endIndex && (
            <g>
              <line
                x1={sampleToX(rPeakSample)}
                y1={PADDING_TOP}
                x2={sampleToX(rPeakSample)}
                y2={SVG_HEIGHT - PADDING_BOTTOM}
                stroke="#00F0FF"
                strokeWidth="1.2"
                strokeDasharray="4 3"
              />
              {/* R-Peak Pill Badge */}
              <rect
                x={sampleToX(rPeakSample) - 28}
                y={PADDING_TOP + 4}
                width="56"
                height="15"
                rx="4"
                fill="#002b36"
                stroke="#00F0FF"
                strokeWidth="0.8"
              />
              <text
                x={sampleToX(rPeakSample)}
                y={PADDING_TOP + 15}
                textAnchor="middle"
                fill="#00F0FF"
                fontSize="8.5"
                fontFamily="monospace"
                fontWeight="bold"
              >
                R-PEAK #{rPeakSample}
              </text>
            </g>
          )}

          {/* Caliper Point 1 Marker */}
          {caliperP1 && caliperP1.index >= clampedPan && caliperP1.index <= endIndex && (
            <g>
              <line
                x1={sampleToX(caliperP1.index)}
                y1={PADDING_TOP}
                x2={sampleToX(caliperP1.index)}
                y2={SVG_HEIGHT - PADDING_BOTTOM}
                stroke="#8B5CF6"
                strokeWidth="1.5"
                strokeDasharray="2 2"
              />
              <circle
                cx={sampleToX(caliperP1.index)}
                cy={voltageToY(caliperP1.voltageMv)}
                r="4.5"
                fill="#8B5CF6"
                stroke="#FFFFFF"
                strokeWidth="1.5"
              />
              <text
                x={sampleToX(caliperP1.index)}
                y={PADDING_TOP - 6}
                textAnchor="middle"
                fill="#8B5CF6"
                fontSize="9"
                fontFamily="monospace"
                fontWeight="bold"
              >
                [P1]
              </text>
            </g>
          )}

          {/* Caliper Point 2 Marker */}
          {caliperP2 && caliperP2.index >= clampedPan && caliperP2.index <= endIndex && (
            <g>
              <line
                x1={sampleToX(caliperP2.index)}
                y1={PADDING_TOP}
                x2={sampleToX(caliperP2.index)}
                y2={SVG_HEIGHT - PADDING_BOTTOM}
                stroke="#A855F7"
                strokeWidth="1.5"
                strokeDasharray="2 2"
              />
              <circle
                cx={sampleToX(caliperP2.index)}
                cy={voltageToY(caliperP2.voltageMv)}
                r="4.5"
                fill="#A855F7"
                stroke="#FFFFFF"
                strokeWidth="1.5"
              />
              <text
                x={sampleToX(caliperP2.index)}
                y={PADDING_TOP - 6}
                textAnchor="middle"
                fill="#A855F7"
                fontSize="9"
                fontFamily="monospace"
                fontWeight="bold"
              >
                [P2]
              </text>
            </g>
          )}

          {/* Actual 360-sample Waveform Path */}
          {waveformPath && (
            <path
              d={waveformPath}
              fill="none"
              stroke={isVEB ? "url(#vebGlow)" : "url(#normalGlow)"}
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ filter: glowFilter }}
            />
          )}

          {/* Active Hover Crosshair and Dot */}
          {hoveredSample && (
            <g>
              {/* Vertical Crosshair Line */}
              <line
                x1={hoveredSample.svgX}
                y1={PADDING_TOP}
                x2={hoveredSample.svgX}
                y2={SVG_HEIGHT - PADDING_BOTTOM}
                stroke="rgba(255, 255, 255, 0.45)"
                strokeWidth="0.8"
                strokeDasharray="3 3"
              />
              {/* Horizontal Crosshair Line */}
              <line
                x1={PADDING_LEFT}
                y1={hoveredSample.svgY}
                x2={SVG_WIDTH - PADDING_RIGHT}
                y2={hoveredSample.svgY}
                stroke="rgba(255, 255, 255, 0.45)"
                strokeWidth="0.8"
                strokeDasharray="3 3"
              />
              {/* Highlighting Circle on Waveform */}
              <circle
                cx={hoveredSample.svgX}
                cy={hoveredSample.svgY}
                r="4.5"
                fill="#FFFFFF"
                stroke={traceColor}
                strokeWidth="2"
              />
            </g>
          )}

          {/* Plot Bounding Box Border */}
          <rect
            x={PADDING_LEFT}
            y={PADDING_TOP}
            width={PLOT_WIDTH}
            height={PLOT_HEIGHT}
            fill="none"
            stroke="rgba(255, 255, 255, 0.15)"
            strokeWidth="1"
          />

          {/* Bottom Sample Counter Ticks */}
          <text
            x={PADDING_LEFT}
            y={SVG_HEIGHT - 10}
            textAnchor="start"
            fill="#64748B"
            fontSize="8.5"
            fontFamily="monospace"
          >
            Start: #{clampedPan} ({((clampedPan / samplingRate) * 1000).toFixed(0)}ms)
          </text>
          <text
            x={SVG_WIDTH - PADDING_RIGHT}
            y={SVG_HEIGHT - 10}
            textAnchor="end"
            fill="#64748B"
            fontSize="8.5"
            fontFamily="monospace"
          >
            End: #{endIndex} ({((endIndex / samplingRate) * 1000).toFixed(0)}ms)
          </text>
          <text
            x={SVG_WIDTH / 2}
            y={SVG_HEIGHT - 10}
            textAnchor="middle"
            fill="#64748B"
            fontSize="8.5"
            fontFamily="monospace"
          >
            Window: 360 Samples @ 360 Hz (359 sample intervals = 997.2 ms duration)
          </text>
        </svg>

        {/* Pan Scroller when Zoomed In */}
        {zoomLevel > 1.0 && (
          <div className="flex items-center gap-3 px-4 py-2 border-t border-white/10 bg-black/60 font-mono text-xs">
            <button
              onClick={() => setPanIndex(Math.max(0, panIndex - 20))}
              disabled={panIndex <= 0}
              className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-300 disabled:opacity-30 cursor-pointer"
              title="Pan Left"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] text-slate-400">Pan Window:</span>
            <input
              type="range"
              min="0"
              max={maxPan}
              value={clampedPan}
              onChange={(e) => setPanIndex(Number(e.target.value))}
              className="w-full accent-nexus-cyan h-1.5 bg-slate-800 rounded-lg cursor-pointer"
            />
            <button
              onClick={() => setPanIndex(Math.min(maxPan, panIndex + 20))}
              disabled={panIndex >= maxPan}
              className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-300 disabled:opacity-30 cursor-pointer"
              title="Pan Right"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] text-slate-400 min-w-[70px] text-right">
              {clampedPan}..{endIndex}
            </span>
          </div>
        )}
      </div>

      {/* Under-Waveform Physiological Reference Bar */}
      <div className="p-2.5 rounded-xl bg-nexus-card border border-white/10 flex flex-wrap items-center justify-between text-xs font-mono text-slate-400 gap-3">
        <div className="flex items-center gap-2">
          <span className="text-white font-bold">SEGMENT:</span>
          <span className="text-nexus-cyan font-semibold">{segmentId}</span>
          <span className="text-slate-600">·</span>
          <span>ANNOTATION:</span>
          <span
            className={`font-bold px-1.5 py-0.5 rounded text-[10px] ${
              isVEB ? "bg-pink-500/20 text-pink-400 border border-pink-500/40" : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
            }`}
          >
            '{annotationSymbol}' ({isVEB ? "Ventricular Ectopic" : "Normal Sinus"})
          </span>
        </div>

        {notes && (
          <div className="text-[11px] text-amber-300 flex items-center gap-1.5">
            <span>⚠️</span>
            <span>{notes}</span>
          </div>
        )}

        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400" /> Normal Baseline (0.0 mV)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> R-Peak #144 (±25 RMS QRS)
          </span>
        </div>
      </div>
    </div>
  );
};
