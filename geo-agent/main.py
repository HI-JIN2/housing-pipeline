from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import asyncio
import os
import sys

# Load shared models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

from services.enrich_service import enrich_and_save, db_service
from services.kakao_api import KakaoGeoClient

kakao_client = KakaoGeoClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Geo Agent...")
    # Initialize DB in the background
    asyncio.create_task(db_service.init_pool())
    yield
    print("Shutting down Geo Agent...")
    await db_service.close_pool()

app = FastAPI(title="Geo Agent (공고zip)", lifespan=lifespan)

# Direct health check
@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Geo Agent is running"}

@app.get("/")
def health_check():
    return {"status": "ok", "service": "geo-agent"}

@app.post("/api/enrich")
async def enrich_data(data: dict):
    print(f"Received data for enrichment: {data.get('name')} at {data.get('address')}")
    await enrich_and_save(data)
    return {"status": "success"}

@app.get("/api/geocode")
async def geocode_address(address: str):
    try:
        lat, lng = await kakao_client.get_coordinates(address)
        return {"lat": lat, "lng": lng}
    except Exception as e:
        print(f"Geocoding failed for address '{address}': {e}")
        raise HTTPException(status_code=502, detail=f"Geo Agent Error: {str(e)}")

@app.delete("/api/housing/{announcement_id}")
async def delete_housing_data(announcement_id: str):
    await db_service.delete_housing_data_by_announcement(announcement_id)
    return {"status": "success"}
