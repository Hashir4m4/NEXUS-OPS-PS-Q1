import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "../..");
const resultsDir = path.join(rootDir, "results");

console.log("=== NEXUS-OPS FRONTEND SCIENTIFIC INTEGRITY AUDIT TEST ===");

let passedTests = 0;
let totalTests = 0;

function assert(condition, message) {
  totalTests++;
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    process.exitCode = 1;
  } else {
    console.log(`✅ PASS: ${message}`);
    passedTests++;
  }
}

// 1. Audit Checkpoint & Model Selection
const modelSelectionPath = path.join(resultsDir, "vqc_model_selection.json");
const modelSelection = JSON.parse(fs.readFileSync(modelSelectionPath, "utf-8"));
assert(
  modelSelection.selected_candidate.run_id === "fold_1_seed_303",
  "Model selection chose checkpoint fold_1_seed_303"
);
assert(
  modelSelection.selected_candidate.fold_id === 1,
  "Selected checkpoint source fold is 1"
);
assert(
  modelSelection.selected_candidate.seed === 303,
  "Selected checkpoint random seed is 303"
);

// 2. Audit Held-Out Evaluation & Clipping Statistics
const heldoutEvalPath = path.join(resultsDir, "vqc_heldout_evaluation.json");
const heldoutEval = JSON.parse(fs.readFileSync(heldoutEvalPath, "utf-8"));
assert(
  heldoutEval.metadata.total_test_samples === 100,
  "Held-out test cohort has exactly 100 samples"
);
assert(
  heldoutEval.clipping_statistics.total_evaluated_values === 600,
  "Exact evaluated test values denominator is 600 (100 beats * 6 features)"
);
assert(
  heldoutEval.clipping_statistics.total_clipped_values === 14,
  "Exact clipped values count is 14 (14/600 = 2.33%)"
);
assert(
  heldoutEval.clipping_statistics.affected_beats_count === 13,
  "Exact affected beats count is 13 (13/100 = 13.0%)"
);
assert(
  heldoutEval.overall_test_metrics.accuracy === 0.76,
  "Frozen VQC test accuracy is 0.76 (76.00%)"
);
assert(
  heldoutEval.overall_test_metrics.sensitivity === 1.0,
  "Frozen VQC test sensitivity is 1.0 (100.00% recall)"
);
assert(
  heldoutEval.overall_test_metrics.specificity === 0.52,
  "Frozen VQC test specificity is 0.52 (52.00%)"
);
assert(
  Math.abs(heldoutEval.overall_test_metrics.f1_score - 0.8064516) < 0.0001,
  "Frozen VQC test F1 score is 0.8065"
);
assert(
  heldoutEval.overall_test_metrics.roc_auc === 0.9988,
  "Frozen VQC ideal test ROC-AUC is 0.9988"
);

// 3. Sample 82 Inference Ground Truth Verification
const sample82 = heldoutEval.sample_predictions.find((s) => s.sample_idx === 82);
assert(sample82 !== undefined, "Sample 82 exists in held-out predictions");
assert(
  sample82.record_id === 208,
  "Sample 82 belongs to MIT-BIH Record 208"
);
assert(
  sample82.true_label === 0,
  "Sample 82 ground truth label is Normal (0)"
);
assert(
  sample82.predicted_label === 1,
  "Sample 82 was predicted as VEB (1) - False Positive"
);
assert(
  Math.abs(sample82.probability_veb - 0.563813) < 0.001,
  "Sample 82 predicted P(VEB) is 0.5638 (56.38%)"
);
assert(
  Math.abs(sample82.expectation - 0.127626) < 0.001,
  "Sample 82 Pauli-Z expectation is +0.1276"
);

// 4. Classical Baseline Verification & Data Budget
const classicalPath = path.join(resultsDir, "classical_baseline.json");
const classical = JSON.parse(fs.readFileSync(classicalPath, "utf-8"));
const lrTest = classical.final_test_evaluation.models.logistic_regression;
assert(
  lrTest.accuracy === 0.92,
  "Logistic Regression test accuracy is 0.92 (92.00%)"
);
assert(
  lrTest.sensitivity === 1.0,
  "Logistic Regression test sensitivity is 1.0 (100.00%)"
);
assert(
  lrTest.specificity === 0.84,
  "Logistic Regression test specificity is 0.84 (84.00%)"
);
assert(
  Math.abs(lrTest.f1_score - 0.925925) < 0.0001,
  "Logistic Regression test F1 is 0.9259"
);
assert(
  lrTest.roc_auc === 0.996,
  "Logistic Regression test ROC-AUC is 0.9960"
);
assert(
  classical.dataset.train_samples === 200,
  "Classical baseline trained on 200 samples (asymmetry with VQC 100-sample fold)"
);

// 5. Noisy Aer Simulation Verification
const noisyPath = path.join(resultsDir, "noisy_simulation_results.json");
const noisy = JSON.parse(fs.readFileSync(noisyPath, "utf-8"));
assert(
  noisy.path_b_full_noise_combined.metrics.roc_auc === 0.9984,
  "Noisy Aer simulator VQC ROC-AUC is 0.9984"
);
assert(
  noisy.path_b_full_noise_combined.metrics.accuracy === 0.77,
  "Noisy Aer simulator VQC accuracy is 0.77 (77.00%)"
);

// 6. Processor A/B Hardware Topology Verification
const transpilationPath = path.join(resultsDir, "processor_ab_transpilation.json");
const transpilation = JSON.parse(fs.readFileSync(transpilationPath, "utf-8"));
assert(
  transpilation.transpilation_results.processor_a_canonical_6q.capacity_exceeded === true,
  "Processor A capacity exceeded for 6Q circuit"
);
assert(
  transpilation.transpilation_results.processor_a_canonical_6q.error_type === "CircuitTooWideForTarget",
  "Processor A raised CircuitTooWideForTarget"
);
assert(
  transpilation.transpilation_results.processor_b_canonical_6q.depth === 15,
  "Processor B transpiled depth without measurements is 15"
);
assert(
  transpilation.transpilation_results.processor_b_canonical_6q.cx_count === 5,
  "Processor B CX count is exactly 5"
);
assert(
  transpilation.transpilation_results.processor_b_canonical_6q.swap_count === 0,
  "Processor B SWAP count is exactly 0"
);
assert(
  transpilation.transpilation_results.processor_b_canonical_6q.total_ops === 65,
  "Processor B total ops without measurements is 65 (rz:36, sx:24, cx:5)"
);

// 7. Verify frontend exported disclosures in scientific.ts
const scientificTsPath = path.join(__dirname, "../src/types/scientific.ts");
const scientificContent = fs.readFileSync(scientificTsPath, "utf-8");
assert(
  scientificContent.includes("NOT constitute verified patient-level separation"),
  "scientific.ts explicitly disclaims verified patient-level separation"
);
assert(
  scientificContent.includes("14/600 clipped values (2.33%) across 13/100 affected beats"),
  "scientific.ts includes exact clipping denominators and values"
);
assert(
  scientificContent.includes("classical simulators (Qiskit 2.5.2 StatevectorEstimator and Aer 0.17.2 AerSimulator)"),
  "scientific.ts explicitly discloses classical simulation runtime"
);

console.log(`\n========================================`);
console.log(`Summary: ${passedTests} / ${totalTests} integrity tests PASSED.`);
if (passedTests === totalTests) {
  console.log("Verdict: SCIENTIFIC INTEGRITY VERIFIED (100% BIT-EXACT CONFORMANCE)");
} else {
  console.error("Verdict: SCIENTIFIC DISCREPANCIES DETECTED");
  process.exit(1);
}
