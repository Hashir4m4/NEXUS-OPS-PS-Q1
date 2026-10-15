import React from "react";
import { Modal } from "../ui/Modal";
import { SCIENTIFIC_DISCLOSURES, FROZEN_MODEL } from "../../types/scientific";
import { AlertTriangle, ShieldCheck, Cpu, Database, Award } from "lucide-react";
import { StatusBadge } from "../ui/StatusBadge";

interface DisclosuresModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DisclosuresModal: React.FC<DisclosuresModalProps> = ({
  isOpen,
  onClose,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-nexus-cyan" />
          <span>Scientific Guardrails & Evaluation Disclosures</span>
        </div>
      }
      subtitle="IBM Quantum Qiskit Fall Fest 2026 — PS-Q1 Biomedical Signal Classifier"
      maxWidth="2xl"
    >
      <div className="space-y-4 text-xs leading-relaxed text-slate-300">
        {/* Banner 1: Non-Diagnostic Disclaimer */}
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3 text-amber-200">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-amber-300 text-sm mb-1 uppercase tracking-wider">
              Clinical Disclaimer
            </div>
            <p>{SCIENTIFIC_DISCLOSURES.nonDiagnosticDisclaimer}</p>
          </div>
        </div>

        {/* Section 2: Hardware vs Simulation */}
        <div className="p-3.5 rounded-xl bg-nexus-card border border-white/10 flex items-start gap-3">
          <Cpu className="w-5 h-5 text-nexus-cyan shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-white text-sm mb-1 flex items-center gap-2">
              <span>Simulation vs. Physical Hardware Execution</span>
              <StatusBadge variant="cyan" size="sm">Aer 0.17.2</StatusBadge>
            </div>
            <p>{SCIENTIFIC_DISCLOSURES.simulationNotice}</p>
          </div>
        </div>

        {/* Section 3: LORO Protocol */}
        <div className="p-3.5 rounded-xl bg-nexus-card border border-white/10 flex items-start gap-3">
          <Database className="w-5 h-5 text-nexus-blue shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-white text-sm mb-1 flex items-center gap-2">
              <span>Leakage-Controlled LORO Partitioning</span>
              <StatusBadge variant="blue" size="sm">Records 200/208 Quarantined</StatusBadge>
            </div>
            <p>{SCIENTIFIC_DISCLOSURES.loroPartitionNote}</p>
          </div>
        </div>

        {/* Section 4: Scaler Clipping & Shift */}
        <div className="p-3.5 rounded-xl bg-nexus-card border border-white/10 flex items-start gap-3">
          <Award className="w-5 h-5 text-nexus-violet shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-white text-sm mb-1 flex items-center gap-2">
              <span>Feature Scaler Quarantine & Clipping Rate</span>
              <StatusBadge variant="amber" size="sm">2.33% Value Clipping</StatusBadge>
            </div>
            <p className="mb-2">{SCIENTIFIC_DISCLOSURES.scalerClampingNote}</p>
            <p className="text-slate-400">{SCIENTIFIC_DISCLOSURES.record208ShiftNote}</p>
          </div>
        </div>

        {/* Section 5: Frozen Checkpoint Specifications */}
        <div className="p-3 rounded-lg bg-black/40 border border-nexus-cyan/20 font-mono text-[11px] text-slate-300">
          <div className="text-nexus-cyan font-semibold mb-1">
            FROZEN MODEL RUN ID: {FROZEN_MODEL.runId}
          </div>
          <div className="grid grid-cols-2 gap-2 text-slate-400">
            <div>Training Source: Record {FROZEN_MODEL.trainRecord} (N=100)</div>
            <div>Validation Source: Record {FROZEN_MODEL.valRecord} (N=100)</div>
            <div>Variational Parameters: {FROZEN_MODEL.parameterCount} (RealAmplitudes reps=1)</div>
            <div>Selection Rule: {FROZEN_MODEL.selectionRule}</div>
          </div>
        </div>
      </div>
    </Modal>
  );
};
