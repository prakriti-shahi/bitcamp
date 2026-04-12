# Qrypt
We use Quantum Oblivious Transfer to perform secure multi-party computation with quantum-secure key distribution to implement a quantum secure electronic voting machine.
## Requirements
Python dependencies are listed under [requirements.txt.](https://github.com/prakriti-shahi/bitcamp/blob/main/requirements.txt)
## Overview
**Qrypt** implements the [Goldreid-Micali-Wigderson](https://dl.acm.org/doi/10.1145/28395.28420) (GMW) protocol for privacy-preserving multi-party collaborative computation, which is robust against semi-honest adversaries (number of corrupted players t < n/2), for a voting system of *m* candidates and *n* voters. At its core, the GMW protocol allows for participants to secretly share input bits, and employs the *oblivious transfer* (OT) primitive to securely evaluate all gates for a given circuit and its input bits. Key to **Qrypt** is the modification of the OT to utilize *quantum key distribution* (QKD) through the [E91](https://doi.org/10.1103/PhysRevLett.67.661) QKD protocol instead of the usual classical alternative, gaining quantum-secure advantage. 
