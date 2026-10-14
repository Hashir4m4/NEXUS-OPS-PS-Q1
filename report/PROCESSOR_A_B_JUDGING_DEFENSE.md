# NEXUS-OPS | PS-Q1 Biomedical Signal Classifier
# Processor A vs. Processor B Architectural Defense Dossier

**Project:** NEXUS-OPS — Project Q
**Challenge:** Problem Statement PS-Q1 — Biomedical Signal Classification
**Competition:** IBM Quantum Qiskit Fall Fest 2026 (SRM University-AP)
**Auditor Roles:** Senior IBM Quantum Researcher, Quantum Hardware Architect, Qiskit Circuit Specialist
**Authoritative Organizer Precedent:** Confirmed via direct inquiry on 13 October 2026:
> **Question:** *"Is documenting Processor A's five-qubit capacity limitation, together with an auxiliary five-qubit routing benchmark, acceptable when the full classifier cannot fit on Processor A?"*
> **Organizer Response:** **`YES.`**

---

## 1. Executive Hardware Defense Strategy

The central hardware challenge of Problem Statement PS-Q1 is evaluating quantum classifier architectures across two distinct physical processor topologies provided by hackathon organizers:
1. **Processor A:** A 5-qubit linear chain with nearest-neighbor coupling.
2. **Processor B:** A 9-qubit sparse tree topology inspired by IBM Quantum heavy-hex lattices.

NEXUS-OPS designed a clinically grounded 6-qubit Variational Quantum Classifier (VQC) where each logical qubit encodes a specific physiological ECG feature. This design creates a fundamental architectural question: **How should the team handle Processor A when the 6-qubit classifier physically exceeds Processor A's 5-qubit capacity?**

### The NEXUS-OPS Architectural Position
1. **Capacity Enforcement Over Clinical Distortion:** We refuse to artificially truncate clinical features (e.g., discarding the clinically vital `spectral_ratio` feature) solely to force the model onto an undersized 5-qubit chip. Feature selection must be dictated by biomedical validity, not hardware convenience.
2. **Mathematically Rigorous Rejection:** In `processors/processor_a.py`, our compilation pipeline formally checks circuit width against physical capacity and raises a structured `ValueError: Circuit width (6) exceeds target capacity (5)`. This is the architecturally correct behavior for an automated compiler encountering an oversized problem graph.
3. **Dedicated Auxiliary 5-Qubit Routing Benchmark:** To fulfill the competition requirement of benchmarking Processor A's compiler without compromising biomedical integrity, we designed a separate 5-qubit reference circuit (`processors/processor_a.py`). We measure its transpilation depth, CX count, and routing overhead, but **we never present auxiliary routing results as biomedical classification metrics**.
4. **Native Embedding on Processor B:** On the 9-qubit target (Processor B), our 6-qubit linear ansatz achieves an **optimal native embedding with transpiled depth 15, exactly 5 CX gates, and 0 SWAP gates**.

---

## 2. Processor Topological Specifications & Coupling Maps

### 2.1 Processor A (5 Physical Qubits — Linear Chain)
- **Node Count:** 5 physical qubits ($Q_0 \dots Q_4$).
- **Edge Count:** 4 bidirectional edges (8 directed pairs).
- **Coupling Map:**
  $$\mathcal{E}_A = \{(0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2), (3, 4), (4, 3)\}$$
- **Maximum Degree:** 2 (internal nodes $Q_1, Q_2, Q_3$).
- **Diameter:** 4 edges ($Q_0 \leftrightarrow Q_4$).
- **Basis Gates:** `['rz', 'sx', 'x', 'cx']`.

```
Processor A Topology Diagram:
(Q0) ────── (Q1) ────── (Q2) ────── (Q3) ────── (Q4)
```

### 2.2 Processor B (9 Physical Qubits — Heavy-Hex Sparse Tree)
- **Node Count:** 9 physical qubits ($Q_0 \dots Q_8$).
- **Edge Count:** 8 bidirectional edges (16 directed pairs).
- **Coupling Map:**
  $$\mathcal{E}_B = \{(0, 1), (1, 2), (2, 3), (2, 4), (4, 5), (5, 6), (4, 7), (7, 8)\}$$ (bidirectional)
- **Branching Hub Nodes:**
  - $Q_2$: Degree 3 (connected to $Q_1, Q_3, Q_4$).
  - $Q_4$: Degree 3 (connected to $Q_2, Q_5, Q_7$).
- **Diameter:** 6 edges ($Q_0 \leftrightarrow Q_6$ or $Q_0 \leftrightarrow Q_8$).
- **Basis Gates:** `['rz', 'sx', 'x', 'cx']`.

```
Processor B Topology Diagram:
(Q0) ── (Q1) ── (Q2) ── (Q3)
                 │
                (Q4) ── (Q5) ── (Q6)
                 │
                (Q7) ── (Q8)
```

---

## 3. Subgraph Isomorphism & Native Embedding on Processor B

### 3.1 Logical Circuit Interaction Graph
The approved NEXUS-OPS VQC utilizes a `RealAmplitudes` ansatz with 1 repetition and linear nearest-neighbor CX entanglement:
- Logical Interaction Graph: Path graph $P_6 = (V_L, E_L)$ where $V_L = \{q_0, q_1, q_2, q_3, q_4, q_5\}$ and:
  $$E_L = \{(q_0, q_1), (q_1, q_2), (q_2, q_3), (q_3, q_4), (q_4, q_5)\}$$

### 3.2 Subgraph Embedding Analysis
To execute $P_6$ on a hardware graph $G_H = (V_H, E_H)$ without inserting SWAP gates, there must exist an injective homomorphism (subgraph isomorphism) $f: V_L \to V_H$ such that:
$$(u, v) \in E_L \implies (f(u), f(v)) \in E_H$$

1. **For Processor A ($G_A$):**
   - $|V_A| = 5$. Since $|V_L| = 6 > |V_A| = 5$, no injection $f: V_L \to V_A$ can exist by the Pigeonhole Principle.
   - **Conclusion:** $P_6$ cannot be embedded into $G_A$ under any mapping, with or without SWAP gates.

2. **For Processor B ($G_B$):**
   - $|V_B| = 9$. We search for a simple path of length 5 (6 vertices) within $G_B$.
   - By traversing $Q_0 \to Q_1 \to Q_2 \to Q_4 \to Q_5 \to Q_6$, every consecutive step corresponds to an existing edge in $\mathcal{E}_B$:
     - $(Q_0, Q_1) \in \mathcal{E}_B$
     - $(Q_1, Q_2) \in \mathcal{E}_B$
     - $(Q_2, Q_4) \in \mathcal{E}_B$
     - $(Q_4, Q_5) \in \mathcal{E}_B$
     - $(Q_5, Q_6) \in \mathcal{E}_B$
   - Thus, the mapping $f(q_j) = [0, 1, 2, 4, 5, 6]_j$ establishes an **exact subgraph isomorphism**.
   - **Result:** Exactly **zero SWAP gates** are required. The compiler preserves the minimal 5 CX gate count and achieves the theoretical minimum depth of 15.

---

## 4. Hardware Compilation Benchmark Comparison

| Compilation Metric | 6Q Biomedical VQC on Processor A | Auxiliary 5Q Reference on Processor A | 6Q Biomedical VQC on Processor B | Source Artifact |
|:---|:---:|:---:|:---:|:---|
| **Input Logical Qubits** | 6 logical qubits | 5 logical qubits | 6 logical qubits | `src/vqc_circuit.py`, `processors/processor_a.py` |
| **Target Physical Capacity** | 5 physical qubits | 5 physical qubits | 9 physical qubits | `processors/processor_A.json`, `processor_B.json` |
| **Compilation Outcome** | **`CAPACITY REJECTED`** | **`SUCCESSFUL`** | **`OPTIMAL NATIVE`** | `processors/processor_a.py`, `results/transpilation_comparison.json` |
| **Rejection Mechanism** | `ValueError: width (6) > capacity (5)` | N/A | N/A | `processors/processor_a.py#L95` |
| **Transpiled Depth (No Meas)** | N/A | **16** | **15** | `results/transpilation_comparison.json` |
| **Transpiled Depth (With Meas)**| N/A | **17** | **16** | `results/transpilation_comparison.json` |
| **Single-Qubit Gates (`rz`, `sx`)**| N/A | 25 (`rz`: 15, `sx`: 10) | 60 (`rz`: 36, `sx`: 24) | `results/transpilation_comparison.json` |
| **Two-Qubit CX Gates** | N/A | **4 CX** | **5 CX** | `results/transpilation_comparison.json` |
| **SWAP Gates Inserted** | N/A | **0 SWAP** | **0 SWAP** | `results/transpilation_comparison.json` |
| **Optimal Physical Layout** | N/A | `[0, 1, 2, 3, 4]` | `[0, 1, 2, 4, 5, 6]` | `src/transpilation_experiments.py` |
| **Execution Role** | Architectural Rejection | Hardware Routing Reference | Primary Biomedical Target | `README.md#L133-L175` |

---

## 5. Noise Modeling, Readout Calibration & Permutation Verification

### 5.1 Noise Model Specification
In `src/noise_experiments.py` and `processors/processor_B.json`, the authoritative challenge synthetic noise channels are configured:
1. **Single-Qubit Gate Depolarizing Error:**
   - Applied to basis gates `['sx', 'x']`: $p_{1Q} = 10^{-3}$ ($0.1\%$).
2. **Two-Qubit Gate Depolarizing Error:**
   - Applied to `cx` gates across active coupling pairs: $p_{2Q} = 0.005$ ($0.5\%$).
3. **Readout Bit-Flip Probability:**
   - Classical measurement bit-flip error matrix:
     $$M = \begin{pmatrix} 1 - p_{\text{ro}} & p_{\text{ro}} \\ p_{\text{ro}} & 1 - p_{\text{ro}} \end{pmatrix}, \quad p_{\text{ro}} = 0.01 \quad (1.0\%)$$
4. **Thermal Relaxation ($T_1, T_2$):**
   - Note: The challenge synthetic noise model focuses on gate depolarizing and readout bit-flip channels; thermal relaxation ($T_1/T_2$) is not configured in `processor_B.json` or `noise_experiments.py`.

### 5.2 Transpiler Permutation Verification
When circuits are transpiled with layout optimization, the physical qubit indices rarely equal logical qubit indices. If measurements are sampled naively, observable $\hat{O} = \frac{1}{6}\sum_{j=0}^5 Z_j$ will misattribute physical measurements to wrong logical qubits.

In `src/noise_experiments.py#L90-L135`, our pipeline explicitly extracts the final permutation mapping:
$$\pi: \{0, \dots, 5\} \to \{0, \dots, 8\}$$
and reconstructs the expectation value via:
$$\langle Z_j \rangle = \sum_{x \in \{0, 1\}^n} (-1)^{x_{\pi(j)}} P(x)$$
This guarantees that noisy measurement-based simulation on Aer matches exact statevector expectation values in the zero-noise limit (`tests/test_hardware_experiments.py::test_transpiler_mapping_and_ideal_measurement_equivalence`).

### 5.3 Finite-Shot Variance Analysis
In `results/shot_based_results.json`, finite-shot sweeps over $S \in [256, 512, 1024, 2048, 4096]$ demonstrate:
$$\text{Var}(\langle\hat{O}\rangle) = \frac{\sigma_O^2}{S} \propto \frac{1}{S}$$
At $S=4096$ shots, the empirical standard error across the 6-qubit ensemble observable is $\sigma \approx 0.0078$, ensuring sharp, reliable classification boundaries.

---

## 6. Ten Key Hardware Defense Points for Judges

1. **Why does the VQC use 6 qubits when Processor A has only 5?**
   *Defense:* In biomedical engineering, input features must represent independent physiological indicators. Our clinical signal analysis identified 6 necessary markers (R-R intervals, QRS morphological features, and spectral energy). Truncating to 5 qubits would discard a critical biomarker purely to suit hardware. Processor B natively accommodates 6 qubits.
2. **Did hackathon organizers approve rejecting Processor A?**
   *Defense:* Yes. On 13 October 2026, organizers explicitly confirmed via WhatsApp that documenting Processor A's 5-qubit capacity limitation alongside an auxiliary 5-qubit routing benchmark is fully acceptable.
3. **Does the auxiliary 5-qubit circuit classify ECG beats?**
   *Defense:* No. We maintain strict scientific transparency: the 5-qubit reference is strictly an architectural routing benchmark. We never conflate routing metrics with clinical accuracy.
4. **Why does Processor B achieve 0 SWAP gates?**
   *Defense:* The linear nearest-neighbor CX cascade ($q_0 \to q_1 \to q_2 \to q_3 \to q_4 \to q_5$) forms a path graph $P_6$. The sub-path $Q_0 \to Q_1 \to Q_2 \to Q_4 \to Q_5 \to Q_6$ in Processor B's heavy-hex tree is an isomorphic sub-graph. The compiler embeds this path with zero routing overhead.
5. **Why is transpiled depth exactly 15?**
   *Defense:* Each linear CX layer requires 1 two-qubit execution layer. In standard basis decomposition, 1 repetition of `RealAmplitudes` with 5 CX gates plus initial and final `Rz-Sx-Rz` Euler single-qubit rotations compiles into exactly 15 sequential time slices.
6. **How was the noise model verified?**
   *Defense:* Unit tests in `tests/test_hardware_experiments.py` verify that single-qubit gates, CX gates, and measurement operators reflect the exact configured noise channels.
7. **Why is noisy accuracy (77%) slightly higher than ideal accuracy (76%)?**
   *Defense:* The test set has several borderline cases near threshold $\tau = 0.5$. Small symmetric readout noise slightly flattens extreme expectations, nudging one ambiguous beat across the decision boundary. Both ideal and noisy models achieve identical **100% sensitivity on VEB beats (50/50)**.
8. **Did you run on a physical IBM QPU?**
   *Defense:* No. We make zero false claims of physical QPU execution. All hardware results represent transpilation analysis and synthetic noise simulations using Qiskit Aer.
9. **Could you run a like-for-like 4-qubit classifier?**
   *Defense:* Yes. Organizers confirmed a 4-qubit synthetic experiment could offer a "bigger edge". We have designed this as an optional supplementary module that trains and compiles on BOTH processors without weakening our primary biomedical benchmark.
10. **What happens in Phase 2?**
   *Defense:* In Phase 2, organizers introduce Processor C and custom Processor D. Our modular `processors/` package architecture is built to ingest new JSON coupling maps and automatically benchmark routing depth and noise resilience in seconds.
