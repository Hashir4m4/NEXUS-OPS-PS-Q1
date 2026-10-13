"""NEXUS-OPS Processor Topologies and Benchmark Modules.

Authoritative processor models and simulation pipelines for Qiskit Fall Fest 2026.
"""

from .processor_a import (
    get_processor_a_config,
    build_processor_a_coupling_map,
    build_processor_a_noise_model,
    transpile_for_processor_a,
)
from .processor_b import (
    get_processor_b_config,
    build_processor_b_coupling_map,
    build_processor_b_noise_model,
    transpile_for_processor_b,
    simulate_processor_b,
)

__all__ = [
    "get_processor_a_config",
    "build_processor_a_coupling_map",
    "build_processor_a_noise_model",
    "transpile_for_processor_a",
    "get_processor_b_config",
    "build_processor_b_coupling_map",
    "build_processor_b_noise_model",
    "transpile_for_processor_b",
    "simulate_processor_b",
]
