import os
import requests
from typing import List
from PIL import Image
from io import BytesIO
from geopy.distance import geodesic
from sentence_transformers import SentenceTransformer, util
from core.schema import Candidate

# Initialize models once
vision_model = SentenceTransformer('clip-ViT-B-32')

class ImageToolkit:
    @staticmethod
    def fetch_unsplash(poi_name: str) -> List[Candidate]:
        try:
            key = os.getenv("UNSPLASH_ACCESS_KEY")
            url = "https://api.unsplash.com/search/photos"
            params = {"query": f"{poi_name} NYC", "client_id": key, "per_page": 5}
            resp = requests.get(url, params=params).json().get('results', [])
            return [
                Candidate(
                    url=r['urls']['regular'],
                    source="Unsplash",
                    author=r['user']['name'],
                    author_profile=r['user']['links']['html'],
                    license_type="Unsplash License",
                    license_url="https://unsplash.com/license",
                    description=r.get('description') or r.get('alt_description')
                ) for r in resp
            ]
        except Exception as e:
            print(f"Unsplash Tool Error: {e}")
            return []

    @staticmethod
    def fetch_pexels(poi_name: str) -> List[Candidate]:
        """Integrated Pexels Tool"""
        try:
            key = os.getenv("PEXELS_API_KEY")
            url = f"https://api.pexels.com/v1/search?query={poi_name} NYC&per_page=5"
            headers = {"Authorization": key}
            resp = requests.get(url, headers=headers).json().get('photos', [])
            return [
                Candidate(
                    url=r['src']['large'],
                    source="Pexels",
                    author=r['photographer'],
                    author_profile=r['photographer_url'],
                    license_type="Pexels License",
                    license_url="https://www.pexels.com/license/",
                    description=poi_name
                ) for r in resp
            ]
        except Exception as e:
            print(f"Pexels Tool Error: {e}")
            return []

    @staticmethod
    def fetch_wikimedia(poi_name: str) -> List[Candidate]:
        email = os.getenv("EMAIL")
        url = "https://commons.wikimedia.org/w/api.php"
        headers = {"User-Agent": f"NYC-Discovery-Agent/1.0 ({email})"}
        params = {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": f"File:{poi_name} NYC", "gsrlimit": 5,
            "prop": "imageinfo", "iiprop": "url|user|extmetadata", "iilimit": 1
        }
        try:
            resp_json = requests.get(url, params=params, headers=headers, timeout=10).json()
            pages = resp_json.get("query", {}).get("pages", {})
            results = []
            for _, data in pages.items():
                info_list = data.get("imageinfo", [])
                if not info_list: continue
                info = info_list[0]
                url_img = info.get("url")
                if not url_img.lower().endswith(('.jpg', '.jpeg', '.png')): continue
                
                meta = info.get("extmetadata", {})
                lat = meta.get("GPSLatitude", {}).get("value")
                lng = meta.get("GPSLongitude", {}).get("value")

                results.append(Candidate(
                    url=url_img,
                    source="Wikimedia",
                    author=info.get("user"),
                    author_profile=f"https://commons.wikimedia.org/wiki/User:{info.get('user')}",
                    license_type=meta.get("LicenseShortName", {}).get("value", "CC-BY-SA"),
                    license_url="https://commons.wikimedia.org/wiki/Main_Page",
                    coords=(float(lat), float(lng)) if lat and lng else None,
                    description=meta.get("ObjectName", {}).get("value", "")
                ))
            return results
        except Exception as e:
            print(f"Wikimedia Tool Error: {e}")
            return []

    @staticmethod
    def calculate_scores(candidate: Candidate, poi_name: str, target_lat: float, target_lng: float):
        """Unified scoring tool"""
        # 1. Vision Score
        try:
            headers = {"User-Agent": f"Agent ({os.getenv('EMAIL')})"}
            resp = requests.get(candidate.url, headers=headers, timeout=10)
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img_emb = vision_model.encode(img)
            text_emb = vision_model.encode([f"a photo of {poi_name} NYC", "landmark"])
            candidate.v_score = float(util.cos_sim(img_emb, text_emb).max())
            del img # Memory safety for 8GB RAM
        except:
            candidate.v_score = 0.5

        # 2. Geo Score
        if candidate.coords:
            dist = geodesic((target_lat, target_lng), candidate.coords).km
            if dist < 0.1: candidate.g_score = 0.6
            elif dist <= 1.5: candidate.g_score = 1.0
            elif dist <= 4.0: candidate.g_score = 0.4
            else: candidate.g_score = 0.0
        else:
            candidate.g_score = 0.5

        # 3. Final Weighted Score
        candidate.final_score = (candidate.v_score * 0.7) + (candidate.g_score * 0.3)
        if candidate.source in ["Unsplash", "Pexels"]:
            candidate.final_score += 0.08