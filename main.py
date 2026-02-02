import os
import json
import requests
from core.schema import AgentState, Candidate 
from core.brain import AgentBrain
from core.tools import ImageToolkit

OUTPUT_BASE_PATH = "/app/output"

def save_winner(c: Candidate, poi_name: str):
    """Save the best image and metadata for a POI."""
    email = os.getenv("EMAIL")
    headers = {"User-Agent": f"NYC-Discovery-Agent/1.0 ({email})"}
    folder_name = poi_name.lower().replace(" ", "_")
    path = os.path.join(OUTPUT_BASE_PATH, folder_name)
    os.makedirs(path, exist_ok=True)

    try:
        response = requests.get(c.url, headers=headers, timeout=15)
        response.raise_for_status()
        with open(f"{path}/image.jpg", 'wb') as f:
            f.write(response.content)
    except Exception as e:
        print(f"[Warning] Failed to download image: {e}")

    with open(f"{path}/metadata.json", 'w') as f:
        f.write(c.model_dump_json(indent=2))
    
    print(f"!!! Goal Met: {c.source} selected for {poi_name} (Score: {c.final_score:.2f})")

def run_agent_loop(poi_data):
    """Autonomous loop for fetching and scoring images for a POI."""
    action_count = 0
    state = AgentState(
        poi_name=poi_data['name'],
        target_lat=poi_data['lat'],
        target_lng=poi_data['lng']
    )

    print(f"\n>>> Agent Starting Task: Find image for {state.poi_name}")

    while not state.is_complete:
        action_count += 1

        # Ask the brain which action/tool to use
        action = AgentBrain.decide_next_action(state, action_count)
        print(f"    [Brain Thought]: I will execute '{action}'")

        new_candidates = []
        # Execute the selected tool
        if action == "search_unsplash":
            new_candidates = ImageToolkit.fetch_unsplash(state.poi_name)
            state.tried_sources.append("unsplash")
        elif action == "search_pexels":
            new_candidates = ImageToolkit.fetch_pexels(state.poi_name)
            state.tried_sources.append("pexels")
        elif action == "search_wikimedia":
            new_candidates = ImageToolkit.fetch_wikimedia(state.poi_name)
            state.tried_sources.append("wikimedia")
        elif action == "finalize" or action_count >= 10:
            # Finalize if brain decides or max iterations reached
            if state.candidates:
                state.best_candidate = max(state.candidates, key=lambda x: x.final_score)
                save_winner(state.best_candidate, state.poi_name)
            else:
                print(f"    [Warning]: No images were found for {state.poi_name}")
            state.is_complete = True
            continue

        # Score each new candidate
        for c in new_candidates:
            ImageToolkit.calculate_scores(c, state.poi_name, state.target_lat, state.target_lng)
            state.candidates.append(c)

        # Update the best score so far
        if state.candidates:
            current_max = max(c.final_score for c in state.candidates)
            state.best_score = current_max
            print(f"    [Observation]: Current best score is {current_max:.2f}")

if __name__ == "__main__":
    try:
        with open('locations.json', 'r') as f:
            locations = json.load(f)
            for loc in locations:
                run_agent_loop(loc)
    except FileNotFoundError:
        print("Error: locations.json not found.")