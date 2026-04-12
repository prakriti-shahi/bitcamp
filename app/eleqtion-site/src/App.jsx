import React, { useState } from 'react';
import axios from 'axios';
import './index.css';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [phase, setPhase] = useState('SETUP');
  
  const [candidateInput, setCandidateInput] = useState('');
  const [numVoters, setNumVoters] = useState(3);
  const [candidatesList, setCandidatesList] = useState([]);
  
  const [currentVoter, setCurrentVoter] = useState(1);
  const [selectedChoice, setSelectedChoice] = useState('');
  
  const [results, setResults] = useState(null);

  const handleSetupSubmit = async (e) => {
    e.preventDefault();
    if (!candidateInput.trim() || numVoters < 1) return;

    try {
      await axios.post(`${API_BASE}/get-inputs`, { names: candidateInput, person: 'candidate' });
      await axios.post(`${API_BASE}/get-inputs`, { names: numVoters.toString(), person: 'voter' });

      const parsedCandidates = candidateInput.split(',').map(c => c.trim()).filter(Boolean);
      setCandidatesList(parsedCandidates);
      setPhase('VOTING');
    } catch (err) {
      console.error("Setup Error:", err.response?.data || err.message);
      alert("Connection to the Quantum Server failed. Check the console.");
    }
  };

  const handleVoteSubmit = async (e) => {
    e.preventDefault();
    if (selectedChoice === '') return;

    try {
      await axios.post(`${API_BASE}/submit-ballot`, { choice: selectedChoice });

      if (currentVoter < numVoters) {
        setCurrentVoter(prev => prev + 1);
        setSelectedChoice('');
      } else {
        setPhase('CALCULATING');
        runQuantumElection();
      }
    } catch (err) {
      console.error("Ballot Error:", err.response?.data || err.message);
      alert("Failed to cast ballot. Check the console.");
    }
  };

  const runQuantumElection = async () => {
    try {
      const response = await axios.post(`${API_BASE}/run-election`);
      setResults(response.data);
      setPhase('RESULTS');
    } catch (err) {
      console.error("Election Error:", err.response?.data || err.message);
      alert("Quantum circuit evaluation failed.");
      setPhase('SETUP');
    }
  };

  return (
    // Main Background Wrapper
    <div className="min-h-screen w-full bg-[#07030a] text-[#e0d8ea] font-sans flex items-center justify-center relative overflow-hidden">
      
      {/* 1. Static Background Glows (Deepest Layer) */}
      <div className="absolute top-[20%] left-[10%] w-[500px] h-[500px] bg-[#461464] rounded-full mix-blend-screen blur-[120px] opacity-20 pointer-events-none z-0"></div>
      <div className="absolute bottom-[10%] right-[10%] w-[600px] h-[600px] bg-[#280a50] rounded-full mix-blend-screen blur-[150px] opacity-20 pointer-events-none z-0"></div>

      {/* 2. Pulsing Aura (Middle Layer - now z-0 to stay behind the container) */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0">
        <div className="w-full max-w-lg aspect-square bg-[#8a2be2] rounded-full blur-[120px] opacity-30 animate-pulse"></div>
      </div>

      {/* 3. App Container (Top Layer - z-10) */}
      <div className="w-full max-w-lg p-6 z-10">
        
        {/* Glass Panel */}
        <div className="bg-[#140a1e]/80 backdrop-blur-2xl border border-[#8a2be2]/20 rounded-2xl p-10 shadow-[0_8px_32px_rgba(0,0,0,0.8)] shadow-inner shadow-[#8a2be2]/5 transition-all duration-500">
          
          {phase === 'SETUP' && (
            <form onSubmit={handleSetupSubmit}>
              <h1 className="font-light tracking-[0.2em] text-center mb-8 text-white drop-shadow-[0_0_12px_rgba(138,43,226,0.5)] uppercase text-2xl">ELEQTION</h1>
              
              <div className="flex flex-col gap-2 mb-6">
                <label className="text-xs uppercase tracking-widest text-[#8a7a9e]">Candidates (Comma Separated)</label>
                <input 
                  type="text" 
                  placeholder="Alice, Bob, Charlie" 
                  value={candidateInput}
                  onChange={(e) => setCandidateInput(e.target.value)}
                  className="bg-black/30 border border-[#8a2be2]/30 text-[#e0d8ea] px-4 py-3 rounded-lg outline-none transition-all duration-300 focus:border-[#9d4edd] focus:shadow-[0_0_15px_rgba(138,43,226,0.4)] placeholder:text-[#8a7a9e]/50"
                  required
                />
              </div>
              
              <div className="flex flex-col gap-2 mb-8">
                <label className="text-xs uppercase tracking-widest text-[#8a7a9e]">Number of Voters</label>
                <input 
                  type="number" 
                  min="1"
                  value={numVoters}
                  onChange={(e) => setNumVoters(parseInt(e.target.value) || 1)}
                  className="bg-black/30 border border-[#8a2be2]/30 text-[#e0d8ea] px-4 py-3 rounded-lg outline-none transition-all duration-300 focus:border-[#9d4edd] focus:shadow-[0_0_15px_rgba(138,43,226,0.4)]"
                  required
                />
              </div>
              
              <button 
                type="submit"
                className="w-full bg-[#9d4edd] text-white py-3 px-6 rounded-lg tracking-wider border border-[#9d4edd] hover:bg-[#c77dff] hover:shadow-[0_0_20px_rgba(138,43,226,0.5)] transition-all duration-300"
              >
                Initialize States
              </button>
            </form>
          )}

          {phase === 'VOTING' && (
            <form onSubmit={handleVoteSubmit}>
              <h1 className="font-light tracking-[0.2em] text-center mb-8 text-white drop-shadow-[0_0_12px_rgba(138,43,226,0.5)] uppercase text-xl">
                VOTER {currentVoter} <span className="text-[#8a7a9e]">/ {numVoters}</span>
              </h1>
              
              <div className="flex flex-col gap-3 mb-8">
                {candidatesList.map((candidate, idx) => (
                  <label key={idx} className="flex items-center gap-4 p-4 border border-[#8a2be2]/20 rounded-lg cursor-pointer transition-colors duration-300 hover:bg-[#8a2be2]/10">
                    <input 
                      type="radio" 
                      name="candidate" 
                      value={idx}
                      checked={selectedChoice === String(idx)}
                      onChange={(e) => setSelectedChoice(e.target.value)}
                      className="scale-125 accent-[#9d4edd] cursor-pointer"
                    />
                    <span className="tracking-wide">{candidate}</span>
                  </label>
                ))}
                
                <label className="flex items-center gap-4 p-4 border border-[#ff0a54]/30 rounded-lg cursor-pointer transition-colors duration-300 hover:bg-[#ff0a54]/10 mt-2">
                  <input 
                    type="radio" 
                    name="candidate" 
                    value="cheat"
                    checked={selectedChoice === 'cheat'}
                    onChange={(e) => setSelectedChoice(e.target.value)}
                    className="scale-125 accent-[#ff0a54] cursor-pointer"
                  />
                  <span className="text-[#ff0a54] tracking-wide">Inject Malicious State (Cheat)</span>
                </label>
              </div>
              
              <button 
                type="submit"
                className="w-full bg-transparent text-[#9d4edd] py-3 px-6 rounded-lg tracking-wider border border-[#9d4edd] hover:bg-[#9d4edd] hover:text-white hover:shadow-[0_0_20px_rgba(138,43,226,0.4)] transition-all duration-300"
              >
                Cast Ballot
              </button>
            </form>
          )}

          {phase === 'CALCULATING' && (
            <div className="py-8">
              <h1 className="font-light tracking-[0.2em] text-center mb-6 text-white drop-shadow-[0_0_12px_rgba(138,43,226,0.5)] uppercase text-2xl">TALLYING</h1>
              <p className="text-center italic text-[#8a7a9e] animate-pulse tracking-wide">
                Collapsing quantum states...<br/>Evaluating GMW circuits via OT...
              </p>
            </div>
          )}

          {phase === 'RESULTS' && results && (
            <div>
              <h1 className="font-light tracking-[0.2em] text-center mb-8 text-white drop-shadow-[0_0_12px_rgba(138,43,226,0.5)] uppercase text-2xl">RESULTS</h1>
              
              <ul className="mb-8 flex flex-col gap-2">
                {Object.entries(results.full_tally || {}).map(([name, votes]) => (
                  <li key={name} className="flex justify-between items-center py-3 border-b border-white/5">
                    <span className="text-lg tracking-wide">{name}</span>
                    <span className="text-xl text-[#c77dff] font-bold">{votes}</span>
                  </li>
                ))}
              </ul>
              
              <div className="text-center text-2xl text-[#c77dff] mt-6 mb-8 drop-shadow-[0_0_15px_rgba(138,43,226,0.6)] font-light tracking-widest uppercase">
                Winner: <span className="font-bold">{results.winner}</span>
              </div>
              
              <button 
                onClick={() => window.location.reload()}
                className="w-full bg-transparent text-[#8a7a9e] py-3 px-6 rounded-lg tracking-wider border border-[#8a7a9e]/30 hover:text-white hover:border-[#8a2be2] hover:bg-[#8a2be2]/20 transition-all duration-300"
              >
                Reset Quantum System
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}