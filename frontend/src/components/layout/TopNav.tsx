import React, { useState, useEffect, useCallback } from "react";
import { Search, ShieldAlert, Cpu, Bell, Activity, Sparkles, Menu, RefreshCw } from "lucide-react";
import { FROZEN_MODEL } from "../../types/scientific";
import { api, type BackendHealth } from "../../services/api";

interface TopNavProps {
  onOpenCommand: () => void;
  onOpenDisclosures: () => void;
  onToggleSidebar: () => void;
  isSidebarOpen: boolean;
}

export const TopNav: React.FC<TopNavProps> = ({
  onOpenCommand,
  onOpenDisclosures,
  onToggleSidebar,
}) => {
  const [timeStr, setTimeStr] = useState("");
  const [backendHealth, setBackendHealth] = useState<BackendHealth | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  const checkBackend = useCallback(async () => {
    setIsChecking(true);
    const result = await api.checkHealth();
    setIsBackendOnline(result.isOnline);
    setBackendHealth(result.data);
    setIsChecking(false);
  }, []);

  useEffect(() => {
    checkBackend();
    const unsubscribe = api.subscribeStatus((online) => {
      setIsBackendOnline(online);
    });
    const interval = setInterval(checkBackend, 15000);
    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, [checkBackend]);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }) + " UTC"
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="sticky top-0 z-30 h-16 bg-nexus-black/80 backdrop-blur-xl border-b border-nexus-border/40 px-4 lg:px-6 flex items-center justify-between gap-4">
      {/* Left: Mobile hamburger & Project Branding */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] lg:hidden focus:outline-none"
          aria-label="Toggle Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5">
          {/* Glowing Crystal / Quantum Node Icon */}
          <div className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-nexus-cyan/20 to-nexus-violet/30 border border-nexus-cyan/50 flex items-center justify-center shadow-glow-cyan-sm">
            <Sparkles className="w-4 h-4 text-nexus-cyan animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm tracking-widest text-white uppercase">
                NEXUS<span className="text-nexus-cyan">-OPS</span>
              </span>
              <span className="hidden sm:inline-block text-[10px] font-mono px-1.5 py-0.2 rounded bg-nexus-violet/20 text-violet-300 border border-nexus-violet/30">
                PROJECT Q
              </span>
            </div>
            <p className="hidden md:block text-[10px] text-slate-400 font-mono tracking-tight">
              PS-Q1 Biomedical Classifier · IBM Quantum Qiskit Fall Fest 2026
            </p>
          </div>
        </div>
      </div>

      {/* Middle: Command Palette Search Bar */}
      <div className="flex-1 max-w-md mx-2 sm:mx-6">
        <button
          onClick={onOpenCommand}
          className="w-full flex items-center justify-between px-3.5 py-1.5 rounded-xl bg-nexus-navy/60 border border-white/10 hover:border-nexus-cyan/40 text-slate-400 hover:text-slate-200 transition-all text-xs group"
        >
          <span className="flex items-center gap-2">
            <Search className="w-4 h-4 text-nexus-cyan/80 group-hover:text-nexus-cyan" />
            <span className="truncate">Search modules, features, hardware...</span>
          </span>
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono bg-white/[0.06] border border-white/10 rounded text-slate-300">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right: Telemetry Status Badges & User Profile */}
      <div className="flex items-center gap-3">
        {/* Backend API Connectivity Pill */}
        {isBackendOnline ? (
          <div
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-[11px] font-mono text-emerald-300"
            title={`FastAPI backend live at 127.0.0.1:8000 · Qiskit ${backendHealth?.qiskit_version || "2.5.2"}`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#10B981]" />
            <span>API: LIVE</span>
          </div>
        ) : (
          <button
            onClick={checkBackend}
            disabled={isChecking}
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[11px] font-mono text-amber-300 hover:bg-amber-500/20 transition-colors"
            title="FastAPI backend offline. Running on verified scientific audit cache. Click to retry connection."
          >
            {isChecking ? (
              <RefreshCw className="w-3 h-3 text-amber-400 animate-spin" />
            ) : (
              <span className="w-2 h-2 rounded-full bg-amber-400" />
            )}
            <span>API: CACHED</span>
          </button>
        )}

        {/* Simulation Guardrail Badge */}
        <div className="hidden xl:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/10 text-[11px] font-mono text-slate-300">
          <Cpu className="w-3.5 h-3.5 text-nexus-blue" />
          <span>Simulated QPU</span>
          <span className="text-slate-500">·</span>
          <span className="text-nexus-cyan">Aer 0.17.2</span>
        </div>

        {/* Frozen Checkpoint Pill */}
        <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/10 text-[11px] font-mono text-slate-300">
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <span>Model:</span>
          <span className="text-emerald-300 font-semibold">{FROZEN_MODEL.runId}</span>
        </div>

        {/* Live Clock */}
        <div className="hidden sm:block text-[11px] font-mono text-slate-400 px-2">
          {timeStr}
        </div>

        {/* Disclosures Trigger */}
        <button
          onClick={onOpenDisclosures}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 transition-colors text-xs font-mono"
          title="Review scientific disclosures and guardrails"
        >
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <span className="hidden md:inline">Guardrails</span>
        </button>

        {/* Notifications Icon */}
        <button
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] transition-colors relative"
          aria-label="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-nexus-cyan rounded-full shadow-[0_0_6px_#00F0FF]" />
        </button>

        {/* User / Team Avatar Pill */}
        <div className="flex items-center gap-2 pl-2 border-l border-white/10">
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-nexus-cyan to-nexus-violet flex items-center justify-center font-bold text-xs text-nexus-black">
            H4
          </div>
          <div className="hidden 2xl:block text-left text-xs">
            <div className="font-semibold text-white leading-none">Hashir4m4</div>
            <div className="text-[10px] text-slate-400 leading-none mt-1">Lead Researcher</div>
          </div>
        </div>
      </div>
    </header>
  );
};
