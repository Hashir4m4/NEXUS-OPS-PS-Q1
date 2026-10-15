import React from "react";
import {
  LayoutDashboard,
  Activity,
  Atom,
  Cpu,
  BarChart3,
  FileCheck2,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Zap,
} from "lucide-react";
import type { AppRoute } from "../../types/navigation";
import { APP_ROUTES } from "../../types/navigation";
import { cn } from "../../lib/utils";

interface SidebarProps {
  currentRoute: AppRoute;
  onSelectRoute: (route: AppRoute) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  onOpenDisclosures: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentRoute,
  onSelectRoute,
  isCollapsed,
  onToggleCollapse,
  isOpenMobile,
  onCloseMobile,
  onOpenDisclosures,
}) => {
  const getRouteIcon = (id: AppRoute) => {
    switch (id) {
      case "command-center":
        return <LayoutDashboard className="w-4 h-4 shrink-0" />;
      case "ecg-intelligence":
        return <Activity className="w-4 h-4 shrink-0" />;
      case "quantum-ai-lab":
        return <Atom className="w-4 h-4 shrink-0" />;
      case "hardware-intelligence":
        return <Cpu className="w-4 h-4 shrink-0" />;
      case "performance-observatory":
        return <BarChart3 className="w-4 h-4 shrink-0" />;
      case "dataset-audit":
        return <FileCheck2 className="w-4 h-4 shrink-0" />;
    }
  };

  const coreRoutes = APP_ROUTES.filter((r) => r.category === "core");
  const scientificRoutes = APP_ROUTES.filter(
    (r) => r.category === "biomedical" || r.category === "quantum"
  );
  const auditRoutes = APP_ROUTES.filter((r) => r.category === "audit");

  const renderRouteGroup = (title: string, routes: typeof APP_ROUTES) => (
    <div className="mb-4">
      {!isCollapsed && (
        <div className="px-3 mb-1.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </div>
      )}
      <div className="space-y-1">
        {routes.map((route) => {
          const isActive = currentRoute === route.id;
          return (
            <button
              key={route.id}
              onClick={() => {
                onSelectRoute(route.id);
                onCloseMobile();
              }}
              title={isCollapsed ? route.name : undefined}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all group relative cursor-pointer",
                isActive
                  ? "bg-gradient-to-r from-nexus-cyan/15 to-transparent text-white border-l-2 border-nexus-cyan shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
              )}
            >
              <div
                className={cn(
                  "p-1.5 rounded-lg transition-colors",
                  isActive
                    ? "bg-nexus-cyan/20 text-nexus-cyan shadow-glow-cyan-sm"
                    : "text-slate-400 group-hover:text-nexus-cyan group-hover:bg-nexus-cyan/10"
                )}
              >
                {getRouteIcon(route.id)}
              </div>

              {!isCollapsed && (
                <div className="flex-1 flex items-center justify-between min-w-0 text-left">
                  <span className="truncate">{route.name}</span>
                  {route.badge && (
                    <span
                      className={cn(
                        "text-[9px] font-mono px-1.5 py-0.5 rounded uppercase tracking-wider",
                        isActive
                          ? "bg-nexus-cyan/20 text-nexus-cyan border border-nexus-cyan/30"
                          : "bg-white/[0.06] text-slate-400 border border-white/10"
                      )}
                    >
                      {route.badge}
                    </span>
                  )}
                </div>
              )}

              {/* Glowing active notch indicator */}
              {isActive && (
                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-4 bg-nexus-cyan rounded-l shadow-[0_0_8px_#00F0FF]" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={cn(
          "fixed top-16 bottom-0 left-0 z-40 bg-nexus-black/90 backdrop-blur-2xl border-r border-nexus-border/30 transition-all duration-300 flex flex-col justify-between p-3 overflow-y-auto overflow-x-hidden",
          isCollapsed ? "w-18" : "w-64",
          isOpenMobile ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div>
          {/* Top Collapse Toggle Button (Desktop only) */}
          <div className="hidden lg:flex items-center justify-end mb-3 pb-2 border-b border-white/[0.06]">
            <button
              onClick={onToggleCollapse}
              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-white/[0.06] transition-colors"
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {isCollapsed ? (
                <ChevronRight className="w-4 h-4 text-nexus-cyan" />
              ) : (
                <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400 hover:text-slate-200">
                  <span>Collapse</span>
                  <ChevronLeft className="w-3.5 h-3.5" />
                </div>
              )}
            </button>
          </div>

          {/* Route Groups */}
          {renderRouteGroup("Platform Operations", coreRoutes)}
          {renderRouteGroup("Intelligence Engines", scientificRoutes)}
          {renderRouteGroup("Verification & Ethics", auditRoutes)}
        </div>

        {/* Bottom Platform Status Card */}
        <div className="pt-3 border-t border-white/[0.06]">
          {!isCollapsed ? (
            <div className="p-3 rounded-xl bg-nexus-card/60 border border-nexus-cyan/20 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-emerald-400 font-mono font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#10B981] animate-pulse" />
                  Systems Verified
                </span>
                <span className="text-[10px] font-mono text-slate-400">116/116</span>
              </div>
              <p className="text-[10px] text-slate-400 leading-tight">
                VQC fold_1_seed_303 frozen. Quarantined test cohort ready.
              </p>
              <button
                onClick={onOpenDisclosures}
                className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-white/[0.05] hover:bg-nexus-cyan/10 border border-white/10 hover:border-nexus-cyan/30 text-[11px] font-mono text-slate-300 hover:text-nexus-cyan transition-colors"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Audit Disclosures</span>
              </button>
            </div>
          ) : (
            <div className="flex justify-center">
              <button
                onClick={onOpenDisclosures}
                className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
                title="Systems Verified: 116/116 Tests Passed. Click to view disclosures."
              >
                <Zap className="w-4 h-4 animate-pulse" />
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
