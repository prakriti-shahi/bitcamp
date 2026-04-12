"""
Secure Anonymous Voting: Two-Server Model with ZKPs + Quantum OT
================================================================
Qiskit 1.x implementation using Primitives V2.

Architecture:
  - Voters are Clients. They generate Zero-Knowledge Proofs (ZKPs) and 
    shard their multi-candidate vote vector.
  - Two non-colluding Servers (Server A & Server B) run the GMW Engine.
  - Server A & B maintain the running tallies using Quantum OT, never 
    learning the individual votes.

Gates:
  XOR — FREE: each server locally XORs their own shares. Zero communication.
  AND — COSTLY: requires 2 BBCS quantum OTs (one per cross-term).
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.primitives import StatevectorSampler
import numpy as np
import hashlib
import secrets
import math
from typing import List, Tuple, Dict


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 1: BB84 Quantum Channel (Modern Qiskit 1.x)
# ═══════════════════════════════════════════════════════════════════════════════

class QuantumBB84Channel:
    """
    Simulates BB84 photon transmission using Qiskit 1.x Primitives V2.
    MEMORY SAFE: Simulates N independent 1-qubit circuits instead of one N-qubit circuit.
    """
    def __init__(self, n_qubits: int):
        self.n = n_qubits
        self.sampler = StatevectorSampler()

    def transmit(self, alice_bits, alice_bases, bob_bases):
        circuits = []
        
        # Build N separate 1-qubit circuits
        for i in range(self.n):
            qr = QuantumRegister(1, 'q')
            cr = ClassicalRegister(1, 'meas')
            qc = QuantumCircuit(qr, cr)

            # Alice: encode bit in chosen basis
            if alice_bits[i]:
                qc.x(0)
            if alice_bases[i]:
                qc.h(0)

            # Bob: rotate to his measurement basis
            if bob_bases[i]:
                qc.h(0)

            # Measure
            qc.measure(qr, cr)
            circuits.append(qc)

        # Run all N circuits in one batch
        job = self.sampler.run(circuits, shots=1)
        results = job.result()
        
        # Extract the single bit from each of the N circuits
        measured_bits = []
        for i in range(self.n):
            bitstring = results[i].data.meas.get_bitstrings()[0]
            measured_bits.append(int(bitstring))

        return np.array(measured_bits)


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 2: BBCS 1-out-of-2 Quantum Oblivious Transfer
# ═══════════════════════════════════════════════════════════════════════════════

class BBCSOblTransfer:
    def __init__(self, security_param: int, channel: QuantumBB84Channel):
        self.n = security_param
        self.channel = channel
        self.total_qubits = 0
        self.ot_calls = 0

    def _hash(self, bits, salt):
        return hashlib.sha256(bits.tobytes() + salt).digest()[0] & 1

    def transfer(self, m0: int, m1: int, choice: int) -> int:
        self.ot_calls += 1
        x_a = np.random.randint(0, 2, self.n)
        theta_a = np.random.randint(0, 2, self.n)
        theta_b = np.random.randint(0, 2, self.n)
        x_b = self.channel.transmit(x_a, theta_a, theta_b)
        self.total_qubits += self.n

        test_idx = set(np.random.choice(self.n, self.n // 2, replace=False))
        remaining = np.array([i for i in range(self.n) if i not in test_idx])
        for i in test_idx:
            if theta_a[i] == theta_b[i] and x_a[i] != x_b[i]:
                raise RuntimeError("BB84 verification failed!")

        e = theta_a[remaining] ^ theta_b[remaining]
        I0 = remaining[e == 0] 
        I1 = remaining[e == 1] 

        if len(I0) < 4 or len(I1) < 4:
            return self.transfer(m0, m1, choice)

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


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 4: Arithmetic Circuit 
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

def bits_to_int(bits: List[int]) -> int:
    return sum(b << i for i, b in enumerate(bits))


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 5: Zero Knowledge Proof Simulator
# ═══════════════════════════════════════════════════════════════════════════════

class MockZKP:
    @staticmethod
    def generate_proof(ballot_vector: List[int]) -> dict:
        range_valid = all(v in [0, 1] for v in ballot_vector)
        sum_valid = sum(ballot_vector) == 1
        
        return {
            "is_valid": range_valid and sum_valid,
            "signature": secrets.token_hex(8)
        }

    @staticmethod
    def verify_proof(proof: dict) -> bool:
        return proof.get("is_valid", False)


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 6: Verifiable Two-Server Tallying Protocol
# ═══════════════════════════════════════════════════════════════════════════════

def run_secure_verifiable_election(ballots: List[List[int]], candidates: List[str], security_param: int = 64):
    n_voters = len(ballots)
    max_bits = math.ceil(math.log2(n_voters + 1))

    print("\n" + "=" * 70)
    print("  TWO-SERVER QUANTUM VOTING WITH ZKP VERIFICATION")
    print("=" * 70)
    print(f"  Voters: {n_voters}   Candidates: {len(candidates)}")
    print("  Privacy Model: Voters shard ballots; Servers tally via Quantum OT.")
    print("-" * 70)

    channel = QuantumBB84Channel(security_param)
    ot = BBCSOblTransfer(security_param, channel)
    engine = GMWEngine(ot)

    accumulators = {}
    for candidate in candidates:
        accumulators[candidate] = [engine.input_wire(0, owner="server")]

    valid_votes_cast = 0

    for i, ballot in enumerate(ballots):
        print(f"  Processing Voter {i+1}...")
        
        proof = MockZKP.generate_proof(ballot)

        if not MockZKP.verify_proof(proof):
            print(f"      [REJECTED] Invalid Zero-Knowledge Proof detected! (Spoiled ballot)")
            continue
            
        print(f"      [ACCEPTED] ZKP Verified. Adding shares to running tallies via Quantum OT.")
        valid_votes_cast += 1

        for j, candidate in enumerate(candidates):
            v_wire = engine.input_wire(ballot[j], owner="voter")
            accumulators[candidate] = add_vote(engine, accumulators[candidate], v_wire, max_bits)

    print("\n  Election Complete. Servers A & B perform final share exchange...")
    
    print("\n" + "=" * 70)
    print("  ELECTION RESULTS")
    print("=" * 70)
    
    results = {}
    for candidate in candidates:
        result_bits = [engine.reveal(w) for w in accumulators[candidate]]
        results[candidate] = bits_to_int(result_bits)
        print(f"  {candidate:10} : {results[candidate]} votes")
        
    if results:
        winner = max(results, key=results.get)
        print("-" * 70)
        print(f"  Winner:            {winner}")
        print(f"  Valid Ballots:     {valid_votes_cast}")
        print(f"  AND gates:         {engine._and_count}")
        print(f"  OT instances:      {ot.ot_calls}")
        print(f"  Total qubits:      {ot.total_qubits}")
    print("=" * 70)
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Main - Interactive Execution
# ═══════════════════════════════════════════════════════════════════════════════

def election():
    np.random.seed(42)

    print("--- Election Setup ---")
    candidate_input = input("Enter the names of eligible candidates (comma separated): ")
    candidates = [name.strip() for name in candidate_input.split(",") if name.strip()]

    if not candidates:
        print("No candidates provided. Exiting.")
        exit()

    try:
        num_voters = int(input("Enter the number of voters: "))
        if num_voters <= 0:
            print("Number of voters must be positive. Exiting.")
            exit()
    except ValueError:
        print("Invalid number of voters. Exiting.")
        exit()

    ballots = []
    print("\n--- Voting Phase ---")
    for i in range(num_voters):
        print(f"\nVoter {i+1}, please cast your vote.")
        for idx, c in enumerate(candidates):
            print(f"  [{idx}] {c}")
        print("  [cheat] Simulate a malicious ballot (votes for everyone)")
        
        choice = input("Enter your choice: ").strip().lower()

        ballot = [0] * len(candidates)
        if choice == 'cheat':
            ballot = [1] * len(candidates)
        else:
            try:
                choice_idx = int(choice)
                if 0 <= choice_idx < len(candidates):
                    ballot[choice_idx] = 1
                else:
                    print("Invalid candidate number. Blank ballot submitted (will be rejected).")
            except ValueError:
                print("Invalid input. Blank ballot submitted (will be rejected).")

        ballots.append(ballot)

    print("\n--- Starting Server Computation ---")
    run_secure_verifiable_election(ballots, candidates, security_param=48)

if __name__ == "__main__":
    election()