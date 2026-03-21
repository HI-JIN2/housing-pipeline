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
                response.raise_for_status()
                data = response.json()
                
                if data.get("documents"):
                    doc = data["documents"][0]
                    # Kakao API returns x as longitude, y as latitude
                    # y: string format of float
                    lat = float(doc["y"])
                    lng = float(doc["x"])
                    return (lat, lng)
            except Exception as e:
                print(f"Error calling Kakao Geocoding API: {e}")
                
        return (None, None)
