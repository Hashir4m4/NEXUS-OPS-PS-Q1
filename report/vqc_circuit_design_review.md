# Milestone 5E-Preparation: Technical Design Review of Core VQC Circuit Architecture

**Project:** Project Q — IBM Quantum Qiskit Fall Fest 2026  
**Challenge:** PS-Q1 — Biomedical Signal Classifier  
**Team:** NEXUS-OPS  
**Stage:** Milestone 5E Preparation  
**Document Purpose:** Mathematical Specification, Qiskit 2.5.2 API Verification, and Pitfall Analysis for the Core Variational Quantum Classifier (VQC) Circuit  
**Governance Notice:** **ALL TEN VQC ARCHITECTURAL DECISIONS REMAIN PROPOSED — NOT YET TEAM-APPROVED**  
**Submission Deadline:** 14 October 2026  
**Date:** October 13, 2026  

---

## 1. Executive Summary & Review Scope

This technical design review provides a complete, gate-by-gate mathematical specification of the proposed Variational Quantum Classifier (VQC) circuit prior to implementation in `src/vqc_circuit.py`. 

The proposed architecture embodies the ten design choices evaluated during Milestone 5A and 5B:
* **Qubits:** 6 qubits ($q_0, \dots, q_5$).
* **Feature Encoding (D2):** First-order $R_y$ angle encoding ($U_\Phi(\mathbf{x}) = \bigotimes_{i=0}^5 R_y(x_i)$).
* **Variational Ansatz (D3, D4, D5):** `RealAmplitudes` with linear nearest-neighbor entanglement and $L=1$ repetition ($W(\boldsymbol{\theta})$).
* **Measurement & Observable (D6):** Ensemble average of six local Pauli-$Z$ observables ($\hat{O} = \frac{1}{6}\sum_{i=0}^5 \hat{Z}_i$).
* **Class Mapping & Polarity (D6):** Positive expectation values indicate Ventricular Ectopic Beats (VEB, class 1); negative expectation values indicate Normal Sinus Beats (Normal, class 0); $p(\text{VEB}) = \frac{E + 1}{2}$.
* **Optimization Objective (D9):** Mean Squared Error (MSE / Brier score).
* **Execution Paradigm (D10):** Ideal statevector simulation for training via Qiskit Primitives V2; 1,024-shot evaluation for final robustness checks.

> [!IMPORTANT]
> **Strict Implementation Guardrails:**
> 1. This document is a technical design review and pre-implementation specification. It does **not** implement the circuit code or training loop.
> 2. All architecture choices retain their status as `PROPOSED_NOT_TEAM_APPROVED`.
> 3. Gate counts and circuit depths specified herein are **theoretical pre-transpilation metrics**. They must not be conflated with physical transpiled metrics on target quantum hardware.
> 4. Quarantined held-out test data (Records 200 and 208) is strictly excluded from all architecture decisions.

---

## 2. Gate-by-Gate Mathematical Circuit Model

```
       [ Stage 1: Feature Map U_Φ(x) ]       [ Stage 2: Variational Ansatz W(θ) ]            [ Stage 3: Measurement ]
       
|0⟩ --- [ Ry(x0) ] ----------------------- [ Ry(θ0) ] ---●--- [ Ry(θ6)  ] ---------------- [ Z0 ] --- (wt: 1/6)
|0⟩ --- [ Ry(x1) ] ----------------------- [ Ry(θ1) ] ---X--- [ Ry(θ7)  ] ---------------- [ Z1 ] --- (wt: 1/6)
|0⟩ --- [ Ry(x2) ] ----------------------- [ Ry(θ2) ] ---●--- [ Ry(θ8)  ] ---------------- [ Z2 ] --- (wt: 1/6)  ==> E(x, θ) = (1/6) Σ ⟨Zi⟩
|0⟩ --- [ Ry(x3) ] ----------------------- [ Ry(θ3) ] ---X--- [ Ry(θ9)  ] ---------------- [ Z3 ] --- (wt: 1/6)      p(VEB) = (E + 1)/2
|0⟩ --- [ Ry(x4) ] ----------------------- [ Ry(θ4) ] ---●--- [ Ry(θ10) ] ---------------- [ Z4 ] --- (wt: 1/6)
|0⟩ --- [ Ry(x5) ] ----------------------- [ Ry(θ5) ] ---X--- [ Ry(θ11) ] ---------------- [ Z5 ] --- (wt: 1/6)
```

### 2.1 State Initialization
The quantum register begins in the 6-qubit computational ground state:
$$|\psi_0\rangle = |0\rangle^{\otimes 6} = |000000\rangle \in \mathbb{R}^{64}$$
This state is purely real and normalized ($\langle \psi_0 | \psi_0 \rangle = 1$).

### 2.2 Stage 1: Feature Encoding Unitary ($U_\Phi(\mathbf{x})$)
For an input vector of six preprocessed features $\mathbf{x} = [x_0, x_1, x_2, x_3, x_4, x_5]^T \in [0, \pi]^6$, the feature map applies a parallel tensor product of single-qubit rotations:
$$U_\Phi(\mathbf{x}) = \bigotimes_{i=0}^5 R_y(x_i)$$
The single-qubit $R_y(\alpha)$ gate has the real unitary matrix representation:
$$R_y(\alpha) = \exp\left(-i \frac{\alpha}{2} Y\right) = \begin{pmatrix} \cos(\alpha/2) & -\sin(\alpha/2) \\ \sin(\alpha/2) & \cos(\alpha/2) \end{pmatrix}$$
Acting on the ground state $|0\rangle_i = \begin{pmatrix} 1 \\ 0 \end{pmatrix}$, each qubit undergoes the transformation:
$$R_y(x_i)|0\rangle_i = \cos\left(\frac{x_i}{2}\right)|0\rangle_i + \sin\left(\frac{x_i}{2}\right)|1\rangle_i$$
Because $x_i \in [0, \pi]$, the half-angle satisfies $x_i / 2 \in [0, \pi/2]$, ensuring that both basis state amplitudes $\cos(x_i/2) \ge 0$ and $\sin(x_i/2) \ge 0$ are non-negative real numbers.

The state after feature encoding is the separable product state:
$$|\psi_{\text{enc}}(\mathbf{x})\rangle = U_\Phi(\mathbf{x}) |0\rangle^{\otimes 6} = \bigotimes_{i=0}^5 \left( \cos\left(\frac{x_i}{2}\right)|0\rangle_i + \sin\left(\frac{x_i}{2}\right)|1\rangle_i \right)$$
* Gate count: Exactly 6 single-qubit $R_y$ gates.
* Two-qubit gates: $0$.
* Entanglement: Exactly zero (separable product state).

### 2.3 Stage 2: Variational Ansatz ($W(\boldsymbol{\theta})$)
The ansatz corresponds to `real_amplitudes(num_qubits=6, reps=1, entanglement='linear')`. It is parameterized by a vector of 12 trainable weights $\boldsymbol{\theta} = (\theta_0, \dots, \theta_{11})^T \in \mathbb{R}^{12}$ and consists of three sub-layers:

#### Sub-Layer 2a: First Rotation Layer ($R^{(1)}$)
Applies 6 trainable single-qubit $R_y$ gates using weights $\theta_0, \dots, \theta_5$:
$$R^{(1)}(\boldsymbol{\theta}_{0:6}) = \bigotimes_{i=0}^5 R_y(\theta_i)$$
Because consecutive single-qubit rotations around the same axis commute and add linearly:
$$R_y(\theta_i) R_y(x_i) = R_y(x_i + \theta_i)$$
Thus, prior to the entanglement layer, each qubit $i$ resides in the rotated state:
$$|\phi_i(x_i, \theta_i)\rangle = \cos\left(\frac{x_i + \theta_i}{2}\right)|0\rangle_i + \sin\left(\frac{x_i + \theta_i}{2}\right)|1\rangle_i$$

#### Sub-Layer 2b: Linear Entanglement Layer ($U_{\text{ent}}$)
Applies a nearest-neighbor cascade of Controlled-NOT ($CX$) gates from qubit 0 to qubit 5:
$$U_{\text{ent}} = CX_{4,5} \cdot CX_{3,4} \cdot CX_{2,3} \cdot CX_{1,2} \cdot CX_{0,1}$$
where $CX_{j, j+1}$ acts as $|c, t\rangle \mapsto |c, c \oplus t\rangle$ with control qubit $j$ and target qubit $j+1$:
$$CX = \begin{pmatrix} 1 & 0 & 0 & 0 \\ 0 & 1 & 0 & 0 \\ 0 & 0 & 0 & 1 \\ 0 & 0 & 1 & 0 \end{pmatrix}$$
This linear cascade couples each qubit to its spatial neighbor, creating bipartite entanglement across pairs $(0,1), (1,2), (2,3), (3,4), (4,5)$ and propagating correlations across the full 6-qubit register.

#### Sub-Layer 2c: Second Rotation Layer ($R^{(2)}$)
Applies the remaining 6 trainable single-qubit $R_y$ gates using weights $\theta_6, \dots, \theta_{11}$:
$$R^{(2)}(\boldsymbol{\theta}_{6:12}) = \bigotimes_{i=0}^5 R_y(\theta_{6+i})$$

#### Composite Ansatz Unitary
$$W(\boldsymbol{\theta}) = R^{(2)}(\boldsymbol{\theta}_{6:12}) \cdot U_{\text{ent}} \cdot R^{(1)}(\boldsymbol{\theta}_{0:6})$$

### 2.4 Complete Composite State
The state prepared by the complete circuit is:
$$|\psi(\mathbf{x}, \boldsymbol{\theta})\rangle = W(\boldsymbol{\theta}) U_\Phi(\mathbf{x}) |0\rangle^{\otimes 6} = \sum_{k=0}^{63} c_k(\mathbf{x}, \boldsymbol{\theta}) |k\rangle$$
* **Real-Valued Subspace Property:** Every gate in the circuit ($R_y$ and $CX$) has strictly real matrix entries. Therefore, all probability amplitudes $c_k(\mathbf{x}, \boldsymbol{\theta}) \in \mathbb{R}$ are strictly real numbers. No complex or imaginary amplitudes exist at any point in the circuit.
* **Theoretical Gate Counts (Untranspiled):**
  * Qubits: 6
  * Single-qubit $R_y$ gates: $6\text{ (encoding)} + 12\text{ (ansatz)} = 18$
  * Two-qubit $CX$ gates: $5$
  * Total gates: $23$
  * Circuit depth: $8$ ($1\text{ enc} + 1\text{ rot1} + 5\text{ CNOTs} + 1\text{ rot2}$)

---

## 3. Physiological Feature Entry Mapping

The six continuous physiological features extracted by [`src/feature_extraction.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/feature_extraction.py) and scaled into $[0, \pi]$ by [`src/vqc_preprocessing.py`](file:///c:/Data/Projects/NEXUS-OPS/NEXUS-OPS/PS-Q1-Biomedical-Classifier/src/vqc_preprocessing.py) enter the quantum register in strict topological order:

| Qubit | Feature Name | Physical Dimension | Scaled Range | Rotation Gate | Initial State When $x_i = 0$ | Superposition State When $x_i = \pi/2$ | Inverted State When $x_i = \pi$ |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| $q_0$ | `pre_rr` | Preceding RR interval | $[0, \pi]$ | $R_y(x_0)$ | $|0\rangle$ | $\frac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$ | $|1\rangle$ |
| $q_1$ | `post_rr` | Succeeding RR interval | $[0, \pi]$ | $R_y(x_1)$ | $|0\rangle$ | $\frac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$ | $|1\rangle$ |
| $q_2$ | `qrs_rms` | QRS complex RMS amplitude | $[0, \pi]$ | $R_y(x_2)$ | $|0\rangle$ | $\frac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$ | $|1\rangle$ |
| $q_3$ | `qrs_duration` | Estimated QRS width | $[0, \pi]$ | $R_y(x_3)$ | $|0\rangle$ | $\frac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$ | $|1\rangle$ |
| $q_4$ | `p2p_amplitude` | Peak-to-peak voltage range | $[0, \pi]$ | $R_y(x_4)$ | $|0\rangle$ | $\frac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$ | $|1\rangle$ |
| $q_5$ | `spectral_ratio` | High-frequency power ratio | $[0, \pi]$ | $R_y(x_5)$ | $|0\rangle$ | $\frac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$ | $|1\rangle$ |

### Topological Entanglement Implications
Because the entanglement topology is a linear nearest-neighbor cascade ($q_0 \to q_1 \to q_2 \to q_3 \to q_4 \to q_5$):
* $q_0$ (`pre_rr`) directly entangles with $q_1$ (`post_rr`). This directly correlates the physiological rhythm features (pre- and post-ectopic pauses).
* $q_1$ (`post_rr`) entangles with $q_2$ (`qrs_rms`), bridging timing features with energy features.
* $q_2$ (`qrs_rms`), $q_3$ (`qrs_duration`), and $q_4$ (`p2p_amplitude`) entangle sequentially, coupling core morphological features of ventricular deformation.
* $q_4$ (`p2p_amplitude`) entangles with $q_5$ (`spectral_ratio`), linking voltage amplitude excursion with spectral power distribution.

---

## 4. Trainable Parameter Dynamics

The 12 trainable variational parameters $\boldsymbol{\theta}$ act as decision-boundary transformers on the feature-encoded quantum state:

```
                      +-------------------------------------------------+
x_i (Feature) ------->| R_y(x_i + θ_i) : Linear Shift of Feature Angles |
                      +-------------------------------------------------+
                                              |
                                              v
                      +-------------------------------------------------+
                      | CX Cascade     : Generates Feature Correlations |
                      +-------------------------------------------------+
                                              |
                                              v
θ_{6+i} (Weight) ---->| R_y(θ_{6+i})   : Rotates Entangled State        |
                      +-------------------------------------------------+
                                              |
                                              v
                      +-------------------------------------------------+
                      | ⟨Z_i⟩          : Local Expectation Value        |
                      +-------------------------------------------------+
```

1. **Pre-Entanglement Parameters ($\theta_0, \dots, \theta_5$):**
   * Modulate the effective angle of each physiological feature before CNOT gates act.
   * If $\theta_i = 0$, the feature enters the CNOT cascade unmodified.
   * If $\theta_i \ne 0$, it acts as an adaptive bias or offset specific to feature $i$.
2. **Post-Entanglement Parameters ($\theta_6, \dots, \theta_{11}$):**
   * Act on the entangled quantum state after non-local correlations have been synthesized.
   * Rotate the entangled statevector to align the desired class signature with the measurement eigenbasis.
3. **Smooth Differentiability:**
   Every amplitude $c_k(\mathbf{x}, \boldsymbol{\theta})$ is an analytic product of trigonometric terms $\cos$ and $\sin$. Consequently, the quantum expectation value is infinitely differentiable with respect to $\boldsymbol{\theta}$, guaranteeing smooth loss landscapes without discontinuities.

---

## 5. Local Pauli-Z Measurements & Ensemble Averaging

### 5.1 Local Z Observables
For each qubit $i \in \{0, \dots, 5\}$, the local Pauli-$Z$ observable is:
$$\hat{Z}_i = I^{\otimes (5-i)} \otimes Z \otimes I^{\otimes i}$$
Recall that Pauli-$Z$ has eigenvalues $+1$ (eigenstate $|0\rangle$) and $-1$ (eigenstate $|1\rangle$):
$$Z = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}, \quad Z|0\rangle = +|0\rangle, \quad Z|1\rangle = -|1\rangle$$
For any state $|\psi\rangle$, the expectation value on qubit $i$ measures the difference between the marginal probability of observing $|0\rangle$ and $|1\rangle$ on that qubit:
$$\langle \hat{Z}_i \rangle = \langle \psi | \hat{Z}_i | \psi \rangle = P(q_i = 0) - P(q_i = 1) \in [-1, +1]$$

### 5.2 Ensemble Average Observable ($\hat{O}$)
Rather than measuring a single qubit (which would ignore information on the remaining five qubits) or measuring a global parity operator $\hat{Z}^{\otimes 6}$ (which suffers from severe barren plateau gradients), the architecture measures the **ensemble average of all six local observables**:
$$\hat{O} = \frac{1}{6} \sum_{i=0}^5 \hat{Z}_i$$
The total expectation value is the linear average of the six individual expectation values:
$$E(\mathbf{x}, \boldsymbol{\theta}) = \langle \psi(\mathbf{x}, \boldsymbol{\theta}) | \hat{O} | \psi(\mathbf{x}, \boldsymbol{\theta}) \rangle = \frac{1}{6} \sum_{i=0}^5 \langle \hat{Z}_i \rangle_{\mathbf{x}, \boldsymbol{\theta}} \in [-1, +1]$$

* **All Qubits in $|0\rangle$ ($|000000\rangle$):** $\langle \hat{Z}_i \rangle = +1 \ \forall i \implies E = +1.0$.
* **All Qubits in $|1\rangle$ ($|111111\rangle$):** $\langle \hat{Z}_i \rangle = -1 \ \forall i \implies E = -1.0$.
* **Balanced / Superposition State:** $\langle \hat{Z}_i \rangle = 0 \implies E = 0.0$.

---

## 6. Derivation: Expectation Value to VEB Probability

### 6.1 Polarity Convention (Decision D6)
Under architecture decision D6:
* **Positive Expectation ($E > 0$):** Indicates the positive class, **Ventricular Ectopic Beat (VEB, label 1)**.
* **Negative Expectation ($E < 0$):** Indicates the negative class, **Normal Sinus Beat (Normal, label 0)**.
* **Zero Expectation ($E = 0$):** Represents maximum uncertainty / decision threshold.

### 6.2 Mathematical Mapping to $[0, 1]$
Because $E(\mathbf{x}, \boldsymbol{\theta})$ is naturally bounded in $[-1, +1]$, the linear affine mapping to the probability domain $[0, 1]$ is:
$$p(\text{VEB} \mid \mathbf{x}, \boldsymbol{\theta}) = \frac{E(\mathbf{x}, \boldsymbol{\theta}) + 1}{2}$$

#### Verification of Boundary Values:
1. When $E = +1.0$:
   $$p = \frac{+1.0 + 1}{2} = 1.0 \quad (100\% \text{ probability of VEB})$$
2. When $E = -1.0$:
   $$p = \frac{-1.0 + 1}{2} = 0.0 \quad (0\% \text{ probability of VEB, i.e. } 100\% \text{ Normal})$$
3. When $E = 0.0$:
   $$p = \frac{0.0 + 1}{2} = 0.5 \quad (\text{Equal probability, classification boundary})$$

#### Probability of Normal Sinus Beat:
$$p(\text{Normal} \mid \mathbf{x}, \boldsymbol{\theta}) = 1 - p(\text{VEB}) = 1 - \frac{E + 1}{2} = \frac{1 - E(\mathbf{x}, \boldsymbol{\theta})}{2}$$

#### Reversible Transformation:
The expectation value can be recovered from predicted probability via:
$$E = 2 p(\text{VEB}) - 1$$

#### Decision Boundary:
$$\hat{y} = \begin{cases} 1 \ (\text{VEB}), & \text{if } p(\text{VEB}) \ge 0.5 \iff E(\mathbf{x}, \boldsymbol{\theta}) \ge 0 \\ 0 \ (\text{Normal}), & \text{if } p(\text{VEB}) < 0.5 \iff E(\mathbf{x}, \boldsymbol{\theta}) < 0 \end{cases}$$

---

## 7. Mathematical Formulation of the Optimization Loss

### 7.1 Proposed Loss Function: Mean Squared Error (Brier Score) — Decision D9
For a batch of $N$ training observations $\{(\mathbf{x}_k, y_k)\}_{k=1}^N$ with binary labels $y_k \in \{0, 1\}$ and predicted probabilities $p_k = \frac{E_k + 1}{2}$:
$$\mathcal{L}_{\text{MSE}}(\boldsymbol{\theta}) = \frac{1}{N} \sum_{k=1}^N \left( p_k(\mathbf{x}_k, \boldsymbol{\theta}) - y_k \right)^2$$

### 7.2 Equivalence in Expectation Space
If we map binary labels $y_k \in \{0, 1\}$ to the expectation domain targets $t_k \in \{-1, +1\}$ via $t_k = 2 y_k - 1$:
$$t_k = \begin{cases} +1, & \text{if } y_k = 1 \ (\text{VEB}) \\ -1, & \text{if } y_k = 0 \ (\text{Normal}) \end{cases}$$
Then the residual difference is:
$$p_k - y_k = \frac{E_k + 1}{2} - y_k = \frac{E_k - (2y_k - 1)}{2} = \frac{E_k - t_k}{2}$$
Squaring this difference:
$$(p_k - y_k)^2 = \frac{1}{4} (E_k - t_k)^2$$
Thus, the loss can be expressed directly in expectation space:
$$\mathcal{L}_{\text{MSE}}(\boldsymbol{\theta}) = \frac{1}{4N} \sum_{k=1}^N \left( E(\mathbf{x}_k, \boldsymbol{\theta}) - t_k \right)^2$$

### 7.3 Mathematical & Computational Advantages
1. **Strictly Bounded:** $\mathcal{L}_{\text{MSE}} \in [0, 1]$. The worst possible prediction ($E = -1$ for target $t = +1$) yields a maximum squared residual of $(1 - 0)^2 = 1.0$.
2. **No Logarithmic Singularities:** Unlike Binary Cross-Entropy ($-\log(p)$), MSE never encounters numerical overflow ($\log(0)$) or explosive gradients when probabilities approach $0$ or $1$.
3. **Stability for Derivative-Free Optimizers:** COBYLA relies on simplex-like evaluations in parameter space. The smooth, bounded quadratic landscape of MSE prevents unstable step sizes that occur under steep logarithmic cross-entropy walls.

---

## 8. Verified Qiskit 2.5.2 & Aer 0.17.2 API Specification

All proposed classes and methods were empirically tested on the active environment (`Python 3.13.7`, `Qiskit 2.5.2`, `Qiskit Aer 0.17.2`):

| Component | Target Role | Verified Qiskit 2.5.2 API | Deprecation / Version Note |
| :--- | :--- | :--- | :--- |
| **Circuit Construction** | Quantum circuit container | `qiskit.circuit.QuantumCircuit` | Standard stable API |
| **Parameter Management** | Feature and weight vectors | `qiskit.circuit.ParameterVector` | Vectorized indexing supported |
| **Ansatz Construction** | $R_y$ rotations + linear CNOTs | `qiskit.circuit.library.real_amplitudes` (function) | **CRITICAL:** `RealAmplitudes` class is **deprecated in Qiskit 2.1+** (removed in 3.0). Use the `real_amplitudes(...)` functional API. |
| **Observable Definition** | Six local Pauli-$Z$ operators | `qiskit.quantum_info.SparsePauliOp.from_sparse_list` | Avoid string endianness issues |
| **Exact Training Engine** | Statevector expectation evaluation | `qiskit.primitives.StatevectorEstimator` | Qiskit Primitives V2 PUB interface |
| **Shot-Based Engine** | 1,024-shot evaluation | `qiskit_aer.primitives.EstimatorV2` (or `AerSimulator`) | Qiskit Aer 0.17.2 V2 primitive |

### 8.1 Modern Primitive V2 PUB Execution Pattern
In Qiskit 2.5.2, `StatevectorEstimator` executes Primitive Unified Blocs (PUBs):
```python
from qiskit.primitives import StatevectorEstimator

estimator = StatevectorEstimator()
# PUB tuple: (circuit, observable, parameter_values)
# parameter_values shape: (N, 18) for batch of N samples
pub = (circuit, observable, batch_params)
job = estimator.run([pub])
result = job.result()
expectation_values = result[0].data.evs  # Returns np.ndarray of shape (N,)
```

---

## 9. Critical Implementation Pitfalls & Mitigation Strategies

### Pitfall 1: Parameter Name Alphabetical Sorting Hazard (CRITICAL)
* **The Trap:** In Qiskit, `circuit.parameters` is a `ParameterView` that sorts parameters **alphabetically by name**, **NOT** by circuit insertion order.
* **Empirical Demonstration:**
  If a developer names the feature vector `ParameterVector('x', 6)` and the variational vector `ParameterVector('theta', 12)`:
  Because ASCII `'t' < 'x'`, `circuit.parameters` sorts `theta[0]...theta[11]` first (indices 0–11) and `x[0]...x[5]` second (indices 12–17)!
  If the developer feeds an array `np.hstack([batch_x, batch_theta])`, Qiskit will map ECG features into the ansatz parameters and weights into the feature map, silently destroying the model without throwing an error!
* **Mitigation Strategy:**
  1. Name parameter vectors with explicit alphabetical prefixes that match physical order:
     * Feature parameters: `p_enc = ParameterVector('p_enc', 6)`
     * Variational parameters: `p_var = ParameterVector('p_var', 12)`
     *(Because `'p_enc'` alphabetically precedes `'p_var'`, `circuit.parameters` is guaranteed to order them as $0\dots5$ for encoding and $6\dots17$ for ansatz).*
  2. Alternatively, always pass an explicit parameter mapping list or dictionary rather than assuming position-based array indexing.

### Pitfall 2: Observable Pauli String Endianness Hazard
* **The Trap:** Qiskit Pauli string notation is right-to-left (little-endian). The string `'IIIIIZ'` corresponds to Pauli-$Z$ on Qubit 0, while `'ZIIIII'` corresponds to Pauli-$Z$ on Qubit 5.
* **Mitigation Strategy:**
  Do **not** use manual string construction like `from_list(['IIIIIZ', ...])`.
  Use `SparsePauliOp.from_sparse_list([('Z', [i], 1.0/6.0) for i in range(6)], num_qubits=6)`.
  This explicitly maps each term to qubit index `[i]`, eliminating all endianness ambiguity.

### Pitfall 3: Expectation Sign at Zero Initialization vs. ECG Features
* **The Trap:** For the unencoded ground state $|000000\rangle$ (where both $x = 0$ and $\theta = 0$), $Z|0\rangle = +1$, so $E = +1.0 \implies p(\text{VEB}) = 1.0$.
* **Clarification:** Actual ECG features are **NOT** zero; they range across $[0, \pi]$.
  Furthermore, parameters are initialized uniformly: $\theta \sim \mathcal{U}[-0.1, 0.1]$ (Decision D8).
  The initial expectation value for an actual ECG sample depends on its individual six scaled feature angles and the random seed. Do not assume or assert $E = +1.0$ on actual data at initialization.

### Pitfall 4: PUB Array Dimensionality in Primitives V2
* **The Trap:** Passing a 1D array of shape $(18 \times N,)$ or a list of unshaped arrays into `estimator.run()` will trigger a PUB validation error in Qiskit 2.x.
* **Mitigation Strategy:**
  For batch evaluation, format `batch_params` as a contiguous 2D NumPy array of shape $(N, 18)$ and `dtype=np.float64`.

### Pitfall 5: Theoretical vs. Transpiled Gate Count Conflation
* **The Trap:** Claiming that the VQC has "5 CNOTs and depth 8" on quantum hardware.
* **Clarification:** 5 CNOTs and depth 8 describe the **abstract, pre-transpilation** circuit. Real physical processors (e.g. IBM Eagle or Heron) require basis gate translation (e.g. into `cz` or `ecr`, single-qubit `rz` and `sx`) and routing swaps, which substantially increases physical depth.

---

## 10. Independent Circuit Testing Protocol (Without Model Training)

The circuit module (`src/vqc_circuit.py`) must be fully unit-tested without running any training loops or optimizers:

1. **Topological & Structural Invariants:**
   * Assert `circuit.num_qubits == 6`.
   * Assert `circuit.num_parameters == 18` (6 encoding + 12 variational).
   * Assert untranspiled `count_ops()` contains exactly 18 `ry` gates and 5 `cx` gates.
   * Assert untranspiled `depth() == 8`.
2. **Observable Invariants:**
   * Assert `observable.num_qubits == 6`.
   * Assert term count is 6, each with coefficient $1/6$.
   * Evaluate `observable` on statevector $|000000\rangle$: must equal $+1.0 \pm 10^{-12}$.
   * Evaluate `observable` on statevector $|111111\rangle$: must equal $-1.0 \pm 10^{-12}$.
3. **Analytic Expectation Verification on Known State:**
   * Set $\mathbf{x} = [\pi, \pi, \pi, \pi, \pi, \pi]^T$ and $\boldsymbol{\theta} = \mathbf{0}_{12}$.
   * Gate evolution: $R_y(\pi)|0\rangle = |1\rangle$.
   * Entanglement:
     * $q_0 = 1$.
     * $CX(0,1): |1, 1 \oplus 1\rangle = |1, 0\rangle \implies q_1 = 0$.
     * $CX(1,2): |0, 1 \oplus 0\rangle = |0, 1\rangle \implies q_2 = 1$.
     * $CX(2,3): |1, 1 \oplus 1\rangle = |1, 0\rangle \implies q_3 = 0$.
     * $CX(3,4): |0, 1 \oplus 0\rangle = |0, 1\rangle \implies q_4 = 1$.
     * $CX(4,5): |1, 1 \oplus 1\rangle = |1, 0\rangle \implies q_5 = 0$.
   * State before measurement: $|010101\rangle$ (qubits $0, 2, 4$ are $|1\rangle$; qubits $1, 3, 5$ are $|0\rangle$).
   * Individual expectations: $\langle Z_0 \rangle = -1, \langle Z_1 \rangle = +1, \langle Z_2 \rangle = -1, \langle Z_3 \rangle = +1, \langle Z_4 \rangle = -1, \langle Z_5 \rangle = +1$.
   * Theoretical ensemble average:
     $$E = \frac{1}{6} (-1 + 1 - 1 + 1 - 1 + 1) = 0.0$$
   * Assert that `StatevectorEstimator` evaluates this exact analytic case to $0.0 \pm 10^{-12}$.
4. **Vectorized PUB Batching Consistency:**
   * Evaluate a batch of 10 random samples in a single vectorized PUB call.
   * Evaluate the same 10 samples individually in 10 single-sample calls.
   * Assert that `batch_evs[i] == single_evs[i]` to floating-point precision ($10^{-12}$).

---

## 11. Minimal Pre-Implementation Circuit Validation Checklist

Before initiating implementation in `src/vqc_circuit.py`, verify the following requirements:

- [ ] **Qubit Register Count:** Register consists of exactly 6 qubits ($q_0 \dots q_5$).
- [ ] **Parameter Vector Separation:** Parameter vectors are explicitly named (`p_enc` and `p_var`) to guarantee deterministic alphabetical sorting.
- [ ] **Functional Ansatz API:** Uses `real_amplitudes(..., reps=1, entanglement='linear')` instead of deprecated class `RealAmplitudes`.
- [ ] **SparsePauliOp Construction:** Constructed using `from_sparse_list` with coefficients $1/6$ to avoid Pauli string endianness bugs.
- [ ] **Output Expectation Domain:** All expectation values verify strictly within $[-1.0, +1.0]$.
- [ ] **Probability Transformation:** Probability strictly computed as $p = (E + 1) / 2$, mapping to $[0.0, 1.0]$.
- [ ] **Loss Function Implementation:** MSE computed as $\frac{1}{N} \sum (p_k - y_k)^2$ or $\frac{1}{4N} \sum (E_k - t_k)^2$.
- [ ] **Vectorized Batching:** `StatevectorEstimator` accepts 2D arrays $(N, 18)$ and evaluates in a single Primitive call.
- [ ] **Unit Tests:** Standalone unit tests written in `tests/test_vqc_circuit.py` verifying structural, observable, and analytic invariants without optimizer loops.
- [ ] **Transpilation Clarity:** Documentation strictly frames 18 $R_y$ and 5 $CX$ as theoretical pre-transpilation counts.

---

## 12. Single Recommended Next Action for the Technical Lead

> **Present `report/vqc_circuit_design_review.md` and `report/vqc_team_review_summary.md` to the NEXUS-OPS team, formally approve the architecture decisions (D1–D10) in `results/vqc_architecture_decisions.json` by updating their status from `PROPOSED_NOT_TEAM_APPROVED` to `TEAM_APPROVED`, and proceed to Milestone 5E: Implementation of `src/vqc_circuit.py` and `tests/test_vqc_circuit.py`.**
