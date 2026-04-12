# EleQt

We use Quantum Oblivious Transfer to perform secure multi-party computation with Eckert-91 quantum-secure key distribution to implement a trustless, quantum secure electronic voting machine.

## Requirements

Python dependencies are listed under [requirements.txt.](https://github.com/prakriti-shahi/bitcamp/blob/main/requirements.txt)

## Overview

**EleQt** implements the [Goldreid-Micali-Wigderson](https://dl.acm.org/doi/10.1145/28395.28420) (GMW) protocol for privacy-preserving multi-party collaborative computation, which is robust against semi-honest adversaries (number of corrupted players $t < n/2$), for a voting system of *m* candidates and *n* voters (henceforth an *(m,n)* voting system). At its core, the GMW protocol allows for participants to secretly share input votes with the *Bennett-Brassard-Crépeau-Skubiszewska* (BCCS) '2-to-1' communication protocol, ensures that the votes are valid (no double voting) with a simulated [Zero-Knowledge Proof](https://arxiv.org/html/2502.07063v1) (ZKP), and employs the *oblivious transfer* (OT) primitive to securely evaluate all gates for a given vote adder circuit. Key to **EleQt** is the modification of the OT to utilize *quantum key distribution* (QKD) through the [E91](https://doi.org/10.1103/PhysRevLett.67.661) QKD protocol instead of the usual classical alternative, attaining quantum-secure advantage.

## Results

Our team successfully verified a *(m,n)* voting system with simulated QKD in [eleqt_multiparty.ipynb](https://github.com/prakriti-shahi/bitcamp/blob/main/eleqt_multiparty.ipynb), demonstrating a trustless, quantum-secure multi-candidate voting system.
Our team successfully benchmarked **EleQt** on an *IBM-Eagle* 127 qubit processor (Kingston) in [eleqt_binary_hardware.ipynb](https://github.com/prakriti-shahi/bitcamp/blob/main/eleqt_binary_hardware.ipynb), demonstrating **EleQt's** capabilities on a toy model with 3 voters upon real quantum hardware in approximately 6 minutes. We note that our execution time was limited to the ten minutes allotted to free *IBM Quantum* accounts.

Additionally, our team calculated the complexity of **EleQt's** main loop to be $\mathbf{O(m\cdot n \cdot \log n)}$ in [complexity_analysis.md](https://github.com/prakriti-shahi/bitcamp/blob/main/complexity_analysis.md), for an *(m,n)* voting system.

Thus one may infer that the verification of a voting system with thousands of voters could be finished in less than a day on current noisy intermediate scale quantum (NISQ) computers. Further research could be aimed at lowering the computational complexity of the adder circuit by transpiling and optimizing the ripple adder circuit for the specific hardware.

# Running the Webpage

Make sure the github repo is cloned if you haven't already done so. Ensure you start in the root (bitcamp) directory. `npm` is required so make sure your system has this installed. For this, make sure that ***Node.js** is installed.


First, start the Python backend with

`uvicorn app.main:app --reload`

Then,

`cd app/eleqtion-site`

and

`npm install`

to install Node.js.

After this, you can launch the webpage with

`npm run dev`

This will start the frontend and the backend should be connected as well. In your terminal, you can click on the `localhost` link to access the webpage.
