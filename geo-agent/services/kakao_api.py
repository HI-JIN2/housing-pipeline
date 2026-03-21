import os
import httpx
from typing import Tuple, Optional

class KakaoGeoClient:
    def __init__(self):
        self.api_key = os.getenv("KAKAO_REST_API_KEY")
        self.base_url = "https://dapi.kakao.com/v2/local/search/address.json"
        
    async def get_coordinates(self, address: str) -> Tuple[Optional[float], Optional[float]]:
        """Returns tuple of (latitude, longitude) or (None, None) if not found. Includes retries."""
        if not self.api_key or self.api_key == "your_kakao_rest_api_key_here":
            print(f"[{address}] Kakao API Key is not set. Returning dummy values.")
            return (37.5665, 126.9780)
            
        import re
        import asyncio
        
        # Clean Address: Strip content in parentheses which often confuses the API
        # e.g., "은평구 진흥로11길 1-12 (대조동 179-21 외)" -> "은평구 진흥로11길 1-12"
        clean_address = re.sub(r'\(.*?\)', '', address).strip()
        
        headers = {"Authorization": f"KakaoAK {self.api_key}"}
        params = {"query": clean_address}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for attempt in range(3): # Try 3 times
                try:
                    response = await client.get(self.base_url, headers=headers, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("documents"):
                            doc = data["documents"][0]
                            return (float(doc["y"]), float(doc["x"]))
                        else:
                            # If clean address failed, try original (sometimes parentheses have critical info)
                            if clean_address != address:
                                params["query"] = address
                                continue # Retry with original address
                            print(f"Kakao API: No results for '{clean_address}'")
                            return (None, None)
                    elif response.status_code == 429:
                        print(f"Kakao API: Rate Limited (429). Waiting 2s...")
                        await asyncio.sleep(2)
                        continue
                    else:
                        print(f"Kakao API Error: {response.status_code} - {response.text}")
                        break
                except Exception as e:
                    print(f"Geocoding Attempt {attempt+1} failed for '{address}': {e}")
                    await asyncio.sleep(1)
                    
        return (None, None)
