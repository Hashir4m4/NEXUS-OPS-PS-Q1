import React, { useState } from "react";
import { TopNav } from "./TopNav";
import { Sidebar } from "./Sidebar";
import { CommandPalette } from "./CommandPalette";
import { DisclosuresModal } from "./DisclosuresModal";
import type { AppRoute } from "../../types/navigation";
import { APP_ROUTES } from "../../types/navigation";
import { cn } from "../../lib/utils";

interface AppShellProps {
  currentRoute: AppRoute;
  onSelectRoute: (route: AppRoute) => void;
  isDisclosuresOpen?: boolean;
  onSetDisclosuresOpen?: (open: boolean) => void;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  currentRoute,
  onSelectRoute,
  isDisclosuresOpen: controlledDisclosures,
  onSetDisclosuresOpen,
  children,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [internalDisclosures, setInternalDisclosures] = useState(false);

  const isDisclosuresOpen = controlledDisclosures !== undefined ? controlledDisclosures : internalDisclosures;
  const setDisclosuresOpen = onSetDisclosuresOpen || setInternalDisclosures;

  // Keyboard shortcut listener for ⌘K / Ctrl+K
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsCommandOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const activeMeta = APP_ROUTES.find((r) => r.id === currentRoute) || APP_ROUTES[0];

  return (
    <div className="min-h-screen bg-nexus-void text-slate-100 flex flex-col cyber-grid">
      {/* Top Navigation */}
      <TopNav
        onOpenCommand={() => setIsCommandOpen(true)}
        onOpenDisclosures={() => setDisclosuresOpen(true)}
        onToggleSidebar={() => setIsMobileOpen((prev) => !prev)}
        isSidebarOpen={isMobileOpen}
      />

      <div className="flex flex-1 relative">
        {/* Sidebar */}
        <Sidebar
          currentRoute={currentRoute}
          onSelectRoute={onSelectRoute}
          isCollapsed={isCollapsed}
          onToggleCollapse={() => setIsCollapsed((prev) => !prev)}
          isOpenMobile={isMobileOpen}
          onCloseMobile={() => setIsMobileOpen(false)}
          onOpenDisclosures={() => setDisclosuresOpen(true)}
        />

        {/* Main Content Area */}
        <main
          className={cn(
            "flex-1 flex flex-col min-w-0 transition-all duration-300",
            isCollapsed ? "lg:pl-20" : "lg:pl-64"
          )}
        >
          {/* Breadcrumb & Route Banner */}
          <div className="px-6 py-4 border-b border-white/[0.06] bg-nexus-black/40 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                <span className="text-nexus-cyan">NEXUS-OPS</span>
                <span>/</span>
                <span className="capitalize">{activeMeta.category}</span>
                <span>/</span>
                <span className="text-white font-semibold">{activeMeta.name}</span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight mt-1 flex items-center gap-3">
                <span>{activeMeta.name}</span>
                {activeMeta.badge && (
                  <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-nexus-cyan/15 text-nexus-cyan border border-nexus-cyan/30">
                    {activeMeta.badge}
                  </span>
                )}
              </h1>
              <p className="text-xs text-slate-400 mt-1 max-w-2xl">
                {activeMeta.description}
              </p>
            </div>

            {/* Quick action pill */}
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.04] border border-white/10 text-xs font-mono text-slate-300">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Pipeline Active
              </span>
            </div>
          </div>

          {/* Page Body */}
          <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
            {children}
          </div>
        </main>
      </div>

      {/* Global Modals */}
      <CommandPalette
        isOpen={isCommandOpen}
        onClose={() => setIsCommandOpen(false)}
        onNavigate={onSelectRoute}
        onOpenDisclosures={() => setDisclosuresOpen(true)}
      />

      <DisclosuresModal
        isOpen={isDisclosuresOpen}
        onClose={() => setDisclosuresOpen(false)}
      />
    </div>
  );
};
