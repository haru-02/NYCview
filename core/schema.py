from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple

class Candidate(BaseModel):
    url: str
    source: str
    author: str
    author_profile: str
    license_type: str
    license_url: str
    coords: Optional[Tuple[float, float]] = None
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
    is_complete: bool = False
    best_score: float = 0.0
    status: str = "init"  # init, searching, scoring, finalized
    source_pages: Dict[str, int] = {"unsplash": 0, "pexels": 0, "wikimedia": 0}