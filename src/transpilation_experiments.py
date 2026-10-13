"""
Transpilation Experiments & Multi-Seed Processor Architecture Benchmarks
========================================================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Phase 6: Hardware Experiments)

Responsibilities:
-----------------
1. Systematically evaluate circuit compilation across Processor A and Processor B topologies.
2. Verify hardware capacity enforcement (Processor A 5Q limit vs. Approved 6Q VQC).
3. Benchmark reference circuits on 5Q configurations (canonical line vs. branching tree).
4. Perform multi-seed transpilation on Processor B (canonical tree vs. cyclic mesh)
   across optimization levels 1, 2, and 3.
5. Quantify depth, 2-qubit (CX) gate count, SWAP count, total operations, and routing overhead.
6. Compute rigorous multi-seed summary statistics and serialize to results/transpilation_comparison.json.
"""

from collections import defaultdict
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from qiskit import QuantumCircuit, transpile
from qiskit.exceptions import QiskitError

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.vqc_circuit import (
    NUM_QUBITS,
    NUM_VARIATIONAL_PARAMS,
    create_parameter_vectors,
    build_vqc_circuit,
)
from processors.processor_a import (
    get_processor_a_config,
    build_processor_a_coupling_map,
    transpile_for_processor_a,
)
from processors.processor_b import (
    get_processor_b_config,
    build_processor_b_coupling_map,
    transpile_for_processor_b,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"


def build_reference_5q_vqc() -> QuantumCircuit:
    """
    Constructs a 5-qubit reference VQC matching the architecture pattern
    for capacity-limited Processor A evaluation.
    """
    from qiskit.circuit import ParameterVector
    from qiskit.circuit.library import real_amplitudes
    
    p_enc = ParameterVector("p_enc", 5)
    p_var = ParameterVector("p_var", 10)
    
    qc = QuantumCircuit(5, name="Reference_VQC_5Q")
    for i in range(5):
        qc.ry(p_enc[i], i)
    qc.barrier()
    
    ansatz = real_amplitudes(num_qubits=5, reps=1, entanglement="linear", parameter_prefix="p_var")
    qc.compose(ansatz, inplace=True)
    return qc


def run_transpilation_benchmarks(
    seeds: Optional[List[int]] = None,
    opt_levels: Optional[List[int]] = None,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes the complete multi-seed transpilation benchmark suite.

    Parameters
    ----------
    seeds : Optional[List[int]]
        List of transpiler random seeds (default: [42, 101, 202, 303, 404]).
    opt_levels : Optional[List[int]]
        List of Qiskit optimization levels (default: [1, 2, 3]).
    output_path : Optional[Path]
        Target JSON filepath for serialization.

    Returns
    -------
    Dict[str, Any]
        Structured benchmark results dictionary.
    """
    seeds = seeds or [42, 101, 202, 303, 404]
    opt_levels = opt_levels or [1, 2, 3]
    out_file = output_path or (RESULTS_DIR / "transpilation_comparison.json")

    # 1. Circuit instantiation
    p_enc, p_var = create_parameter_vectors()
    approved_6q_vqc = build_vqc_circuit(p_enc, p_var)
    reference_5q_vqc = build_reference_5q_vqc()

    raw_benchmarks = {}

    # -------------------------------------------------------------
    # 2. Processor A Capacity & Baseline Benchmarks
    # -------------------------------------------------------------
    # 2.1 Approved 6Q VQC on Processor A (Canonical Line) -> Must fail cleanly
    res_a_6q = transpile_for_processor_a(approved_6q_vqc, variant="canonical")
    raw_benchmarks["processor_a_canonical_6q_approved"] = {
        "processor": "Processor A (Canonical Line, 5Q)",
        "circuit": "Approved VQC (6Q)",
        "success": res_a_6q["success"],
        "capacity_exceeded": res_a_6q["capacity_exceeded"],
        "error_type": res_a_6q["error_type"],
        "message": res_a_6q["message"],
    }

    # 2.2 Approved 6Q VQC on Processor A (Branching Tree) -> Must fail cleanly
    res_a_branch_6q = transpile_for_processor_a(approved_6q_vqc, variant="branching")
    raw_benchmarks["processor_a_branching_6q_approved"] = {
        "processor": "Processor A (Branching Tree, 5Q)",
        "circuit": "Approved VQC (6Q)",
        "success": res_a_branch_6q["success"],
        "capacity_exceeded": res_a_branch_6q["capacity_exceeded"],
        "error_type": res_a_branch_6q["error_type"],
        "message": res_a_branch_6q["message"],
    }

    # 2.3 Reference 5Q VQC on Processor A across seeds & opt levels
    proc_a_5q_results = defaultdict(lambda: defaultdict(list))
    for variant in ["canonical", "branching"]:
        for opt in opt_levels:
            for s in seeds:
                res = transpile_for_processor_a(
                    reference_5q_vqc,
                    variant=variant,
                    optimization_level=opt,
                    seed_transpiler=s,
                )
                if res["success"]:
                    proc_a_5q_results[variant][opt].append({
                        "seed": s,
                        "depth": res["depth"],
                        "cx_count": res["cx_count"],
                        "swap_count": res["swap_count"],
                        "total_ops": res["total_ops"],
                        "ops": res["ops"],
                        "routing_overhead_cx": res.get("routing_overhead_cx", max(0, res["cx_count"] - 4)),
                    })

    # -------------------------------------------------------------
    # 3. Processor B Multi-Seed Transpilation Benchmarks (Approved 6Q)
    # -------------------------------------------------------------
    proc_b_6q_results = defaultdict(lambda: defaultdict(list))
    for variant in ["canonical", "cyclic"]:
        for opt in opt_levels:
            for s in seeds:
                res = transpile_for_processor_b(
                    approved_6q_vqc,
                    variant=variant,
                    optimization_level=opt,
                    seed_transpiler=s,
                )
                if res["success"]:
                    proc_b_6q_results[variant][opt].append({
                        "seed": s,
                        "depth": res["depth"],
                        "cx_count": res["cx_count"],
                        "swap_count": res["swap_count"],
                        "total_ops": res["total_ops"],
                        "ops": res["ops"],
                        "initial_layout": res["initial_layout"],
                        "routing_overhead_cx": res["routing_overhead_cx"],
                    })

    # -------------------------------------------------------------
    # 4. Aggregate Statistical Synthesis
    # -------------------------------------------------------------
    def _calc_stats(run_list: List[Dict[str, Any]], field: str) -> Dict[str, float]:
        vals = [r[field] for r in run_list]
        return {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)),
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
        }

    statistical_summary = {
        "processor_a_reference_5q": {},
        "processor_b_approved_6q": {},
    }

    for variant, opt_dict in proc_a_5q_results.items():
        statistical_summary["processor_a_reference_5q"][variant] = {}
        for opt, runs in opt_dict.items():
            statistical_summary["processor_a_reference_5q"][variant][f"opt_level_{opt}"] = {
                "num_runs": len(runs),
                "depth": _calc_stats(runs, "depth"),
                "cx_count": _calc_stats(runs, "cx_count"),
                "total_ops": _calc_stats(runs, "total_ops"),
                "routing_overhead_cx": _calc_stats(runs, "routing_overhead_cx"),
            }

    for variant, opt_dict in proc_b_6q_results.items():
        statistical_summary["processor_b_approved_6q"][variant] = {}
        for opt, runs in opt_dict.items():
            statistical_summary["processor_b_approved_6q"][variant][f"opt_level_{opt}"] = {
                "num_runs": len(runs),
                "depth": _calc_stats(runs, "depth"),
                "cx_count": _calc_stats(runs, "cx_count"),
                "swap_count": _calc_stats(runs, "swap_count"),
                "total_ops": _calc_stats(runs, "total_ops"),
                "routing_overhead_cx": _calc_stats(runs, "routing_overhead_cx"),
            }

    # Complete document assembly
    payload = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "seeds": seeds,
            "optimization_levels": opt_levels,
            "logical_circuit_specs": {
                "approved_6q_vqc": {
                    "num_qubits": 6,
                    "depth": approved_6q_vqc.depth(),
                    "cx_count": approved_6q_vqc.count_ops().get("cx", 0),
                    "total_params": len(approved_6q_vqc.parameters),
                },
                "reference_5q_vqc": {
                    "num_qubits": 5,
                    "depth": reference_5q_vqc.depth(),
                    "cx_count": reference_5q_vqc.count_ops().get("cx", 0),
                    "total_params": len(reference_5q_vqc.parameters),
                },
            },
        },
        "capacity_boundary_checks": {
            "processor_a_canonical_6q_approved": raw_benchmarks["processor_a_canonical_6q_approved"],
            "processor_a_branching_6q_approved": raw_benchmarks["processor_a_branching_6q_approved"],
        },
        "statistical_summary": statistical_summary,
        "detailed_runs": {
            "processor_a_reference_5q": proc_a_5q_results,
            "processor_b_approved_6q": proc_b_6q_results,
        },
    }

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload


if __name__ == "__main__":
    res = run_transpilation_benchmarks()
    print("Transpilation benchmarks completed successfully!")
    print(f"Saved to: {RESULTS_DIR / 'transpilation_comparison.json'}")
