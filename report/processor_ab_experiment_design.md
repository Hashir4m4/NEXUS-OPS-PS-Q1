# NEXUS-OPS — Processor A/B Experiment Design Report
## Reproducible Simulation & Transpilation Protocol

**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Event / Competition:** IBM Quantum Qiskit Fall Fest 2026 (Phase 1)  
**Role:** Quantum Hardware Architecture Research Engineer  
**Date:** 13 October 2026  
**Status:** COMPLETE — REPRODUCIBLE BENCHMARK EXPERIMENT DESIGN  
**Target Processors:** Processor A (5 Qubits), Processor B (9 Qubits)  
**Target Algorithm:** Approved 6-Qubit VQC with Linear Entanglement (`src/vqc_circuit.py`)  

---

## 1. Experiment Overview & Purpose

This document establishes the formal, reproducible protocol for conducting hardware-aware compilation, resource analysis, and simulation across **Processor A** and **Processor B** for Problem Statement **PS-Q1 (Biomedical Signal Classifier)**.

Under the rules set out in the official *Phase 1 Giant Challenge Kit* (`Updated_Challenge_Kit.pdf`, Section 3 & 4), participants must:
1. Construct and execute the defined quantum solution across the two target processors using standardized, controlled parameters.
2. Characterize the effects of coupling graph connectivity, basis gate synthesis, and circuit routing on circuit depth, two-qubit gate count, and noise accumulation.
3. Decouple transpilation/resource metrics from noisy execution metrics.
4. Deliver reproducible code, machine-readable JSON artifacts, and verifiable test suites.

---

## 2. Environment & Dependency Specifications

All experiments are executed within the verified project virtual environment (`.venv`):

- **Python Version:** `3.13.7` (64-bit Windows)
- **Qiskit Core Version:** `2.5.2`
- **Qiskit Aer Version:** `0.17.2`
- **Scientific Stack:** `numpy==2.5.4`, `scipy==1.18.1`, `pandas==3.0.6`
- **Testing Framework:** `pytest==9.1.1`

*Note on Package Changes:* No external packages were installed or modified for this task; all models operate on the pre-installed Qiskit 2.5.2 / Aer 0.17.2 environment.

---

## 3. Hardware Architecture & Configuration Contracts

### 3.1 Processor A Configuration Contract
```json
{
  "name": "Processor_A",
  "num_qubits": 5,
  "coupling_map": [[0, 1], [1, 0], [1, 2], [2, 1], [2, 3], [3, 2], [3, 4], [4, 3]],
  "basis_gates": ["rz", "sx", "x", "cx"],
  "noise_model": {
    "single_qubit_depolarizing_p": 0.001,
    "cx_depolarizing_p": 0.005,
    "readout_error_p": 0.01
  }
}
```

- **Graph Structure:** 1D linear chain $0 \leftrightarrow 1 \leftrightarrow 2 \leftrightarrow 3 \leftrightarrow 4$.
- **Transpilation Policy:**
  - When given circuits with $>5$ logical qubits (such as our 6-qubit VQC), the module reports `CircuitTooWideForTarget` (`capacity_exceeded = True`).
  - To prevent arbitrary truncation of clinical ECG features, Processor A acts as a formal **capacity reference**, proving the necessity of $\ge 6$ physical qubits.
  - For controlled routing studies, a 5-qubit linear reference VQC is mapped to establish baseline resource counts (depth 14, 4 CXs).

### 3.2 Processor B Configuration Contract
```json
{
  "name": "Processor_B",
  "num_qubits": 9,
  "coupling_map": [
    [0, 1], [1, 0], [1, 2], [2, 1],
    [2, 3], [3, 2], [2, 4], [4, 2],
    [4, 5], [5, 4], [5, 6], [6, 5],
    [4, 7], [7, 4], [7, 8], [8, 7]
  ],
  "basis_gates": ["rz", "sx", "x", "cx"],
  "noise_model": {
    "single_qubit_depolarizing_p": 0.001,
    "cx_depolarizing_p": 0.005,
    "readout_error_p": 0.01
  }
}
```

- **Graph Structure:** 9-node heavy-hex-inspired sparse tree with branching vertices at nodes 2 and 4.
- **Embedded Linear Subgraph:** Contains two independent 6-node linear subgraphs:
  $$\text{Chain 1: } 0 \leftrightarrow 1 \leftrightarrow 2 \leftrightarrow 4 \leftrightarrow 5 \leftrightarrow 6$$
  $$\text{Chain 2: } 0 \leftrightarrow 1 \leftrightarrow 2 \leftrightarrow 4 \leftrightarrow 7 \leftrightarrow 8$$
- **Transpilation Policy:** Full-size execution target for the approved 6-qubit VQC.

---

## 4. Controlled Transpilation Protocol

To isolate hardware topology effects from stochastic compiler variations, all transpilation passes adhere to strict invariant controls:

1. **Target Gate Set:** Fixed to $\mathcal{B} = \{\text{rz}, \text{sx}, \text{x}, \text{cx}\}$. All $R_y(\theta)$ gates are compiled via the exact decomposition:
   $$R_y(\theta) = R_z(\pi/2) \cdot S_X \cdot R_z(\theta + \pi) \cdot S_X \cdot R_z(5\pi/2)$$
2. **Optimization Level:** `optimization_level=1` (Qiskit light optimization pass with 2Q commutative cancellation and single-qubit gate combination).
3. **Layout & Routing Method:** SABRE (Stochastic Approach for Budgeting Routing and Embedding) with heuristic lookahead.
4. **Transpiler Seed:** Fixed to `seed_transpiler=42` across all runs to guarantee bit-exact transpiled gate ordering and initial layout selection.
5. **Initial Layout Mapping:**
   For Processor B, SABRE automatically selects:
   - Logical Qubit $0 \to$ Physical Qubit 0
   - Logical Qubit $1 \to$ Physical Qubit 1
   - Logical Qubit $2 \to$ Physical Qubit 2
   - Logical Qubit $3 \to$ Physical Qubit 4
   - Logical Qubit $4 \to$ Physical Qubit 5
   - Logical Qubit $5 \to$ Physical Qubit 6
   - Physical Qubits 3, 7, 8 remain unallocated ancillae.

---

## 5. Simulation Protocol & Noise Modeling

### 5.1 Noise Model Specification
Synthetic noise channels are implemented via `qiskit_aer.noise`:
1. **Single-Qubit Gate Noise:**
   Depolarizing channel $\mathcal{E}_{1q}(\rho) = (1 - p_{1q})\rho + \frac{p_{1q}}{3}\sum_{P \in \{X,Y,Z\}} P\rho P$ with $p_{1q} = 0.001$ applied to all single-qubit native gates (`'x'`, `'sx'`).
2. **Two-Qubit Gate Noise:**
   Two-qubit depolarizing channel with $p_{2q} = 0.005$ applied to all `'cx'` gates.
3. **Readout Error:**
   Symmetric bit-flip confusion matrix on all measured physical qubits:
   $$M = \begin{pmatrix} 1 - p_{ro} & p_{ro} \\ p_{ro} & 1 - p_{ro} \end{pmatrix} = \begin{pmatrix} 0.99 & 0.01 \\ 0.01 & 0.99 \end{pmatrix}$$

### 5.2 Simulation Execution Harness
- **Ideal Reference:** `qiskit.primitives.StatevectorEstimator` computing exact statevector expectation values.
- **Noisy Simulation:** `qiskit_aer.primitives.EstimatorV2` with backend options configured to use the synthetic `NoiseModel`, `seed_simulator=42`, and `default_precision=1/\sqrt{4096} = 0.015625`.
- **Measurement Shots:** Fixed at 4096 shots.

---

## 6. Metrics Decoupling & Output Schema

The experimental results are separated into two distinct analytical tiers:

### Tier 1: Hardware Resource & Routing Metrics
- **Logical Qubits ($N_{\text{logical}}$):** Number of active algorithm variables (6).
- **Physical Qubits ($N_{\text{physical}}$):** Chip capacity (5 on A, 9 on B).
- **Transpiled Circuit Depth ($D$):** Longest gate path in the compiled DAG.
- **Two-Qubit CX Count ($N_{\text{CX}}$):** Total physical CNOT gates.
- **Routing Overhead ($\Delta N_{\text{CX}}$):** Extra CX gates inserted beyond logical circuit ($N_{\text{CX, compiled}} - N_{\text{CX, logical}}$).
- **SWAP Count ($N_{\text{SWAP}}$):** Number of explicit or decomposed SWAPs.
- **Single-Qubit Gate Count ($N_{1Q}$):** Total `rz` and `sx` gates.

### Tier 2: Algorithmic & Noise Impact Metrics
- **Ideal Expectation ($\langle \bar{Z} \rangle_{\text{ideal}}$):** Noise-free expectation value.
- **Noisy Expectation ($\langle \bar{Z} \rangle_{\text{noisy}}$):** Expectation under depolarizing and readout noise.
- **Standard Error ($\text{SE}$):** $1/\sqrt{N_{\text{shots}}} = 0.015625$.
- **Noise Shift ($|\Delta E|$):** $|\langle \bar{Z} \rangle_{\text{noisy}} - \langle \bar{Z} \rangle_{\text{ideal}}|$.

---

## 7. Automated Test & Regression Architecture

The test suite in [`tests/test_processor_ab.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests/test_processor_ab.py) implements 10 targeted assertions:
1. `test_processor_a_config_integrity`: Validates Processor A JSON fields, 5 qubits, basis gates, and noise params.
2. `test_processor_a_coupling_map_structure`: Validates 5-node linear graph edges.
3. `test_processor_a_noise_model_structure`: Validates 1Q, 2Q, and readout noise channels.
4. `test_processor_b_config_integrity`: Validates Processor B JSON fields, 9 qubits, basis gates, and noise params.
5. `test_processor_b_coupling_map_structure`: Validates 9-node sparse tree graph edges.
6. `test_processor_a_capacity_rejection_for_6q_vqc`: Confirms graceful rejection of 6Q circuits with `CircuitTooWideForTarget`.
7. `test_processor_a_5q_reference_transpilation`: Tests 5Q reference circuit on line (0 SWAPs) vs. branching tree (+3 CX overhead).
8. `test_processor_b_vqc_transpilation_zero_swap_overhead`: Confirms approved 6Q VQC maps to Processor B with depth 15, 5 CXs, and 0 SWAPs.
9. `test_processor_b_cyclic_variant_transpilation`: Validates alternative 9-qubit cyclic mesh candidate.
10. `test_processor_b_ideal_and_noisy_simulation`: Validates `EstimatorV2` execution and verifies noise shift remains within theoretical bounds.

---

## 8. Integration Plan for Subsequent Milestones

1. **Step 2 / Step 3 (Milestone 5F.3):** Full LORO cross-validation training will be executed using ideal statevector estimation to avoid stochastic optimizer divergence during parameter search.
2. **Step 4 (Final Evaluation):** Once final trained variational parameters $\boldsymbol{\theta}^*$ are frozen, the complete 200-beat training set and 100-beat quarantined test set will be evaluated through `simulate_processor_b()` to measure the exact classification accuracy drop caused by physical hardware noise on Processor B.
3. **Processor D Proposal (Phase 1 Final Report):** The zero-SWAP alignment achieved on Processor B will serve as the baseline for designing custom **Processor D**, exploring whether asymmetric coupling or dedicated readout ancillae further reduce biomedical classification latency.
