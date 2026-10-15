export interface FrozenModelInfo {
  runId: string;
  sourceFold: number;
  seed: number;
  trainRecord: number;
  valRecord: number;
  selectionRule: string;
  parameterCount: number;
  optimalTheta: number[];
}

export const FROZEN_MODEL: FrozenModelInfo = {
  runId: "fold_1_seed_303",
  sourceFold: 1,
  seed: 303,
  trainRecord: 106,
  valRecord: 119,
  selectionRule: "balanced_validation",
  parameterCount: 12,
  optimalTheta: [
    0.48888847284211656,
    -1.2636229184088255,
    -0.49618531730782184,
    -0.9822884876903525,
    -0.8177933416414555,
    -0.7963986558464293,
    -0.3341059768227328,
    -0.3669351575495604,
    -0.8660987972603893,
    -1.034837255605418,
    0.5613811143193971,
    0.4214387999586761,
  ],
};

export interface ScientificDisclosures {
  nonDiagnosticDisclaimer: string;
  simulationNotice: string;
  loroPartitionNote: string;
  scalerClampingNote: string;
  record208ShiftNote: string;
}

export const SCIENTIFIC_DISCLOSURES: ScientificDisclosures = {
  nonDiagnosticDisclaimer:
    "RESEARCH BENCHMARK ONLY: NEXUS-OPS is an engineering research implementation for IBM Quantum Qiskit Fall Fest 2026. It is not an FDA-cleared medical device and must not be used for primary clinical diagnostics or patient triage.",
  simulationNotice:
    "SIMULATION NOTICE: All quantum circuits and noise models are executed on classical simulators (Qiskit 2.5.2 StatevectorEstimator and Aer 0.17.2 AerSimulator). No physical cryogenic quantum hardware was used.",
  loroPartitionNote:
    "RECORD-LEVEL PARTITIONING (LORO): Evaluation enforces strict Leave-One-Record-Out isolation across MIT-BIH recordings (Records 106 & 119 development cohort, 200 beats; Records 200 & 208 strictly quarantined held-out test cohort, 100 beats; 300 beats total). This guarantees zero beat leakage across training and evaluation splits, but does NOT constitute verified patient-level separation. Records 100 & 101 are not part of this experimental protocol.",
  scalerClampingNote:
    "SCALER CLAMPING RECONCILIATION: Fitted strictly on Development Cohort (106 & 119). Clamped to [0, π] on Held-Out Test (200 & 208), yielding exactly 14/600 clipped values (2.33%) across 13/100 affected beats (13.00%). In LORO validation, Record 119 had 120/600 clipped values (20.00%, 54/100 beats) and Record 106 had 154/600 clipped values (25.67%, 89/100 beats). All training sets had 0/1200 clipped values (0.00%).",
  record208ShiftNote:
    "RECORDING DISTRIBUTION SHIFT: Test Record 208 exhibits lower specificity (36.0%) than Record 200 (68.0%), reflecting record-specific ECG morphology shifts across distinct tape sessions.",
};
