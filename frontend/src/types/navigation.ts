export type AppRoute =
  | 'command-center'
  | 'ecg-intelligence'
  | 'quantum-ai-lab'
  | 'hardware-intelligence'
  | 'performance-observatory'
  | 'dataset-audit';

export interface RouteMeta {
  id: AppRoute;
  name: string;
  shortName: string;
  badge?: string;
  icon: string;
  category: 'core' | 'biomedical' | 'quantum' | 'audit';
  description: string;
}

export const APP_ROUTES: RouteMeta[] = [
  {
    id: 'command-center',
    name: 'Command Center',
    shortName: 'Overview',
    badge: 'LIVE',
    icon: 'LayoutDashboard',
    category: 'core',
    description: 'Quantum biomedical workflow routing map, system health, and real-time execution telemetry.',
  },
  {
    id: 'ecg-intelligence',
    name: 'ECG Intelligence',
    shortName: 'ECG AI',
    badge: '360Hz',
    icon: 'Activity',
    category: 'biomedical',
    description: 'Interactive Lead II (MLII) rhythm strip, 6-feature biomarker decomposition, and noise injection controls.',
  },
  {
    id: 'quantum-ai-lab',
    name: 'Quantum AI Lab',
    shortName: 'VQC Lab',
    badge: '6-Qubit',
    icon: 'Atom',
    category: 'quantum',
    description: 'Dilution cryostat HUD, 6-qubit RealAmplitudes VQC circuit, and Pauli-Z ensemble observable.',
  },
  {
    id: 'hardware-intelligence',
    name: 'Hardware Intelligence',
    shortName: 'QPU Target',
    badge: '9Q Sparse',
    icon: 'Cpu',
    category: 'quantum',
    description: 'Processor B heavy-hex tree vs Processor A linear chain capacity enforcement and native transpilation.',
  },
  {
    id: 'performance-observatory',
    name: 'Performance Observatory',
    shortName: 'Analytics',
    badge: 'AUC 0.998',
    icon: 'BarChart3',
    category: 'audit',
    description: 'Held-out test cohort ROC curves, confusion matrices, ECE calibration, and classical ML benchmarks.',
  },
  {
    id: 'dataset-audit',
    name: 'Dataset & Audit',
    shortName: 'Audit Hub',
    badge: 'RECORD SPLIT',
    icon: 'FileCheck2',
    category: 'audit',
    description: 'MIT-BIH cohort provenance, zero-leakage quarantine protocol, scaler clipping analysis, and disclosures.',
  },
];
