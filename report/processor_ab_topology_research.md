# NEXUS-OPS — Processor A/B Topology Research Report
## Quantum Hardware Architecture Research & Comparative Analysis

**Project:** NEXUS-OPS | PS-Q1 Biomedical Signal Classifier  
**Event / Competition:** IBM Quantum Qiskit Fall Fest 2026 (Phase 1)  
**Role:** Quantum Hardware Architecture Research Engineer  
**Date:** 13 October 2026  
**Status:** COMPLETE — VERIFIED WITH OFFICIAL CHALLENGE DOCUMENTS & QISKIT 2.5.2 BENCHMARKS  
**Deliverable Files:**
- [`processors/processor_A.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_A.json)
- [`processors/processor_B.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_B.json)
- [`processors/processor_a.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_a.py)
- [`processors/processor_b.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/processors/processor_b.py)
- [`results/processor_ab_transpilation.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/processor_ab_transpilation.json)
- [`tests/test_processor_ab.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/tests/test_processor_ab.py)

---

## 1. Executive Summary & Context

Under the rules established by the organizers of the **IBM Quantum Qiskit Fall Fest 2026**, participants are required to research, define, and simulate the architectural impact of two target quantum computing processors: **Processor A** (baseline architecture) and **Processor B** (primary contemporary execution architecture).

The hackathon organizers clarified that:
1. There is no separate pre-compiled processor JSON file download distributed by the organizers; teams must construct, document, and test their own processor models from the official specifications.
2. The challenge is geometry-aware: algorithm design is inextricably linked to physical hardware constraints (coupling graph, native basis gates, routing overhead, and noise exposure).
3. The general challenge description PDF in the official Google Drive repository governs all problem statements.

Following direct retrieval and forensic examination of the official materials in the hackathon Google Drive folder (`https://drive.google.com/drive/folders/1caxlXXeqjOkLmXGlimy_Etw0uPHSwyga`), this report provides the definitive architectural characterization of Processor A and Processor B, maps our approved 6-qubit Variational Quantum Classifier (VQC) onto both topologies, and reports exact transpilation and simulation results.

---

## 2. Official Challenge Requirements & Source Material Audit

### 2.1 Retrieved Primary Documents
The following official challenge documents were retrieved directly from the organizers' shared drive repository and archived locally under `docs/challenge_materials/`:

| Document Name | File ID / Path | Date | Role / Status in Challenge |
| :--- | :--- | :---: | :--- |
| **Phase 1 — Giant Challenge Kit** (`Updated_Challenge_Kit.pdf`) | `1i0Tme-5EDQxrfSarNMsYWFlOrrYZdNZp` | 12 Oct 2026 | **Authoritative Single Source of Truth**. Consolidates all 20 problem statements, processor policies, and rules. |
| **Processor A/B Benchmark Configuration** (`processor_ab_benchmark.pdf`) | `1rm0QXzjWc2aOLm0jm29XgmvoQJG9O1-5` | 11 Oct 2026 | **Organizer Consolidation & Approval Draft**. Details earlier drafting discrepancies and alternative topologies. |
| **Starter Notebook / Participant Guide** (`Updated_Challenge_Guide_Phase_1.pdf`) | `1ToQV3LJtqzrOYjhOixELIo_xmJBNbM1v` | 11 Oct 2026 | Illustrative starter code, routing examples, and recommended repository layout. |
| **Phase 1 Master Guide** (`QFF_Phase_1_Master_Guide.pdf`) | `11dhyb4eSA0giemxWaCUd6nYlYa5CgIUv` | 12 Oct 2026 | General event operational guidelines and schedule. |
| **Hackathon Guidelines** (`QFF_IBM_Hackathon_Guideline.pdf`) | `1ZS2Sjf9_st50RLEDuJqw4FD-sn7JfjNw` | 8 Oct 2026 | Unstop registration and team formation rules. |

### 2.2 Extraction of Exact Processor A/B Requirements

From Section 3 (*"Participant-Facing Processor Policy"*) and Section 4 (*"Reproducibility & Benchmark Protocol"*) of `Updated_Challenge_Kit.pdf`:

1. **Processor A — 5-qubit Baseline:**
   - **Physical Qubits:** 5
   - **Topology:** Nearest-neighbor linear chain. Coupling map: `0–1–2–3–4` (bidirectional CX connectivity).
   - **Role:** Historical/baseline architecture and compact connectivity case study.
   - **Capacity / Routing Policy for >5 Qubits (Section 3.1 & Section 12 FAQ):**
     > *"For a problem requiring more than 5 logical qubits, do not delete variables merely to force the full problem into A. Treat A as a capacity/routing reference and perform the full-size execution on Processor B where permitted."*
     > *"What if my problem needs more than 5 qubits? Do not remove variables solely to fit Processor A. Use A as a capacity/routing reference and use the 9-qubit B architecture for the full-size benchmark where the PS permits it."*

2. **Processor B — 9-qubit Contemporary Execution Architecture:**
   - **Physical Qubits:** 9 (fixed participant-facing Processor B value for Phase 1).
   - **Topology:** Fixed 9-qubit heavy-hex-inspired sparse graph.
   - **Coupling Map:** `0–1, 1–2, 2–3, 2–4, 4–5, 5–6, 4–7, 7–8` (bidirectional CX connectivity).
   - **Role:** Primary contemporary architecture for executing the defined quantum problem instances.
   - **Application to 6-qubit VQC:**
     > *"Where a problem uses 6–8 logical qubits, B is the default full-size execution target."*

3. **Processor C — 13-qubit Reference (Study Only):**
   - **Physical Qubits:** 13 (12-node ring + central node 12 connected to even nodes).
   - **Role:** Architectural study/comparison only. Participants are **not** required to implement or execute on Processor C.

4. **Common Gate and Noise Policy (Section 3.4):**
   - **Native Basis Gates:** `['rz', 'sx', 'x', 'cx']` (measurements/resets are excluded from gate cost counts).
   - **Synthetic Noise Model:**
     - Single-qubit gate depolarizing error: $p_{1q} = 0.001$ (0.1%) on `['x', 'sx']`
     - Two-qubit gate depolarizing error: $p_{2q} = 0.005$ (0.5%) on `['cx']`
     - Symmetric readout bit-flip error: $p_{ro} = 0.01$ (1.0%) per measured qubit
   - **Measurement Shots:** 4096 shots for reported sampled results.
   - **Transpilation Baseline:** `optimization_level=1`, SABRE-based layout and routing, `seed_transpiler=42`.

---

## 3. Hardware Lineage & Academic Literature Review

To establish credible candidates with academic and industrial grounding, we trace the design lineage of both processors in published literature:

### 3.1 Processor A: 5-Qubit Nearest-Neighbor Chain Lineage
- **Published Hardware Pedigrees:**
  - **IBM Falcon r4 Subgraphs (e.g., `ibmq_manila`, `ibmq_bogota`):** Many 5-qubit quantum utility backends fielded between 2020 and 2022 exhibited pure 1D linear chain coupling graphs (`0 - 1 - 2 - 3 - 4`).
  - **Canary / Yorktown (ibmqx2) & Tenerife (ibmqx4):** Early 5-qubit superconducting chips featured bow-tie or T-shaped graphs (`(0,1), (1,2), (1,3), (3,4)`). This corresponds to the alternative "branching tree" identified in the Oct 11 draft (`Processor_AB_Benchmark_Configuration_FINAL.pdf`).
- **Physical Characteristics in Literature:**
  - Fixed-frequency transmons with all-microwave cross-resonance (CR) gates.
  - Linear connectivity limits crosstalk and frequency crowding but incurs severe routing overhead when non-nearest-neighbor entangling gates are executed (requiring $\mathcal{O}(N)$ SWAP operations).

### 3.2 Processor B: 9-Qubit Heavy-Hex Sparse Graph Lineage
- **Published Hardware Pedigrees:**
  - **IBM Heavy-Hex Lattice (Chamberland et al., *PRX* 2020; Jurcevic et al., *QST* 2021):**
    Superconducting transmon architectures encounter severe frequency collisions when qubit degree $\ge 4$. To circumvent this, IBM developed the heavy-hex lattice (used in Falcon 27Q, Hummingbird 65Q, Eagle 127Q, and Heron 133Q).
  - In a heavy-hex lattice, qubits alternate between:
    - **Vertex qubits** (degree 2 or 3) located at the vertices of hexagonal cells.
    - **Edge / bridge qubits** (degree 2) placed along the edges connecting vertex qubits.
- **Topology Analysis of Processor B:**
  - In the Challenge Kit graph:
    - Node 2 is connected to 1, 3, 4 (degree 3).
    - Node 4 is connected to 2, 5, 7 (degree 3).
    - Node 1 connects 0 and 2 (degree 2).
    - Nodes 0, 3, 6, 8 have degree 1 (peripheral boundary qubits).
  - This graph represents a minimal 9-qubit heavy-hex subtree containing two degree-3 branching hubs (nodes 2 and 4).
  - Crucially, it embeds a continuous 6-node linear path:
    $$0 \longleftrightarrow 1 \longleftrightarrow 2 \longleftrightarrow 4 \longleftrightarrow 5 \longleftrightarrow 6$$
    and an isomorphic branch:
    $$0 \longleftrightarrow 1 \longleftrightarrow 2 \longleftrightarrow 4 \longleftrightarrow 7 \longleftrightarrow 8$$

---

## 4. Comprehensive Candidate Topologies Specification

### Candidate 1: Processor A (Canonical — Consolidated Challenge Kit)
- **Graph Structure:** 1D linear chain ($P_5$).
- **Physical Qubit Count:** 5 ($q_0, \dots, q_4$).
- **Directed Coupling Edges (8):**
  `[[0,1], [1,0], [1,2], [2,1], [2,3], [3,2], [3,4], [4,3]]`
- **Unique Undirected Edges (4):**
  `(0,1), (1,2), (2,3), (3,4)`
- **Degree Distribution:** Two degree-1 endpoints (0, 4); three degree-2 interior nodes (1, 2, 3).
- **Source:** `Updated_Challenge_Kit.pdf`, Section 3.1.
- **Suitability:** Establishes the baseline capacity constraint and illustrates 1D linear routing dynamics.
- **Limitation:** Cannot physically host quantum circuits with $>5$ logical qubits.

### Candidate 2: Processor A (Alternative — Oct 11 Draft Branching Tree)
- **Graph Structure:** T-shaped / bow-tie branching tree ($T_5$).
- **Physical Qubit Count:** 5 ($q_0, \dots, q_4$).
- **Directed Coupling Edges (8):**
  `[[0,1], [1,0], [1,2], [2,1], [1,3], [3,1], [3,4], [4,3]]`
- **Unique Undirected Edges (4):**
  `(0,1), (1,2), (1,3), (3,4)`
- **Degree Distribution:** Node 1 has degree 3; nodes 0, 2, 4 have degree 1; node 3 has degree 2.
- **Source:** `Processor_AB_Benchmark_Configuration_FINAL.pdf`, Section 3.
- **Suitability:** Reflects early IBM Tenerife / Ourense topologies. Demonstrates how branching topology forces SWAP insertion even on 5-qubit linear entangling circuits.

### Candidate 3: Processor B (Canonical — Consolidated Challenge Kit)
- **Graph Structure:** 9-node heavy-hex-inspired sparse tree ($H_9$).
- **Physical Qubit Count:** 9 ($q_0, \dots, q_8$).
- **Directed Coupling Edges (16):**
  `[[0,1], [1,0], [1,2], [2,1], [2,3], [3,2], [2,4], [4,2], [4,5], [5,4], [5,6], [6,5], [4,7], [7,4], [7,8], [8,7]]`
- **Unique Undirected Edges (8):**
  `(0,1), (1,2), (2,3), (2,4), (4,5), (5,6), (4,7), (7,8)`
- **Degree Distribution:**
  - Degree 3: Node 2 (neighbors: 1, 3, 4), Node 4 (neighbors: 2, 5, 7)
  - Degree 2: Node 1 (neighbors: 0, 2), Node 5 (neighbors: 4, 6), Node 7 (neighbors: 4, 8)
  - Degree 1: Nodes 0, 3, 6, 8
- **Source:** `Updated_Challenge_Kit.pdf`, Section 3.2.
- **Suitability:** Serves as the primary execution architecture. Ample qubit capacity (9 qubits) with sparse degree $\le 3$ mimicking modern IBM Eagle/Heron processors.

### Candidate 4: Processor B (Alternative — Oct 11 Draft Cyclic Mesh)
- **Graph Structure:** 9-node planar cyclic mesh with 12 edges ($M_9$).
- **Physical Qubit Count:** 9 ($q_0, \dots, q_8$).
- **Unique Undirected Edges (12):**
  `(0,1), (1,2), (1,6), (2,3), (2,6), (2,5), (3,4), (4,5), (5,6), (6,7), (6,8), (8,0)`
- **Source:** `Processor_AB_Benchmark_Configuration_FINAL.pdf`, Section 4.
- **Suitability:** Demonstrates high-connectivity alternative with closed loops/cycles.

---

## 5. Mapping the Approved 6-Qubit VQC to Both Topologies

### 5.1 The Approved VQC Architecture (Milestones 5E & 5F.2)
The NEXUS-OPS project has frozen and validated the following 6-qubit VQC architecture (`src/vqc_circuit.py`):
- **Logical Qubits:** 6 ($q_0, \dots, q_5$)
- **Feature Map:** $U_\Phi(\mathbf{x}) = \bigotimes_{i=0}^5 R_y(x_i)$ (6 $R_y$ gates, depth 1)
- **Variational Ansatz:** RealAmplitudes with $L=1$ repetition, linear entanglement
  $$W(\boldsymbol{\theta}) = \left(\bigotimes_{i=0}^5 R_y(\theta_{6+i})\right) \cdot \left(\prod_{i=0}^4 \text{CX}_{i, i+1}\right) \cdot \left(\bigotimes_{i=0}^5 R_y(\theta_i)\right)$$
- **Observable:** Average Pauli-Z observable $\bar{Z} = \frac{1}{6}\sum_{i=0}^5 Z_i$
- **Uncompiled Circuit Metrics:**
  - Qubits: 6
  - Depth: 8
  - Total gates: 23 (18 $R_y$, 5 $\text{CX}$)
  - Variational parameters: 12 ($\theta \in \mathbb{R}^{12}$)

### 5.2 Transpilation onto Processor A (5 Qubits)
When attempting to transpile the approved 6-qubit VQC onto Processor A (5 physical qubits) using Qiskit 2.5.2:
```python
transpile(qc_6q, coupling_map=cmap_a)
```
Qiskit raises:
```text
CircuitTooWideForTarget: 'Number of qubits (6) in VQC_Biomedical is greater than maximum (5) in the coupling_map'
```
**Architectural Consequence & Organizer Policy:**
This capacity violation directly triggers the organizer policy in `Updated_Challenge_Kit.pdf` (Section 3.1 & 12):
- Teams must **not** arbitrarily reduce problem dimensions (e.g., dropping biological ECG features) simply to compress the circuit into Processor A.
- Processor A stands as an official **capacity/routing reference**, demonstrating the fundamental limitation of NISQ processors with insufficient qubit count.
- Full-size execution proceeds on Processor B.

**Controlled Reference Study (5-Qubit Sub-Circuit):**
To evaluate Processor A's routing behavior fairly, we constructed an identical 5-qubit linear VQC reference circuit ($U_\Phi$ on 5 features, RealAmplitudes with 4 CXs) and compiled it across both Processor A candidates:
- **Processor A1 (Canonical Line `0-1-2-3-4`):**
  - Transpiled Depth: **14**
  - Gate counts: 30 $R_z$, 20 $S_X$, **4 CX** (0 SWAPs, total 54 gates)
  - Result: Perfect alignment with linear entanglement. Zero routing penalty.
- **Processor A2 (Branching Tree `(0,1), (1,2), (1,3), (3,4)`):**
  - Transpiled Depth: **21** (+50.0% increase)
  - Gate counts: 30 $R_z$, 20 $S_X$, **7 CX** (1 SWAP overhead = 3 extra CXs, total 57 gates)
  - Result: Because physical node 1 has degree 3 while nodes 0 and 2 are dead ends, routing the 4-CX linear cascade forces SABRE to insert a SWAP between nodes 1 and 3, substantially inflating depth and two-qubit gate error exposure.

### 5.3 Transpilation onto Processor B (9 Qubits)
When the approved 6-qubit VQC is mapped onto Processor B using the official transpiler baseline (`optimization_level=1`, SABRE layout/routing, `seed_transpiler=42`):

```text
Transpiled B Depth: 15
Gate Counts: 36 rz, 24 sx, 5 cx (Total 65 gates)
CX Count: Exactly 5 CX gates (Logical CX = 5)
SWAP Count: 0 (Zero routing SWAPs!)
Routing Overhead: 0 CX gates
Initial Layout Selected by SABRE:
  Logical Qubit 0 -> Physical Qubit 0
  Logical Qubit 1 -> Physical Qubit 1
  Logical Qubit 2 -> Physical Qubit 2
  Logical Qubit 3 -> Physical Qubit 4
  Logical Qubit 4 -> Physical Qubit 5
  Logical Qubit 5 -> Physical Qubit 6
  Unused Ancillae:  Physical Qubits 3, 7, 8
```

**Key Architectural Insight Regarding Decision D3:**
In Milestone 5E, the team approved **Decision D3** (`entanglement="linear"`). The primary architectural justification recorded in [`results/vqc_architecture_decisions.json`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/results/vqc_architecture_decisions.json) was:
> *"Directly matches linear physical topology on superconducting processors without requiring SWAP overhead."*

Our transpilation benchmark now provides **empirical proof** of this foresight:
1. Processor B's heavy-hex tree topology embeds a 6-node linear sub-chain ($0 - 1 - 2 - 4 - 5 - 6$).
2. SABRE layout identifies this subgraph and places the 6 logical qubits with **zero SWAP gates**.
3. If the team had approved full/all-to-all entanglement ($\binom{6}{2} = 15$ CXs), routing across Processor B would have introduced extensive SWAP networks, ballooning CX counts to $>30$ and circuit depth to $>50$.

---

## 6. Transpilation & Resource Comparison Table

All values in the table below are **actual empirical measurements** obtained from Qiskit 2.5.2 under identical compiler settings (`basis_gates=['rz', 'sx', 'x', 'cx']`, `optimization_level=1`, `seed_transpiler=42`):

| Architecture / Candidate | Target Circuit | Physical Qubits | Logical Qubits | Transpiled Depth | Total Ops | 1Q Ops (`rz` + `sx`) | 2Q Ops (`cx`) | SWAP Count | Routing CX Overhead | Transpilation Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Uncompiled Ideal** | Approved VQC | N/A | 6 | 8 | 23 | 18 (`ry`) | 5 | 0 | 0 | Ideal Spec |
| **Processor A (Canonical Line)** | Approved VQC | 5 | 6 | — | — | — | — | — | — | **FAILED** (`CircuitTooWide`) |
| **Processor A (Branching Tree)** | Approved VQC | 5 | 6 | — | — | — | — | — | — | **FAILED** (`CircuitTooWide`) |
| **Processor A (Canonical Line)** | 5Q Reference | 5 | 5 | **14** | 54 | 50 (30 `rz`, 20 `sx`) | **4** | **0** | **0** | **PASSED** (0 overhead) |
| **Processor A (Branching Tree)** | 5Q Reference | 5 | 5 | **21** | 57 | 50 (30 `rz`, 20 `sx`) | **7** | **1** | **+3** | **PASSED** (+50% depth) |
| **Processor B (Canonical Sparse)** | Approved VQC | 9 | 6 | **15** | 65 | 60 (36 `rz`, 24 `sx`) | **5** | **0** | **0** | **PASSED** (0 overhead) |
| **Processor B (Cyclic Mesh)** | Approved VQC | 9 | 6 | **15** | 65 | 60 (36 `rz`, 24 `sx`) | **5** | **0** | **0** | **PASSED** (0 overhead) |

---

## 7. Noisy Simulation Results on Processor B

Using the official Challenge Kit synthetic noise model:
- Single-qubit depolarizing: $p = 0.001$ on `['x', 'sx']`
- Two-qubit depolarizing: $p = 0.005$ on `['cx']`
- Readout bit-flip: $p = 0.01$ per measured qubit
- Shots: 4096 (resulting in theoretical shot-noise precision $\sigma = 1/\sqrt{4096} = 0.015625$)
- Transpiled 6-qubit circuit with observable $\bar{Z} = \frac{1}{6}\sum_{i=0}^5 Z_i$

**Measured Values (`results/processor_ab_transpilation.json`):**
- **Ideal Statevector Expectation:** $\langle \bar{Z} \rangle_{\text{ideal}} = 0.240036$
- **Noisy Aer Simulation Expectation:** $\langle \bar{Z} \rangle_{\text{noisy}} = 0.234710$
- **Noisy Standard Error:** $\text{SE} = 0.015625$
- **Absolute Noise Deviation:** $|\Delta E| = 0.005327$

**Interpretation:**
Because the 6-qubit VQC transpiles with 0 SWAPs and only 5 CX gates on Processor B, cumulative gate error accumulation is minimal. The noise shift $|\Delta E| \approx 0.0053$ is well within the 1-sigma shot noise window ($\sigma = 0.0156$), demonstrating high noise tolerance on this topology.

---

## 8. Explicit Distinction of Facts vs. Assumptions

| Item | Classification | Verification Detail |
| :--- | :---: | :--- |
| **Processor A = 5 qubits, Line `0–1–2–3–4`** | **VERIFIED SOURCE FACT** | Extracted from `Updated_Challenge_Kit.pdf` Section 3.1. |
| **Processor B = 9 qubits, Sparse Tree `(0,1),...,(7,8)`** | **VERIFIED SOURCE FACT** | Extracted from `Updated_Challenge_Kit.pdf` Section 3.2. |
| **Basis Gates `{rz, sx, x, cx}` & Noise Parameters** | **VERIFIED SOURCE FACT** | Extracted from `Updated_Challenge_Kit.pdf` Section 3.4. |
| **Transpiler Baseline (opt_level=1, seed=42)** | **VERIFIED SOURCE FACT** | Extracted from `Updated_Challenge_Kit.pdf` Section 3.4. |
| **`CircuitTooWideForTarget` on Processor A** | **SIMULATED MEASUREMENT** | Empirically verified in Qiskit 2.5.2 (error raised for 6Q). |
| **Processor B Transpiled Depth 15, 0 SWAPs** | **SIMULATED MEASUREMENT** | Empirically verified via `transpile_for_processor_b`. |
| **Noisy Aer Expectation 0.234710 vs Ideal 0.240036** | **SIMULATED MEASUREMENT** | Empirically measured via `EstimatorV2` with 4096 shots. |
| **Physical Hardware Coherence Times ($T_1, T_2$)** | **UNVERIFIED PROPERTY** | Synthetic noise model does not simulate $T_1/T_2$ relaxation. |
| **Crosstalk / Stray Capacitance Couplings** | **UNVERIFIED PROPERTY** | Synthetic model assumes independent depolarizing channels. |
