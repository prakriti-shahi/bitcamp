from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Union

# Import your backend functions
from multiparty_qot_votes import *

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
CANDIDATES = []  # Must be a list of strings for the backend
NUM_VOTERS = 0
ballots = []
SECURITY_PARAM = 48


# --- Pydantic Models ---

class NameRequest(BaseModel):
    names: str
    person: str # "candidate" or "voter"

class BallotRequest(BaseModel):
    # Union allows both integers (candidate index) and strings ("cheat")
    choice: Union[int, str] 


# --- API Routes ---

@app.post("/get-inputs")
def get_inputs(req: NameRequest):
    global CANDIDATES, NUM_VOTERS, ballots
    
    if req.person == "candidate":
        # Parse the comma-separated string into a List of strings
        CANDIDATES = [name.strip() for name in req.names.split(",") if name.strip()]
        # Reset ballots in case this is a new election
        ballots = [] 
        return {"message": "Candidates received successfully", "candidates": CANDIDATES}
        
    elif req.person == "voter":
        # Usually, you'd just pass the number of voters here
        try:
            NUM_VOTERS = int(req.names)
            return {"message": f"Election set up for {NUM_VOTERS} voters."}
        except ValueError:
            return {"message": "Voters received, but note: expected an integer string."}
            
    return {"message": "Invalid person type. Use 'candidate' or 'voter'."}
    

@app.post("/submit-ballot")
def submit_ballot(req: BallotRequest):
    global ballots, CANDIDATES
    
    if not CANDIDATES:
        raise HTTPException(status_code=400, detail="Candidates have not been set yet.")

    # Initialize a blank ballot array based on the number of candidates
    ballot = [0] * len(CANDIDATES)
    choice_str = str(req.choice).strip().lower()

    if choice_str == 'cheat':
        # Create an invalid ballot that votes for everyone
        ballot = [1] * len(CANDIDATES)
    else:
        try:
            choice_idx = int(req.choice)
            if 0 <= choice_idx < len(CANDIDATES):
                ballot[choice_idx] = 1
            else:
                return {"message": "Invalid candidate number. Ballot rejected."}
        except ValueError:
            return {"message": "Invalid input. Ballot rejected."}

    ballots.append(ballot)
    return {
        "message": "Ballot received successfully", 
        "ballots_cast": len(ballots)
    }


@app.post("/run-election")
def run_election():
    global ballots, CANDIDATES
    
    if not CANDIDATES or not ballots:
        raise HTTPException(status_code=400, detail="Cannot run election. Missing candidates or ballots.")
        
    # Execute the Quantum Backend
    results = run_secure_verifiable_election(ballots, CANDIDATES, security_param=SECURITY_PARAM)
    
    # Check if there were valid votes
    if not results or all(votes == 0 for votes in results.values()):
        return {"message": "Election failed. No valid votes cast or tie.", "winner": "None"}
        
    # max() on a dict with key=results.get returns the string key with the highest value
    winner = max(results, key=results.get)
    
    return {
        "message": f"Candidate {winner} wins!", 
        "winner": winner
    }