# NEXUS-OPS — Quantum Processor Architecture & Transpilation Comparison
**Project:** IBM Quantum Qiskit Fall Fest 2026 | Project Q | PS-Q1 Biomedical Classifier  
**Milestone:** Phase 6 — Quantum Hardware Experiments (Stage 7 & 10)  
**Status:** COMPLETED & AUDITED  
**Date:** 2026-10-13  

---

## 1. Executive Summary

This report delivers a rigorous comparative architectural analysis of **Processor A** (5-qubit baseline) versus **Processor B** (9-qubit execution target) for the NEXUS-OPS 6-qubit Variational Quantum Classifier (VQC).

To evaluate compiler robustness, transpilation determinism, and routing overhead, compiler synthesis was systematically benchmarked across:
- **Target Topologies:**
  1. *Processor A Canonical:* 5-qubit linear nearest-neighbor chain ($0-1-2-3-4$).
  2. *Processor A Branching Alternative:* 5-qubit tree ($0-1$, $1-2$, $1-3$, $3-4$).
  3. *Processor B Canonical:* 9-qubit heavy-hex-inspired sparse tree ($8$ bidirectional edges).
  4. *Processor B Cyclic Alternative:* 9-qubit mesh ($12$ bidirectional edges).
- **Compilation Configurations:** Qiskit transpiler optimization levels 1, 2, and 3 across **5 distinct random seeds** (`seeds = [42, 101, 202, 303, 404]`).

### Key Architectural Findings
1. **Physical Capacity Boundary:** The approved 6-qubit VQC strictly requires 6 logical qubits. Transpiling onto Processor A raises `CircuitTooWideForTarget` ($6 > 5$ qubits), adhering to Updated Challenge Kit Sections 3.1 & 12. Processor A serves as a capacity baseline, while Processor B serves as the primary execution hardware.
2. **Zero SWAP Overhead on Processor B:** The canonical Processor B topology contains a linear subgraph of length 6. Across all 5 random seeds and all 3 optimization levels, the approved 6-qubit VQC compiles with **zero SWAP gates** and **zero extra CX overhead** (compiling to exactly 5 CX gates, depth 15, and 65 total operations).
3. **Topology Penalty on Branching Topologies:** Evaluating a 5-qubit reference circuit on Processor A demonstrated that a non-linear branching tree incurs a **$+75\%$ CX gate overhead** (7 CX vs 4 CX) and a **$+43.8\%$ depth expansion** (depth 23 vs 16) compared to the linear chain, proving that matching algorithmic entanglement to physical connectivity is vital for NISQ fidelity.

---

## 2. Hardware Topology & Basis Gate Specifications

| Specification Metric | Processor A (Canonical Line) | Processor A (Branching Tree) | Processor B (Canonical Sparse Tree) | Processor B (Cyclic Mesh) |
| :--- | :---: | :---: | :---: | :---: |
| **Physical Qubit Count** | 5 | 5 | 9 | 9 |
| **Coupling Edges (Directed)** | 8 (4 bidirectional) | 8 (4 bidirectional) | 16 (8 bidirectional) | 24 (12 bidirectional) |
| **Max Degree (Hub Qubit)** | 2 (qubits 1, 2, 3) | 3 (qubit 1) | 3 (qubits 2, 4) | 4 (qubit 4) |
| **Diameter** | 4 | 3 | 5 | 4 |
| **Native Basis Gates** | `['rz', 'sx', 'x', 'cx']` | `['rz', 'sx', 'x', 'cx']` | `['rz', 'sx', 'x', 'cx']` | `['rz', 'sx', 'x', 'cx']` |
| **Challenge 1Q Error ($p_{1q}$)** | $0.001$ (`x`, `sx`) | $0.001$ (`x`, `sx`) | $0.001$ (`x`, `sx`) | $0.001$ (`x`, `sx`) |
| **Challenge 2Q Error ($p_{2q}$)** | $0.005$ (`cx`) | $0.005$ (`cx`) | $0.005$ (`cx`) | $0.005$ (`cx`) |
| **Challenge Readout Error ($p_{ro}$)** | $0.010$ | $0.010$ | $0.010$ | $0.010$ |

### Coupling Map Graph Representations

```
Processor A (Canonical):   [0] ─── [1] ─── [2] ─── [3] ─── [4]

Processor A (Branching):   [0] ─── [1] ─── [2]
                                    │
                                   [3] ─── [4]

Processor B (Canonical):   [0] ─── [1] ─── [2] ─── [3]
                                            │
                                           [4] ─── [5] ─── [6]
                                            │
                                           [7] ─── [8]
```

---

## 3. Transpilation Benchmark Results

### 3.1 Approved 6-Qubit VQC Compilation

Evaluated on uncompiled circuit: 6 qubits, depth 8, 18 $R_y$ gates, 5 CX gates, 18 parameters.

| Target Architecture | Opt Level | Seed Count | Transpiled Depth (mean $\pm$ std) | 2Q (CX) Count (mean $\pm$ std) | SWAP Count | Total Ops | Routing CX Overhead | Success Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Processor A (Canonical)** | 1, 2, 3 | 5 | N/A | N/A | N/A | N/A | N/A | **$0\%$ (Capacity Limit)** |
| **Processor A (Branching)** | 1, 2, 3 | 5 | N/A | N/A | N/A | N/A | N/A | **$0\%$ (Capacity Limit)** |
| **Processor B (Canonical Tree)** | **Level 1** | 5 | **$15.0 \pm 0.0$** | **$5.0 \pm 0.0$** | **0** | **$65.0 \pm 0.0$** | **0** | **$100\%$** |
| | **Level 2** | 5 | **$15.0 \pm 0.0$** | **$5.0 \pm 0.0$** | **0** | **$65.0 \pm 0.0$** | **0** | **$100\%$** |
| | **Level 3** | 5 | **$15.0 \pm 0.0$** | **$5.0 \pm 0.0$** | **0** | **$65.0 \pm 0.0$** | **0** | **$100\%$** |
| **Processor B (Cyclic Mesh)** | Level 1 | 5 | $15.0 \pm 0.0$ | $5.0 \pm 0.0$ | 0 | $65.0 \pm 0.0$ | 0 | $100\%$ |
| | Level 2 | 5 | $15.0 \pm 0.0$ | $5.0 \pm 0.0$ | 0 | $65.0 \pm 0.0$ | 0 | $100\%$ |
| | Level 3 | 5 | $15.0 \pm 0.0$ | $5.0 \pm 0.0$ | 0 | $65.0 \pm 0.0$ | 0 | $100\%$ |

### 3.2 5-Qubit Reference VQC Compilation (Capacity Benchmark)

Evaluated on 5-qubit subset circuit: 5 qubits, 15 $R_y$ gates, 4 CX gates, 15 parameters.

| Target Architecture | Opt Level | Transpiled Depth | CX Count | Total Ops | Routing CX Overhead | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Processor A (Canonical Line)** | 1, 2, 3 | **16** | **4** | **65** | **0** | Exact 1:1 hardware match |
| **Processor A (Branching Tree)** | 1, 2, 3 | **23** | **7** | **68** | **+3** | Additional CX routing required |

---

## 4. Architectural Analysis & Technical Insights

### 4.1 Native Basis Gate Decomposition
On superconducting hardware, arbitrary single-qubit rotations $R_y(\theta)$ are synthesized into native Z-rotations and square-root-of-X pulses:
$$R_y(\theta) = R_z\left(\frac{\pi}{2}\right) \cdot \sqrt{X} \cdot R_z(\pi - \theta) \cdot \sqrt{X} \cdot R_z\left(\frac{\pi}{2}\right)$$
This synthesis replaces each $R_y$ gate with 2 `sx` pulses and up to 3 virtual `rz` frame shifts.
For the 6-qubit approved VQC (containing $6 + 12 = 18$ $R_y$ gates and 5 CX gates):
- $18 \times 2 = 36$ `sx` pulses (or $24$ after adjacent rotation merging in optimization pass).
- $36$ `rz` virtual gates (executed in zero hardware duration via microwave phase shifts).
- Exactly $5$ physical `cx` gates.
- Total gate count: $65$ operations.

### 4.2 Layout Mapping Determinism
On Processor B Canonical, SABRE layout maps the 6 logical qubits along a contiguous chain in the coupling map:
- Logical $0 \rightarrow$ Physical $0$
- Logical $1 \rightarrow$ Physical $1$
- Logical $2 \rightarrow$ Physical $2$
- Logical $3 \rightarrow$ Physical $4$
- Logical $4 \rightarrow$ Physical $5$
- Logical $5 \rightarrow$ Physical $6$
Physical coupling edges used: $(0,1)$, $(1,2)$, $(2,4)$, $(4,5)$, $(5,6)$.
Because this linear subgraph exists directly on the 9-qubit chip, **zero SWAP gates** are inserted by the compiler.
This invariance holds across all random seeds (`std = 0.0`), confirming determinism.

---

## 5. Artifact Verification & Reproducibility Statement

The transpilation suite is reproducible via:
```powershell
python -m src.transpilation_experiments
```
Outputs are serialized in:
- `results/transpilation_comparison.json`
- `results/processor_ab_evidence_audit.json`

> **Auditor Disclaimer:** Transpilation represents compiler synthesis and topological graph routing. It does **not** constitute execution on physical cryogenic quantum hardware.
