import os
import httpx
from typing import Tuple, Optional

class KakaoGeoClient:
    def __init__(self):
        self.api_key = os.getenv("KAKAO_REST_API_KEY")
        self.base_url = "https://dapi.kakao.com/v2/local/search/address.json"
        
    async def get_coordinates(self, address: str) -> Tuple[Optional[float], Optional[float]]:
        """Returns tuple of (latitude, longitude) or (None, None) if not found"""
        if not self.api_key or self.api_key == "your_kakao_rest_api_key_here":
            print(f"[{address}] Kakao API Key is not set. Returning dummy values.")
            return (37.5665, 126.9780) # 서울시청 (Mock)
            
        headers = {"Authorization": f"KakaoAK {self.api_key}"}
        params = {"query": address}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, headers=headers, params=params)
                if response.status_code != 200:
                    print(f"Kakao API Error: Status {response.status_code}, Body: {response.text}")
                    return (None, None)
                
                data = response.json()
                if not data.get("documents"):
                    print(f"Kakao API: No documents found for address '{address}'")
                    return (None, None)
                
                doc = data["documents"][0]
                lat = float(doc["y"])
                lng = float(doc["x"])
                return (lat, lng)
            except Exception as e:
                print(f"Exception during Kakao Geocoding for '{address}': {e}")
                
        return (None, None)
