"""
Controlled Shot-Count Scaling & Finite Sampling Analysis
=========================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Phase 6: Hardware Experiments)

Responsibilities:
-----------------
1. Systematically investigate shot noise scaling across finite shot budgets:
   S in [256, 512, 1024, 2048, 4096] (plus infinite/statevector limit).
2. For each shot budget, execute multiple simulation seeds [42, 101, 202]
   to quantify sample variance and empirical confidence intervals.
3. Verify theoretical shot-noise scaling law: sigma_empirical ~ 1 / sqrt(S).
4. Measure classification stability, prediction flip rates, and threshold sensitivity.
5. Serialize comprehensive results to results/shot_based_results.json.
"""

import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from qiskit import transpile
from qiskit.primitives import StatevectorEstimator
from qiskit_aer.primitives import EstimatorV2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.vqc_circuit import (
    create_parameter_vectors,
    build_vqc_circuit,
    build_ensemble_z_observable,
    format_pub_parameters,
    expectation_to_probability,
)
from src.vqc_training import compute_vqc_metrics
from src.vqc_preprocessing import prepare_final_benchmark_datasets
from processors.processor_b import (
    build_processor_b_coupling_map,
    build_processor_b_noise_model,
)

RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def run_shot_scaling_experiment(
    shot_budgets: Optional[List[int]] = None,
    sim_seeds: Optional[List[int]] = None,
    seed_transpiler: int = 42,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes controlled shot-scaling experiments on the held-out test cohort.

    Parameters
    ----------
    shot_budgets : Optional[List[int]]
        List of shot counts to benchmark (default: [256, 512, 1024, 2048, 4096]).
    sim_seeds : Optional[List[int]]
        List of simulator RNG seeds for variance estimation (default: [42, 101, 202]).
    seed_transpiler : int
        RNG seed for transpilation.
    output_path : Optional[Path]
        Output path for results JSON.

    Returns
    -------
    Dict[str, Any]
        Complete shot scaling results dictionary.
    """
    shot_budgets = shot_budgets or [256, 512, 1024, 2048, 4096]
    sim_seeds = sim_seeds or [42, 101, 202]
    out_file = output_path or (RESULTS_DIR / "shot_based_results.json")

    # 1. Load frozen selected model
    sel_path = RESULTS_DIR / "vqc_model_selection.json"
    with open(sel_path, "r", encoding="utf-8") as f:
        selected_data = json.load(f)
    theta_opt = np.array(selected_data["selected_candidate"]["optimal_theta"], dtype=float)

    # 2. Load held-out test cohort
    train_csv = DATA_DIR / "features_train.csv"
    test_csv = DATA_DIR / "features_test.csv"
    df_train = pd.read_csv(train_csv)
    df_test = pd.read_csv(test_csv)

    final_train, final_test, _ = prepare_final_benchmark_datasets(df_train, df_test)
    X_test, y_test = final_test.X, final_test.y
    num_samples = len(y_test)

    # 3. Transpile circuit and map observable
    p_enc, p_var = create_parameter_vectors()
    vqc_circuit = build_vqc_circuit(p_enc, p_var)
    logical_obs = build_ensemble_z_observable()

    cmap = build_processor_b_coupling_map(variant="canonical")
    basis_gates = ["rz", "sx", "x", "cx"]
    compiled_circuit = transpile(
        vqc_circuit,
        coupling_map=cmap,
        basis_gates=basis_gates,
        optimization_level=1,
        seed_transpiler=seed_transpiler,
    )
    physical_obs = logical_obs.apply_layout(compiled_circuit.layout)
    pub_params = format_pub_parameters(X_test, theta_opt)

    # 4. Statevector Exact Baseline
    sv_estimator = StatevectorEstimator()
    job_sv = sv_estimator.run([(compiled_circuit, physical_obs, pub_params)])
    res_sv = job_sv.result()
    evs_exact = np.asarray(res_sv[0].data.evs, dtype=float)
    probs_exact = expectation_to_probability(evs_exact)
    preds_exact = (probs_exact >= 0.5).astype(int)
    exact_metrics = compute_vqc_metrics(y_test, probs_exact).to_dict()

    # 5. Shot Scaling Sweep
    noise_model = build_processor_b_noise_model()
    shot_results = {}

    for s_count in shot_budgets:
        theoretical_sigma = 1.0 / np.sqrt(s_count)
        seed_runs = []
        all_evs = []

        for seed in sim_seeds:
            aer_est = EstimatorV2(
                options={
                    "default_precision": theoretical_sigma,
                    "run_options": {"shots": s_count},
                    "backend_options": {
                        "noise_model": noise_model,
                        "seed_simulator": seed,
                    },
                }
            )
            job = aer_est.run([(compiled_circuit, physical_obs, pub_params)])
            res = job.result()
            evs_noisy = np.clip(np.asarray(res[0].data.evs, dtype=float), -1.0, 1.0)
            probs_noisy = expectation_to_probability(evs_noisy)
            preds_noisy = (probs_noisy >= 0.5).astype(int)
            m = compute_vqc_metrics(y_test, probs_noisy).to_dict()

            mae_vs_exact = float(np.mean(np.abs(evs_noisy - evs_exact)))
            flips = int(np.sum(preds_noisy != preds_exact))

            all_evs.append(evs_noisy)
            seed_runs.append({
                "seed": seed,
                "metrics": m,
                "mae_vs_exact": mae_vs_exact,
                "flips_vs_exact": flips,
                "flip_rate": float(flips / num_samples),
            })

        # Calculate empirical standard deviation across seeds for each sample, then average
        all_evs_arr = np.array(all_evs)  # shape: (num_seeds, num_samples)
        sample_stds = np.std(all_evs_arr, axis=0)
        empirical_sigma = float(np.mean(sample_stds))

        # Metric averages across seeds
        accs = [r["metrics"]["accuracy"] for r in seed_runs]
        f1s = [r["metrics"]["f1_score"] for r in seed_runs]
        sens = [r["metrics"]["sensitivity"] for r in seed_runs]
        specs = [r["metrics"]["specificity"] for r in seed_runs]
        mses = [r["metrics"]["mse_loss"] for r in seed_runs]
        aucs = [r["metrics"]["roc_auc"] for r in seed_runs]
        maes = [r["mae_vs_exact"] for r in seed_runs]
        flip_rates = [r["flip_rate"] for r in seed_runs]

        shot_results[str(s_count)] = {
            "shots": s_count,
            "theoretical_precision": float(theoretical_sigma),
            "empirical_mean_std": empirical_sigma,
            "std_ratio_empirical_to_theoretical": float(empirical_sigma / theoretical_sigma) if theoretical_sigma > 0 else 0.0,
            "summary_metrics": {
                "accuracy": {"mean": float(np.mean(accs)), "std": float(np.std(accs))},
                "f1_score": {"mean": float(np.mean(f1s)), "std": float(np.std(f1s))},
                "sensitivity": {"mean": float(np.mean(sens)), "std": float(np.std(sens))},
                "specificity": {"mean": float(np.mean(specs)), "std": float(np.std(specs))},
                "mse_loss": {"mean": float(np.mean(mses)), "std": float(np.std(mses))},
                "roc_auc": {"mean": float(np.mean(aucs)), "std": float(np.std(aucs))},
                "mae_vs_exact": {"mean": float(np.mean(maes)), "std": float(np.std(maes))},
                "flip_rate": {"mean": float(np.mean(flip_rates)), "std": float(np.std(flip_rates))},
            },
            "individual_runs": seed_runs,
        }

    payload = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "processor": "Processor B (Canonical Sparse Tree, 9Q)",
            "shot_budgets": shot_budgets,
            "simulation_seeds": sim_seeds,
            "num_test_samples": num_samples,
            "noise_model": {
                "single_qubit_depolarizing_p": 0.001,
                "cx_depolarizing_p": 0.005,
                "readout_error_p": 0.01,
            },
        },
        "exact_statevector_baseline": exact_metrics,
        "shot_scaling_results": shot_results,
    }

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


if __name__ == "__main__":
    res = run_shot_scaling_experiment()
    print("Shot scaling experiment completed successfully!")
    print(f"Saved to: {RESULTS_DIR / 'shot_based_results.json'}")
    for shots, data in res["shot_scaling_results"].items():
        sm = data["summary_metrics"]
        print(f"Shots: {shots:4s} | Acc: {sm['accuracy']['mean']:.4f} +- {sm['accuracy']['std']:.4f} | F1: {sm['f1_score']['mean']:.4f} | MAE: {sm['mae_vs_exact']['mean']:.4f} | Emp Std: {data['empirical_mean_std']:.4f} (Theo: {data['theoretical_precision']:.4f})")
