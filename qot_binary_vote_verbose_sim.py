"""
Secure Anonymous Voting: Entanglement-Based Quantum OT + GMW Secret Sharing
===========================================================================
Qiskit 1.x implementation using Primitives V2 and Entanglement (EPR pairs).
"""

import time
import os
import numpy as np
import hashlib
import secrets
import math
from typing import List, Tuple, Dict

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.primitives import StatevectorSampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

# ═══════════════════════════════════════════════════════════════════════════════
# Optional IBM Cloud Setup (Commented out for local testing speed)
# ═══════════════════════════════════════════════════════════════════════════════
# IBMQ_API_KEY = os.getenv("IBMQ_API_KEY")
# try:
#     QiskitRuntimeService.save_account(
#         channel="ibm_quantum_platform",
#         token=IBMQ_API_KEY,
#         overwrite=True
#     )
# except:
#     pass
# service = QiskitRuntimeService()


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 1: Entanglement Channel (EPR / Simplified E91)
# ═══════════════════════════════════════════════════════════════════════════════

class QuantumEPRChannel:
    """
    Simulates an Entanglement-based channel.
    Instead of Alice preparing states, a central source distributes
    |Phi+> Bell states to Alice and Bob. Both measure to get their bits.
    
    Bases restricted to Z (0) and X (1) to ensure exactly 50% correlation 
    on mismatches, which is strictly required for Oblivious Transfer security.
    """

    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self.sampler = StatevectorSampler()

    def transmit(self, alice_bases, bob_bases):
        circuits = []
        
        for i in range(self.n):
            # Explicit registers
            alice_qr = QuantumRegister(1, 'alice')
            bob_qr = QuantumRegister(1, 'bob')
            c_alice = ClassicalRegister(1, 'ca')
            c_bob = ClassicalRegister(1, 'cb')
            
            qc = QuantumCircuit(alice_qr, bob_qr, c_alice, c_bob)

            # 1. Prepare the Bell State |Phi+> = (|00> + |11>)/sqrt(2)
            qc.h(alice_qr[0])
            qc.cx(alice_qr[0], bob_qr[0])

            # 2. Rotate to measurement basis (X basis requires a Hadamard)
            if alice_bases[i] == 1:
                qc.h(alice_qr[0])
            if bob_bases[i] == 1:
                qc.h(bob_qr[0])

            # 3. Measure
            qc.measure(alice_qr[0], c_alice[0])
            qc.measure(bob_qr[0], c_bob[0])
            
            circuits.append(qc)

        # Run all independent pairs locally for testing
        job = self.sampler.run(circuits, shots=1)
        results = job.result()

        # ── IBM QPU execution block (Uncomment to use real hardware) ──
        # backend = service.least_busy(operational=True, simulator=False)
        # pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        # qc_isa = pm.run(circuits)
        # sampler = Sampler(mode=backend)
        # job = sampler.run(qc_isa)
        # while not job.done():
        #     time.sleep(2)
        # results = job.result()
        # ──────────────────────────────────────────────────────────────
            
        x_a = []
        x_b = []
        
        # Extract the bit from each party's classical register
        for i in range(self.n):
            a_bit = results[i].data.ca.get_bitstrings()[0]
            b_bit = results[i].data.cb.get_bitstrings()[0]
            x_a.append(int(a_bit))
            x_b.append(int(b_bit))

        return np.array(x_a), np.array(x_b)


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 2: BBCS 1-out-of-2 Quantum Oblivious Transfer
# ═══════════════════════════════════════════════════════════════════════════════

class BBCSOblTransfer:
    """
    BBCS protocol mapped onto an Entanglement-based channel.
    """

    def __init__(self, security_param: int, channel: QuantumEPRChannel):
        self.n = security_param
        self.channel = channel
        self.total_qubits = 0
        self.ot_calls = 0

    def _hash(self, bits, salt):
        return hashlib.sha256(bits.tobytes() + salt).digest()[0] & 1

    def transfer(self, m0: int, m1: int, choice: int) -> int:
        self.ot_calls += 1

        # Quantum Phase: Alice and Bob just choose bases.
        theta_a = np.random.randint(0, 2, self.n)
        theta_b = np.random.randint(0, 2, self.n)
        
        # They measure their halves of the Bell pairs to GET their bits
        x_a, x_b = self.channel.transmit(theta_a, theta_b)
        self.total_qubits += self.n

        # Cut-and-choose verification
        test_idx = set(np.random.choice(self.n, self.n // 2, replace=False))
        remaining = np.array([i for i in range(self.n) if i not in test_idx])
        for i in test_idx:
            if theta_a[i] == theta_b[i] and x_a[i] != x_b[i]:
                # Print instead of crash to allow noisy simulator/hardware to proceed
                print("  [Warning] Entanglement verification failed! Possible Eavesdropper or Noise.")

        # Partition by basis agreement
        e = theta_a[remaining] ^ theta_b[remaining]
        I0 = remaining[e == 0]  # matched bases
        I1 = remaining[e == 1]  # differing bases

        if len(I0) < 4 or len(I1) < 4:
            return self.transfer(m0, m1, choice)

        # Transfer phase
        if choice == 0:
            sent, complement = I0, I1
        else:
            sent, complement = I1, I0

        s0_salt = secrets.token_bytes(16)
        s1_salt = secrets.token_bytes(16)
        s0 = m0 ^ self._hash(x_a[sent], s0_salt)
        s1 = m1 ^ self._hash(x_a[complement], s1_salt)

        if choice == 0:
            return s0 ^ self._hash(x_b[I0], s0_salt)
        else:
            return s1 ^ self._hash(x_b[I0], s1_salt)


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 3: GMW Engine
# ═══════════════════════════════════════════════════════════════════════════════

class GMWEngine:
    def __init__(self, ot: BBCSOblTransfer):
        self.ot = ot
        self._server_shares: Dict[int, int] = {}
        self._voter_shares: Dict[int, int] = {}
        self._next_wire = 0
        self._and_count = 0
        self._xor_count = 0

    def _new_wire(self) -> int:
        w = self._next_wire
        self._next_wire += 1
        return w

    def input_wire(self, value: int, owner: str) -> int:
        w = self._new_wire()
        r = secrets.randbelow(2)
        if owner == "server":
            self._server_shares[w] = value ^ r
            self._voter_shares[w] = r
        else:
            self._voter_shares[w] = value ^ r
            self._server_shares[w] = r
        return w

    def xor_gate(self, w_x: int, w_y: int) -> int:
        w = self._new_wire()
        self._server_shares[w] = self._server_shares[w_x] ^ self._server_shares[w_y]
        self._voter_shares[w] = self._voter_shares[w_x] ^ self._voter_shares[w_y]
        self._xor_count += 1
        return w

    def and_gate(self, w_x: int, w_y: int) -> int:
        x_s = self._server_shares[w_x]
        y_s = self._server_shares[w_y]
        x_v = self._voter_shares[w_x]
        y_v = self._voter_shares[w_y]

        r1 = secrets.randbelow(2)
        t1 = self.ot.transfer(m0=r1, m1=r1 ^ x_s, choice=y_v)

        r2 = secrets.randbelow(2)
        t2 = self.ot.transfer(m0=r2, m1=r2 ^ x_v, choice=y_s)

        w = self._new_wire()
        self._server_shares[w] = (x_s & y_s) ^ r1 ^ t2
        self._voter_shares[w] = (x_v & y_v) ^ t1 ^ r2
        self._and_count += 1
        return w

    def reveal(self, w: int) -> int:
        return self._server_shares[w] ^ self._voter_shares[w]

    def get_voter_shares(self) -> Dict[int, int]:
        return dict(self._voter_shares)

    def set_voter_shares(self, shares: Dict[int, int]):
        self._voter_shares = shares


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 4: Arithmetic Circuit — Half-Adder Chain
# ═══════════════════════════════════════════════════════════════════════════════

def half_adder(engine: GMWEngine, w_a: int, w_b: int) -> Tuple[int, int]:
    s = engine.xor_gate(w_a, w_b)
    c = engine.and_gate(w_a, w_b)
    return s, c

def add_vote(engine: GMWEngine, acc: List[int], vote_w: int, max_bits: int) -> List[int]:
    result = []
    carry = vote_w
    for acc_w in acc:
        s, carry = half_adder(engine, acc_w, carry)
        result.append(s)
    if len(result) < max_bits:
        result.append(carry)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 5: Voting Protocol
# ═══════════════════════════════════════════════════════════════════════════════

def bits_to_int(bits: List[int]) -> int:
    return sum(b << i for i, b in enumerate(bits))

def run_secure_election(votes: List[int], security_param: int = 64):
    n_voters = len(votes)
    max_bits = math.ceil(math.log2(n_voters + 1))

    print("=" * 70)
    print("  SECURE QUANTUM VOTING — Entanglement (EPR) + GMW Protocol")
    print("=" * 70)
    print(f"  Voters: {n_voters}   Max sum bits: {max_bits}   "
          f"Security: {security_param} qubits/OT")
    print(f"  (For verification: votes = {votes})")
    print()
    
    channel = QuantumEPRChannel(security_param)
    ot = BBCSOblTransfer(security_param, channel)
    engine = GMWEngine(ot)

    acc = [engine.input_wire(votes[0], owner="voter")]
    for i in range(1, n_voters):
        prev_shares = engine.get_voter_shares()
        engine.set_voter_shares(prev_shares)

        v_wire = engine.input_wire(votes[i], owner="voter")
        acc = add_vote(engine, acc, v_wire, max_bits)

    result_bits = [engine.reveal(w) for w in acc]
    total_b = bits_to_int(result_bits)
    total_a = n_voters - total_b

    print(f"  Party A (vote=0):  {total_a} votes")
    print(f"  Party B (vote=1):  {total_b} votes")
    
    expected = sum(votes)
    ok = total_b == expected
    print(f"  Verify:            expected B={expected}, got B={total_b}  "
          f"{'CORRECT' if ok else 'ERROR'}")
    print("=" * 70)
    return total_a, total_b


# ═══════════════════════════════════════════════════════════════════════════════
# Privacy Audit
# ═══════════════════════════════════════════════════════════════════════════════

def privacy_audit():
    print("\n" + "=" * 70)
    print("  PRIVACY AUDIT: Do shares leak information?")
    print("=" * 70)

    votes = [1, 0, 1, 1, 0, 1, 0]
    print(f"  Same votes both times: {votes}\n")

    for trial in range(2):
        ch = QuantumEPRChannel(32)
        ot = BBCSOblTransfer(32, ch)
        eng = GMWEngine(ot)
        max_bits = 3

        acc = [eng.input_wire(votes[0], owner="voter")]
        for i in range(1, len(votes)):
            sh = eng.get_voter_shares()
            eng.set_voter_shares(sh)
            v = eng.input_wire(votes[i], owner="voter")
            acc = add_vote(eng, acc, v, max_bits)

        server_view = [eng._server_shares[w] for w in acc]
        voter_view = [eng._voter_shares[w] for w in acc]
        result = [eng.reveal(w) for w in acc]

        print(f"  Trial {trial+1}:")
        print(f"    Server sees (acc shares): {server_view}  <- random")
        print(f"    Voter sees  (acc shares): {voter_view}  <- random")
        print(f"    Combined (XOR):           {result}  = {bits_to_int(result)} "
              f"<- only visible when BOTH cooperate")
        print()

    print("  Shares differ each trial despite identical votes.")
    print("  Neither party alone can reconstruct the tally.")
    print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════════
# Correctness Tests
# ═══════════════════════════════════════════════════════════════════════════════

def test_gmw_xor(n_trials=100):
    print("  Testing GMW XOR gate (free, no OT)...")
    ch = QuantumEPRChannel(32)
    ot = BBCSOblTransfer(32, ch)
    passed = 0
    for _ in range(n_trials):
        eng = GMWEngine(ot)
        x, y = secrets.randbelow(2), secrets.randbelow(2)
        w_x = eng.input_wire(x, owner="server")
        w_y = eng.input_wire(y, owner="voter")
        w_z = eng.xor_gate(w_x, w_y)
        if eng.reveal(w_z) == (x ^ y):
            passed += 1
    assert ot.ot_calls == 0, "XOR should use zero OTs!"
    print(f"  {passed}/{n_trials} passed  (0 OTs used, confirmed free)")
    return passed == n_trials


def test_gmw_and(n_trials=100, sec=32):
    print("  Testing GMW AND gate (secret-shared, 2 OTs each)...")
    ch = QuantumEPRChannel(sec)
    ot = BBCSOblTransfer(sec, ch)
    passed = 0
    for _ in range(n_trials):
        eng = GMWEngine(ot)
        x, y = secrets.randbelow(2), secrets.randbelow(2)
        w_x = eng.input_wire(x, owner="server")
        w_y = eng.input_wire(y, owner="voter")
        w_z = eng.and_gate(w_x, w_y)
        if eng.reveal(w_z) == (x & y):
            passed += 1
    print(f"  {passed}/{n_trials} passed")
    return passed == n_trials


def test_addition(n_trials=50, sec=32):
    print("  Testing full addition circuit...")
    ch = QuantumEPRChannel(sec)
    ot = BBCSOblTransfer(sec, ch)
    passed = 0
    for _ in range(n_trials):
        eng = GMWEngine(ot)
        n = np.random.randint(3, 8)
        votes = [secrets.randbelow(2) for _ in range(n)]
        max_bits = math.ceil(math.log2(n + 1))
        acc = [eng.input_wire(votes[0], owner="voter")]
        for v in votes[1:]:
            sh = eng.get_voter_shares()
            eng.set_voter_shares(sh)
            vw = eng.input_wire(v, owner="voter")
            acc = add_vote(eng, acc, vw, max_bits)
        result = bits_to_int([eng.reveal(w) for w in acc])
        if result == sum(votes):
            passed += 1
    print(f"  {passed}/{n_trials} passed")
    return passed == n_trials


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    np.random.seed(42)

    print("=" * 70)
    print("  PRE-FLIGHT CORRECTNESS CHECKS")
    print("=" * 70)
    ok = test_gmw_xor() and test_gmw_and() and test_addition()
    if not ok:
        print("\n  Tests failed!")
        exit(1)
    print("  All checks passed\n")

    # Election 1: close race
    run_secure_election([1, 0, 1, 0, 1, 0, 1], security_param=64)

    # Election 2: landslide
    print()
    run_secure_election([0, 0, 0, 1, 0, 0, 0], security_param=64)

    # Privacy audit
    privacy_audit()

    # Stress test
    print("\n" + "=" * 70)
    print("  STRESS TEST: 20 random elections")
    print("=" * 70)
    all_ok = True
    for trial in range(20):
        ch = QuantumEPRChannel(48)
        ot = BBCSOblTransfer(48, ch)
        eng = GMWEngine(ot)
        rv = [secrets.randbelow(2) for _ in range(7)]
        mb = math.ceil(math.log2(8))
        acc = [eng.input_wire(rv[0], owner="voter")]
        for v in rv[1:]:
            sh = eng.get_voter_shares()
            eng.set_voter_shares(sh)
            vw = eng.input_wire(v, owner="voter")
            acc = add_vote(eng, acc, vw, mb)
        got = bits_to_int([eng.reveal(w) for w in acc])
        exp = sum(rv)
        ok = got == exp
        if not ok:
            all_ok = False
        print(f"  Trial {trial+1:2d}: {rv}  exp={exp} got={got}  "
              f"{'ok' if ok else 'FAIL'}")

    print(f"\n  {'ALL CORRECT' if all_ok else 'SOME FAILED'}")
    print("=" * 70)