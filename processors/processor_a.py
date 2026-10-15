"""NEXUS-OPS Processor A Module.

Defines the 5-qubit baseline hardware architecture (Processor A) for
Qiskit Fall Fest 2026 Phase 1 benchmarking.

Authoritative specification:
- 5 physical qubits
- Canonical topology: 1D nearest-neighbor chain 0-1-2-3-4
- Alternative topology: 5-qubit branching tree (from Oct 11 organizer draft)
- Basis gates: ['rz', 'sx', 'x', 'cx']
- Challenge synthetic noise model:
    * 1-qubit depolarizing: p = 0.001 (on 'x', 'sx')
    * 2-qubit depolarizing: p = 0.005 (on 'cx')
    * Readout bit-flip: p = 0.01 per measured qubit
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from qiskit import QuantumCircuit, transpile
from qiskit.exceptions import QiskitError
from qiskit.transpiler import CouplingMap

CONFIG_DIR = Path(__file__).resolve().parent


def get_processor_a_config(variant: str = "canonical") -> Dict[str, Any]:
    """Load Processor A configuration.

    Args:
        variant: 'canonical' (5-qubit line) or 'branching' (5-qubit tree).

    Returns:
        Configuration dictionary parsed from JSON.
    """
    if variant == "canonical":
        config_path = CONFIG_DIR / "processor_A.json"
    elif variant == "branching":
        config_path = CONFIG_DIR / "processor_A_branching.json"
    else:
        raise ValueError(f"Unknown Processor A variant: {variant}. Expected 'canonical' or 'branching'.")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_processor_a_coupling_map(variant: str = "canonical") -> CouplingMap:
    """Construct the Qiskit CouplingMap for Processor A.

    Args:
        variant: 'canonical' or 'branching'.

    Returns:
        Configured CouplingMap with bidirectional connectivity.
    """
    config = get_processor_a_config(variant=variant)
    coupling_list = [tuple(edge) for edge in config["coupling_map"]]
    return CouplingMap(coupling_list)


def build_processor_a_noise_model(config: Optional[Dict[str, Any]] = None) -> Any:
    """Construct the synthetic Qiskit Aer NoiseModel for Processor A.

    Args:
        config: Optional configuration dictionary. If None, loads canonical config.

    Returns:
        Configured Qiskit Aer NoiseModel.
    """
    from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

    if config is None:
        config = get_processor_a_config()

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


def transpile_for_processor_a(
    circuit: QuantumCircuit,
    variant: str = "canonical",
    optimization_level: int = 1,
    seed_transpiler: int = 42,
) -> Dict[str, Any]:
    """Transpile a quantum circuit onto Processor A.

    If circuit.num_qubits > 5, reports capacity overflow according to the
    official QFF Phase 1 rule (Updated_Challenge_Kit.pdf Section 3.1 & 12).

    Args:
        circuit: Input logical QuantumCircuit.
        variant: 'canonical' or 'branching'.
        optimization_level: Qiskit optimization level (default 1).
        seed_transpiler: Transpiler seed for SABRE determinism (default 42).

    Returns:
        Dictionary containing transpilation metrics, status, and compiled circuit.
    """
    config = get_processor_a_config(variant=variant)
    cmap = build_processor_a_coupling_map(variant=variant)
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
                f"Circuit width ({circuit.num_qubits} qubits) exceeds Processor A "
                f"physical capacity ({config['num_qubits']} qubits). In accordance with "
                "Challenge Kit Section 3.1, Processor A serves as a capacity reference, "
                "and full-size execution is performed on Processor B."
            ),
            "transpiled_circuit": None,
            "depth": None,
            "cx_count": None,
            "swap_count": None,
            "total_ops": None,
            "ops": None,
        }

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
        }

    ops = dict(compiled.count_ops())
    cx_count = ops.get("cx", 0)
    swap_count = ops.get("swap", 0)
    total_ops = sum(ops.values())

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
    }
