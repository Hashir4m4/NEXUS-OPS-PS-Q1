import { useState } from "react";
import { AppShell } from "./components/layout/AppShell";
import type { AppRoute } from "./types/navigation";
import { CommandCenter } from "./pages/CommandCenter";
import { EcgIntelligence } from "./pages/EcgIntelligence";
import { QuantumAiLab } from "./pages/QuantumAiLab";
import { HardwareIntelligence } from "./pages/HardwareIntelligence";
import { PerformanceObservatory } from "./pages/PerformanceObservatory";
import { DatasetAudit } from "./pages/DatasetAudit";

export function App() {
  const [currentRoute, setCurrentRoute] = useState<AppRoute>("command-center");
  const [isDisclosuresOpen, setIsDisclosuresOpen] = useState(false);

  const renderActivePage = () => {
    switch (currentRoute) {
      case "command-center":
        return (
          <CommandCenter
            onNavigate={setCurrentRoute}
            onOpenDisclosures={() => setIsDisclosuresOpen(true)}
          />
        );
      case "ecg-intelligence":
        return (
          <EcgIntelligence
            onOpenDisclosures={() => setIsDisclosuresOpen(true)}
          />
        );
      case "quantum-ai-lab":
        return (
          <QuantumAiLab
            onOpenDisclosures={() => setIsDisclosuresOpen(true)}
          />
        );
      case "hardware-intelligence":
        return <HardwareIntelligence />;
      case "performance-observatory":
        return <PerformanceObservatory />;
      case "dataset-audit":
        return (
          <DatasetAudit
            onOpenDisclosures={() => setIsDisclosuresOpen(true)}
          />
        );
      default:
        return (
          <CommandCenter
            onNavigate={setCurrentRoute}
            onOpenDisclosures={() => setIsDisclosuresOpen(true)}
          />
        );
    }
  };

  return (
    <AppShell
      currentRoute={currentRoute}
      onSelectRoute={setCurrentRoute}
      isDisclosuresOpen={isDisclosuresOpen}
      onSetDisclosuresOpen={setIsDisclosuresOpen}
    >
      {renderActivePage()}
    </AppShell>
  );
}

export default App;
