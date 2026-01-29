import os
import json
import requests
from pydantic import BaseModel
from typing import Optional
from geopy.distance import geodesic
from PIL import Image
from io import BytesIO
from sentence_transformers import SentenceTransformer, util

# add the config and absolute paths in this place.
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
# im using cpu only to conserve resources. U can remove this if you want to use GPU.
OUTPUT_BASE_PATH = "/app/output"
# EMAIL is imp for sending requests to wikimedia, make sure to add that in docker-compose file
EMAIL = os.getenv("EMAIL")

# metadata schema defined as per the assignment requriements.
# The license_type and scoring system is a lot more descriptive.
class ImageRecord(BaseModel):
    poi_name: str
    image_url: str
    source: str
    author: str
    author_profile: str
    license_type: str
    license_url: str
    vision_score: float
    geo_score: float
    final_score: float
    description: Optional[str]

def calculate_geo_score(target_lat, target_lng, image_lat, image_lng):
    # 30% of the final score is due to location from the site.
    # if the coordinates are too similar, that means the pic is of the view from the location,
    # not a picture of the location itself. so we need to calibrate.
    if image_lat is None or image_lng is None:
        return 0.5
    
    distance = geodesic((target_lat, target_lng), (image_lat, image_lng)).km
    if distance < 0.1:
        return 0.6
    elif 0.1 <= distance <= 1.5:
        return 1.0
    elif 1.5 < distance <= 4.0:
        return 0.4
    else:
        return 0.0

print("Loading AI Vision Model (CLIP)") # ill know if it slows down after this point with this print.
vision_model = SentenceTransformer('clip-ViT-B-32')

def get_vision_score(image_url, poi_name):
    # we are using the vision_model locally, and prompting it to score the pic.
    # the vision score contributes to 70% of the final score.

    try:
        # send requests to get the image bytes first.
        headers = {"User-Agent": f"NYC-Discovery-Agent/1.0 ({EMAIL})"}
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status()

        # process the bytes into an Image object
        img = Image.open(BytesIO(response.content)).convert("RGB")
        
        # AI scoring logic
        text_queries = [f"a photo of {poi_name} in New York City", "a landmark"]
        img_emb = vision_model.encode(img)
        text_emb = vision_model.encode(text_queries)
        
        cos_sim = util.cos_sim(img_emb, text_emb)
        score = float(cos_sim.max())

        # Explicitly clear memory for RAM and memory safety.
        del img
        del img_emb
        
        return score

    except Exception as e:
        # a catch all for errors. 
        # I struggled here for wikimedia images due to improper request headers.
        print(f" Vision validation failed for {image_url}: {e}")
        return 0.5

def fetch_from_source(source_name: str, poi_name: str):
    # list of all candidates here.
    candidates = []
    
    # Routing based on source
    if source_name == "unsplash":
        try:
            UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
            url = "https://api.unsplash.com/search/photos"
            params = {"query": f"{poi_name} NYC", "client_id": UNSPLASH_ACCESS_KEY, "per_page": 5}
            resp = requests.get(url, params=params).json().get('results', [])
            for r in resp:
                candidates.append({
                    "source": "Unsplash",
                    "url": r['urls']['regular'],
                    "author": r['user']['name'],
                    "author_profile": r['user']['links']['html'],
                    "license_type": "Unsplash License",
                    "license_url": "https://unsplash.com/license",
                    "coords": None, # Unsplash rarely has public GPS in search
                    "description": r.get('description') or r.get('alt_description')
                })
        except Exception as e:
            print(f"Unsplash error : {e}")

    elif source_name == "pexels":
        try:
            PEXELS_KEY = os.getenv("PEXELS_API_KEY")
            url = f"https://api.pexels.com/v1/search?query={poi_name} NYC&per_page=5"
            headers = {"Authorization": PEXELS_KEY}
            resp = requests.get(url, headers=headers).json().get('photos', [])
            for r in resp:
                candidates.append({
                    "source": "Pexels",
                    "url": r['src']['large'],
                    "author": r['photographer'],
                    "author_profile": r['photographer_url'],
                    "license_type": "Pexels License",
                    "license_url": "https://www.pexels.com/license/",
                    "coords": None,
                    "description": poi_name
                })
        except Exception as e:
            print(f"pexels error : {e}") 

    elif source_name == "wikimedia":
        url = "https://commons.wikimedia.org/w/api.php"
        headers = {"User-Agent": f"NYC-Discovery-Agent/1.0 ({EMAIL})"}
        params = {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"File:{poi_name} NYC", "gsrlimit": 5,
            "prop": "imageinfo", 
            "iiprop": "url|user|extmetadata",
            "iilimit": 1
        }
        try:
            resp_json = requests.get(url, params=params, headers=headers, timeout=10).json()
            pages = resp_json.get("query", {}).get("pages", {})
            
            for _, data in pages.items():
                image_info_list = data.get("imageinfo", [])
                if not image_info_list: continue
                
                info = image_info_list[0]
                direct_image_url = info.get("url") # THIS is the actual .jpg link
                
                # Check if it's a valid image extension to avoid downloading HTML
                # this error cost me a lot of time debugging. Need to keep this in mind for future use.
                if not direct_image_url.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue

                meta = info.get("extmetadata", {})
                lat = meta.get("GPSLatitude", {}).get("value")
                lng = meta.get("GPSLongitude", {}).get("value")

                candidates.append({
                    "source": "Wikimedia",
                    "url": direct_image_url,
                    "author": info.get("user"),
                    "author_profile": f"https://commons.wikimedia.org/wiki/User:{info.get('user')}",
                    "license_type": meta.get("LicenseShortName", {}).get("value", "CC-BY-SA"),
                    "license_url": "https://commons.wikimedia.org/wiki/Main_Page",
                    "coords": (float(lat), float(lng)) if lat and lng else None,
                    "description": meta.get("ObjectName", {}).get("value", "")
                })
        except Exception as e:
            print(f"Wikimedia Source Error: {e}")
        

    return candidates

def run_autonomous_agent():
    try:
        with open('locations.json', 'r') as f:
            locations = json.load(f)
    except FileNotFoundError:
        return

    sources = ["unsplash", "pexels", "wikimedia"]

    for loc in locations:
        print(f"\n--- Agent scouting: {loc['name']} ---")
        all_candidates = []
        
        # Sourcing
        for s in sources:
            all_candidates.extend(fetch_from_source(s, loc['name']))

        # Evaluating
        best_candidate = None
        max_final_score = -1

        for c in all_candidates:
            # visual score
            v_score = get_vision_score(c['url'], loc['name'])
            
            # Geographic score
            g_score = 0.5
            if c['coords']:
                g_score = calculate_geo_score(loc['lat'], loc['lng'], c['coords'][0], c['coords'][1])
            
            # Weighted Decision Logic (70% Vision, 30% Geo)
            final_score = (v_score * 0.7) + (g_score * 0.3)
            if c['source'] in ["Unsplash", "Pexels"]:
                # wikimedia commons images are generally not that great imo.
                # though they get favoured slightly for some reason.
                # so i gave the better looking images from the other sources a bit more weight.
                final_score += 0.08
            
            print(f"[{c['source']}] V-Score: {v_score:.2f} | G-Score: {g_score:.2f} | Final: {final_score:.2f}")

            if final_score > max_final_score:
                max_final_score = final_score
                best_candidate = c
                best_candidate['v_score'] = v_score
                best_candidate['g_score'] = g_score

        # Execution
        if best_candidate:
            save_winner(best_candidate, loc['name'], max_final_score)

def save_winner(c, poi_name, final_score):
    headers = {"User-Agent": f"NYC-Discovery-Agent/1.0 ({EMAIL})"}
    folder_name = poi_name.lower().replace(" ", "_")
    path = os.path.join(OUTPUT_BASE_PATH, folder_name)
    os.makedirs(path, exist_ok=True)

    record = ImageRecord(
        poi_name=poi_name,
        image_url=c['url'],
        source=c['source'],
        author=c['author'],
        author_profile=c['author_profile'],
        license_type=c['license_type'],
        license_url=c['license_url'],
        vision_score=c['v_score'],
        geo_score=c['g_score'],
        final_score=final_score,
        description=c.get('description')
    )

    response = requests.get(c['url'], headers=headers, timeout=15)
    response.raise_for_status()
    img_data = response.content  
    with open(f"{path}/image.jpg", 'wb') as f:
            f.write(img_data)
    with open(f"{path}/metadata.json", 'w') as f:
        f.write(record.model_dump_json(indent=2))
    
    print(f"Winner: {c['source']} with score {final_score:.2f}")

if __name__ == "__main__":
    run_autonomous_agent()