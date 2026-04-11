# Complexity Analysis: `multiparty_qot_votes.py`

---

## Definitions

| Symbol | Meaning |
|--------|---------|
| **n** | Number of voters |
| **m** | Number of parties (candidates) |
| **log n** | `max_bits = ceil(log₂(n + 1))` — bit-width of the vote counter |

---

## Summary

| Metric | Complexity |
|--------|------------|
| **Total classical work (time)** | **O(n · m · log n)** |
| **Total quantum gate depth (BBCS circuit rounds)** | **O(n · m · log n)** |

---

## Cell-by-Cell Breakdown

### Layer 1 — `QuantumEPRChannel` · EPR Bell-pair channel

Each call prepares and measures **k independent Bell-pair circuits** (constant security
parameter, not a function of n or m). The k circuits run in parallel on the sampler:

- Gate sequence per circuit: `H → CNOT → [H] → Measure` — **O(1) gate depth**
- Classical post-processing per call: O(k), absorbed into the constant

> **Per-call cost: O(1) gate depth, O(1) classical work** (k is constant).

---

### Layer 2 — `BBCSOblTransfer.transfer` · One BBCS OT instance

Each call invokes `transmit` once, then performs O(k) classical work
(cut-and-choose, basis partitioning, hashing). k is constant, so:

- Qubits consumed: k (constant)
- Quantum gate depth: **O(1)** — the k Bell circuits are parallel, not sequential
- Classical work: **O(1)**

The recursive retry branch triggers with exponentially small probability and
contributes O(1) amortised calls.

> **Per OT call: O(1) gate depth, O(1) classical work.**

---

### Layer 3 — `GMWEngine` · Secret-shared boolean circuit evaluation

| Gate | OT calls | Classical work | Gate depth contribution |
|------|----------|----------------|------------------------|
| `xor_gate` | 0 | O(1) — local XOR of shares | O(1) |
| `and_gate` | **2** | O(1) | **O(1) sequential OT round** |

Every AND gate is one sequential OT round. XOR gates are free (no OT, no depth).

> **AND gate: 2 OT calls, O(1) depth. XOR gate: 0 OT calls, O(1) depth.**

---

### Layer 4 — `add_vote` / `half_adder` · Ripple-carry accumulator

`add_vote` adds one 1-bit vote wire into a multi-bit accumulator using a chain of
half-adders. After voter *i* has been processed, the accumulator for one candidate
holds `min(i, log n)` bits. For voter *i*, `add_vote` chains `min(i, log n)`
half-adders in **series** (carry-out of bit j feeds into bit j+1).

Each half-adder costs **1 AND gate** (1 XOR is free).

**AND gates per candidate, summed over all n voters:**

$$\sum_{i=1}^{n} \min(i,\, \log n)
  = \underbrace{\sum_{i=1}^{\log n} i}_{O(\log^2 n)}
  + \underbrace{\sum_{i=\log n}^{n} \log n}_{O(n \log n)}
  = O(n \log n)$$

Across all **m** candidates (tallied sequentially):

$$\text{Total AND gates} = O(n \cdot m \cdot \log n)$$

**Critical note on depth:** the carry chain within each `add_vote` is strictly
sequential — each half-adder depends on the carry output of the previous one.
This makes the **circuit depth per voter O(log n)**, not O(1).

> **Per candidate, per voter: O(log n) AND gates in series → O(log n) depth.**

---

### Layer 5 — `MockZKP` · Zero-knowledge proof (simulated)

Each proof generation and verification is O(m) — it iterates once over the ballot
vector of length m. This is dominated by Layer 4 in every regime.

> **O(m) per voter. Dominated. No effect on leading term.**

---

### Layer 6 — `run_secure_verifiable_election` · Top-level protocol

Orchestration loop: for each of the n voters, for each of the m candidates, call
`add_vote`. Everything else (ZKP, share exchange, reveal) is O(n · m) or smaller.

---

## Final Totals

**Total AND gates / OT instances:**

$$O(n \cdot m \cdot \log n)$$

**Total classical work** (each OT call is O(1) after absorbing k):

$$\boxed{O(n \cdot m \cdot \log n)}$$

**Total BBCS quantum gate depth** (AND gates are sequential; each OT round has O(1)
gate depth, but OT rounds themselves cannot be parallelised across the carry chain):

$$\boxed{O(n \cdot m \cdot \log n)}$$
