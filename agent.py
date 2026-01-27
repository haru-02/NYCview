import os
import json
import requests
from pydantic import BaseModel
from typing import Optional

# add the config env variables and absolute paths in this place.
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
OUTPUT_BASE_PATH = "/app/output"

# metadata schema defined as per the assignment requriements.
class ImageRecord(BaseModel):
    poi_name: str
    image_url: str
    author: str
    unsplash_id: str
    score: float
    description: Optional[str]

def calculate_unsplash_score(photo, poi_name):
    """
    this funciton ranks the images we get.
    it will prioritize the images where the description will have the POI name.
    longer descriptions will also have more context.
    Likes can also be used as a proxy for relevancy, thereby adding further context.
    """

    score = 0
    desc = (photo.get('description') or "").lower()
    alt_desc = (photo.get('alt_description') or "").lower()
    poi_lower = poi_name.lower()
    
    # Subject Relevance (Strongest Weight)
    if poi_lower in desc or poi_lower in alt_desc:
        score += 60

    # We use likes as a proxy for the 'classic' view people expect.
    likes = photo.get('likes', 0)
    if likes > 500:
        score += 30
    elif likes > 100:
        score += 15

    # Photographers who provide longer descriptions usually 
    # provide more context for landmarks.
    if len(desc) > 30:
        score += 10

    return score

def fetch_and_save():
    if not UNSPLASH_ACCESS_KEY:
        print("Error: UNSPLASH_ACCESS_KEY not found in environment!")
        return

    # Load your point of interest mission list
    try:
        with open('locations.json', 'r') as f:
            locations = json.load(f)
    except FileNotFoundError:
        print("Error: locations.json not found.")
        return

    for loc in locations:
        print(f"\n Scouting: {loc['name']}...")
        
        # search for 10 candidates to find the best "Iconic" shot
        search_url = "https://api.unsplash.com/search/photos"
        params = {
            "query": f"{loc['name']} New York City landmark",
            "per_page": 10,
            "orientation": "landscape",
            "client_id": UNSPLASH_ACCESS_KEY
        }

        response = requests.get(search_url, params=params)
        
        if response.status_code != 200:
            print(f" API Error: {response.status_code}")
            continue
            
        results = response.json().get('results', [])
        if not results:
            print(f" No images found for {loc['name']}")
            continue
            
        # Evaluate the 10 candidates
        best_photo = None
        max_score = -1

        for photo in results:
            current_score = calculate_unsplash_score(photo, loc['name'])
            if current_score > max_score:
                max_score = current_score
                best_photo = photo

        # Save the winner
        if best_photo:
            folder_name = loc['name'].lower().replace(" ", "_")
            path = os.path.join(OUTPUT_BASE_PATH, folder_name)
            os.makedirs(path, exist_ok=True)

            # Prepare record
            record = ImageRecord(
                poi_name=loc['name'],
                image_url=best_photo['urls']['regular'],
                author=best_photo['user']['name'],
                unsplash_id=best_photo['id'],
                score=max_score,
                description=best_photo.get('description')
            )

            # Download & Save
            img_data = requests.get(record.image_url).content
            with open(f"{path}/image.jpg", 'wb') as f:
                f.write(img_data)
        
            with open(f"{path}/metadata.json", 'w') as f:
                f.write(record.model_dump_json(indent=2))
        
            print(f" Winner selected! (Score: {max_score}) Shot by {record.author}")

if __name__ == "__main__":
    fetch_and_save()