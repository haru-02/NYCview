from pydantic import BaseModel
from typing import List, Dict, Optional

class Candidate(BaseModel):
    url: str
    source: str
    author: str
    author_profile: str
    license_type: str
    license_url: str
    coords: Optional[tuple] = None
    description: Optional[str] = None
    v_score: float = 0.0
    g_score: float = 0.5
    final_score: float = 0.0

class AgentState(BaseModel):
    poi_name: str
    target_lat: float
    target_lng: float
    candidates: List[Candidate] = []
    tried_sources: List[str] = []
    best_candidate: Optional[Candidate] = None
    status: str = "init" # init, searching, scoring, finalized
    is_complete: bool = False  # Add this line
    best_score: float = 0.0    # Add this so main.py can track it