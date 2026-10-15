import React, { useState, useEffect } from "react";
import { Search, ArrowRight, ShieldAlert, Cpu, Activity, BarChart2, FileText, Atom, X } from "lucide-react";
import type { AppRoute } from "../../types/navigation";
import { APP_ROUTES } from "../../types/navigation";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (route: AppRoute) => void;
  onOpenDisclosures: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigate,
  onOpenDisclosures,
}) => {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const getRouteIcon = (id: AppRoute) => {
    switch (id) {
      case "command-center":
        return <Activity className="w-4 h-4 text-nexus-cyan" />;
      case "ecg-intelligence":
        return <Activity className="w-4 h-4 text-emerald-400" />;
      case "quantum-ai-lab":
        return <Atom className="w-4 h-4 text-nexus-violet" />;
      case "hardware-intelligence":
        return <Cpu className="w-4 h-4 text-nexus-blue" />;
      case "performance-observatory":
        return <BarChart2 className="w-4 h-4 text-amber-400" />;
      case "dataset-audit":
        return <FileText className="w-4 h-4 text-purple-400" />;
    }
  };

  const filteredRoutes = APP_ROUTES.filter(
    (r) =>
      r.name.toLowerCase().includes(query.toLowerCase()) ||
      r.description.toLowerCase().includes(query.toLowerCase())
  );

  const quickActions = [
    {
      id: "disclosures",
      title: "Scientific Disclosures & Guardrails",
      subtitle: "Review clinical disclaimer, simulation bounds & LORO protocol",
      icon: <ShieldAlert className="w-4 h-4 text-amber-400" />,
      action: () => {
        onOpenDisclosures();
        onClose();
      },
    },
  ];

  const totalItems = filteredRoutes.length + quickActions.length;

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % totalItems);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + totalItems) % totalItems);
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (selectedIndex < filteredRoutes.length) {
          onNavigate(filteredRoutes[selectedIndex].id);
          onClose();
        } else {
          quickActions[selectedIndex - filteredRoutes.length].action();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, filteredRoutes, totalItems]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 overflow-y-auto">
      <div
        className="fixed inset-0 bg-black/80 backdrop-blur-md animate-in fade-in duration-150"
        onClick={onClose}
      />

      <div className="relative w-full max-w-2xl bg-nexus-navy/95 border border-nexus-cyan/40 rounded-2xl shadow-2xl backdrop-blur-2xl overflow-hidden z-10 animate-in zoom-in-95 duration-150 text-slate-100">
        {/* Top cyan glow hairline */}
        <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-nexus-cyan to-transparent" />

        {/* Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/[0.08]">
          <Search className="w-5 h-5 text-nexus-cyan shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command, search modules, or inspect hardware..."
            className="w-full bg-transparent text-sm text-white placeholder-slate-400 focus:outline-none font-sans"
            autoFocus
          />
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          <div className="px-3 py-1.5 text-[10px] font-mono text-slate-400 tracking-wider uppercase">
            Navigation Modules ({filteredRoutes.length})
          </div>

          {filteredRoutes.map((route, idx) => (
            <div
              key={route.id}
              onClick={() => {
                onNavigate(route.id);
                onClose();
              }}
              onMouseEnter={() => setSelectedIndex(idx)}
              className={`flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                selectedIndex === idx
                  ? "bg-nexus-cyan/15 text-white border border-nexus-cyan/30"
                  : "text-slate-300 hover:bg-white/[0.04]"
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="p-1.5 rounded-md bg-white/[0.06] border border-white/10">
                  {getRouteIcon(route.id)}
                </div>
                <div>
                  <div className="text-sm font-semibold flex items-center gap-2">
                    <span>{route.name}</span>
                    {route.badge && (
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-nexus-cyan/10 text-nexus-cyan border border-nexus-cyan/20">
                        {route.badge}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-400 line-clamp-1">
                    {route.description}
                  </div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </div>
          ))}

          <div className="px-3 pt-3 pb-1.5 text-[10px] font-mono text-slate-400 tracking-wider uppercase">
            Scientific Actions
          </div>

          {quickActions.map((action, actionIdx) => {
            const itemIdx = filteredRoutes.length + actionIdx;
            return (
              <div
                key={action.id}
                onClick={action.action}
                onMouseEnter={() => setSelectedIndex(itemIdx)}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                  selectedIndex === itemIdx
                    ? "bg-amber-500/15 text-white border border-amber-500/30"
                    : "text-slate-300 hover:bg-white/[0.04]"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-md bg-amber-500/10 border border-amber-500/20">
                    {action.icon}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-amber-300">
                      {action.title}
                    </div>
                    <div className="text-xs text-slate-400">{action.subtitle}</div>
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-amber-500/50" />
              </div>
            );
          })}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2 bg-black/40 border-t border-white/[0.06] flex items-center justify-between text-[11px] font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <div className="text-nexus-cyan">Qiskit Fall Fest 2026</div>
        </div>
      </div>
    </div>
  );
};
