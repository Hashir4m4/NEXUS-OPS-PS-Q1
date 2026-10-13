"""NEXUS-OPS Processor B Module.

Defines the 9-qubit primary execution hardware architecture (Processor B) for
Qiskit Fall Fest 2026 Phase 1 benchmarking.

Authoritative specification:
- 9 physical qubits
- Canonical topology: Heavy-hex-inspired sparse graph
    Coupling map: (0,1), (1,2), (2,3), (2,4), (4,5), (5,6), (4,7), (7,8) (bidirectional)
- Alternative topology: 9-qubit cyclic 12-edge mesh (from Oct 11 organizer draft)
- Basis gates: ['rz', 'sx', 'x', 'cx']
- Challenge synthetic noise model:
    * 1-qubit depolarizing: p = 0.001 (on 'x', 'sx')
    * 2-qubit depolarizing: p = 0.005 (on 'cx')
    * Readout bit-flip: p = 0.01 per measured qubit
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.exceptions import QiskitError
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
from qiskit_aer.primitives import EstimatorV2

CONFIG_DIR = Path(__file__).resolve().parent


def get_processor_b_config(variant: str = "canonical") -> Dict[str, Any]:
    """Load Processor B configuration.

    Args:
        variant: 'canonical' (9-qubit sparse tree) or 'cyclic' (9-qubit 12-edge mesh).

    Returns:
        Configuration dictionary parsed from JSON.
    """
    if variant == "canonical":
        config_path = CONFIG_DIR / "processor_B.json"
    elif variant == "cyclic":
        config_path = CONFIG_DIR / "processor_B_cyclic.json"
    else:
        raise ValueError(f"Unknown Processor B variant: {variant}. Expected 'canonical' or 'cyclic'.")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_processor_b_coupling_map(variant: str = "canonical") -> CouplingMap:
    """Construct the Qiskit CouplingMap for Processor B.

    Args:
        variant: 'canonical' or 'cyclic'.

    Returns:
        Configured CouplingMap with bidirectional connectivity.
    """
    config = get_processor_b_config(variant=variant)
    coupling_list = [tuple(edge) for edge in config["coupling_map"]]
    return CouplingMap(coupling_list)


def build_processor_b_noise_model(config: Optional[Dict[str, Any]] = None) -> NoiseModel:
    """Construct the synthetic Qiskit Aer NoiseModel for Processor B.

    Args:
        config: Optional configuration dictionary. If None, loads canonical config.

    Returns:
        Configured Qiskit Aer NoiseModel.
    """
    if config is None:
        config = get_processor_b_config()

    noise_cfg = config.get("noise_model", {})
    p_1q = noise_cfg.get("single_qubit_depolarizing_p", 0.001)
    p_2q = noise_cfg.get("cx_depolarizing_p", 0.005)
    p_ro = noise_cfg.get("readout_error_p", 0.01)

    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(depolarizing_error(p_1q, 1), ["x", "sx"])
    noise_model.add_all_qubit_quantum_error(depolarizing_error(p_2q, 2), ["cx"])

    ro_error = ReadoutError([[1.0 - p_ro, p_ro], [p_ro, 1.0 - p_ro]])
    noise_model.add_all_qubit_readout_error(ro_error)

    return noise_model


def transpile_for_processor_b(
    circuit: QuantumCircuit,
    variant: str = "canonical",
    optimization_level: int = 1,
    seed_transpiler: int = 42,
) -> Dict[str, Any]:
    """Transpile a quantum circuit onto Processor B.

    Args:
        circuit: Input logical QuantumCircuit.
        variant: 'canonical' or 'cyclic'.
        optimization_level: Qiskit optimization level (default 1).
        seed_transpiler: Transpiler seed for SABRE determinism (default 42).

    Returns:
        Dictionary containing transpilation metrics, status, and compiled circuit.
    """
    config = get_processor_b_config(variant=variant)
    cmap = build_processor_b_coupling_map(variant=variant)
    basis_gates = config.get("basis_gates", ["rz", "sx", "x", "cx"])

    if circuit.num_qubits > config["num_qubits"]:
        return {
            "success": False,
            "processor": config["name"],
            "logical_qubits": circuit.num_qubits,
            "physical_qubits": config["num_qubits"],
            "capacity_exceeded": True,
            "error_type": "CircuitTooWideForTarget",
            "message": (
                f"Circuit width ({circuit.num_qubits} qubits) exceeds Processor B "
                f"physical capacity ({config['num_qubits']} qubits)."
            ),
            "transpiled_circuit": None,
            "depth": None,
            "cx_count": None,
            "swap_count": None,
            "total_ops": None,
            "ops": None,
            "initial_layout": None,
            "routing_overhead_cx": None,
        }

    logical_cx = circuit.count_ops().get("cx", 0)

    try:
        compiled = transpile(
            circuit,
            coupling_map=cmap,
            basis_gates=basis_gates,
            optimization_level=optimization_level,
            seed_transpiler=seed_transpiler,
        )
    except QiskitError as err:
        return {
            "success": False,
            "processor": config["name"],
            "logical_qubits": circuit.num_qubits,
            "physical_qubits": config["num_qubits"],
            "capacity_exceeded": False,
            "error_type": type(err).__name__,
            "message": str(err),
            "transpiled_circuit": None,
            "depth": None,
            "cx_count": None,
            "swap_count": None,
            "total_ops": None,
            "ops": None,
            "initial_layout": None,
            "routing_overhead_cx": None,
        }

    ops = dict(compiled.count_ops())
    cx_count = ops.get("cx", 0)
    swap_count = ops.get("swap", 0)
    total_ops = sum(ops.values())
    overhead_cx = max(0, cx_count - logical_cx)

    # Format layout if present
    layout_repr = None
    if compiled.layout and compiled.layout.initial_layout:
        layout_repr = str(compiled.layout.initial_layout)

    return {
        "success": True,
        "processor": config["name"],
        "logical_qubits": circuit.num_qubits,
        "physical_qubits": config["num_qubits"],
        "capacity_exceeded": False,
        "error_type": None,
        "message": "Transpilation successful.",
        "transpiled_circuit": compiled,
        "depth": compiled.depth(),
        "cx_count": cx_count,
        "swap_count": swap_count,
        "total_ops": total_ops,
        "ops": ops,
        "initial_layout": layout_repr,
        "routing_overhead_cx": overhead_cx,
    }


def simulate_processor_b(
    circuit: QuantumCircuit,
    observable: SparsePauliOp,
    pub_parameters: np.ndarray,
    shots: int = 4096,
    seed_simulator: int = 42,
    run_noisy: bool = True,
) -> Dict[str, Any]:
    """Execute ideal and noisy simulations on Processor B target.

    Args:
        circuit: Parameterized or bound QuantumCircuit.
        observable: Target SparsePauliOp observable.
        pub_parameters: 2D array of parameters shaped (N, num_params).
        shots: Number of measurement shots for Aer simulation (default 4096).
        seed_simulator: Simulation seed for Aer RNG.
        run_noisy: Whether to execute noisy Aer simulation in addition to ideal.

    Returns:
        Dictionary of expectation values, errors, and execution metrics.
    """
    pub = (circuit, observable, pub_parameters)

    # 1. Ideal Statevector execution
    sv_est = StatevectorEstimator()
    job_ideal = sv_est.run([pub])
    res_ideal = job_ideal.result()
    evs_ideal = np.asarray(res_ideal[0].data.evs)

    results: Dict[str, Any] = {
        "ideal_expectation": float(evs_ideal[0]) if evs_ideal.size == 1 else evs_ideal.tolist(),
        "shots": shots,
        "seed_simulator": seed_simulator,
    }

    if not run_noisy:
        return results

    # 2. Noisy Aer simulation
    noise_model = build_processor_b_noise_model()
    precision = 1.0 / np.sqrt(shots)

    aer_est = EstimatorV2(
        options={
            "default_precision": precision,
            "run_options": {"shots": shots},
            "backend_options": {"noise_model": noise_model, "seed_simulator": seed_simulator},
        }
    )

    job_noisy = aer_est.run([pub])
    res_noisy = job_noisy.result()
    evs_noisy = np.asarray(res_noisy[0].data.evs)
    stds_noisy = np.asarray(res_noisy[0].data.stds) if hasattr(res_noisy[0].data, "stds") else None

    results["noisy_expectation"] = float(evs_noisy[0]) if evs_noisy.size == 1 else evs_noisy.tolist()
    if stds_noisy is not None:
        results["noisy_std_error"] = float(stds_noisy[0]) if stds_noisy.size == 1 else stds_noisy.tolist()
    else:
        results["noisy_std_error"] = precision

    if evs_ideal.size == 1:
        results["absolute_deviation"] = abs(float(evs_noisy[0]) - float(evs_ideal[0]))
    else:
        results["absolute_deviation"] = np.abs(evs_noisy - evs_ideal).tolist()

    return results
