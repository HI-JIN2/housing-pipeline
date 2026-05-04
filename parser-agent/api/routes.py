from fastapi import APIRouter, HTTPException
import httpx
from services.mongo_service import MongoService
from services.announcement_detail_pipeline import execute_announcement_detail_pipeline
import os
from pymongo.errors import ServerSelectionTimeoutError

router = APIRouter()
mongo_service = MongoService()

@router.get("/ping")
def ping():
    return {"status": "pong", "message": "API server is reachable"}

GEO_AGENT_URL = os.getenv("GEO_AGENT_URL", "http://localhost:8001/api/enrich")

@router.get("/announcements")
async def get_announcements():
    try:
        data = await mongo_service.get_recent_announcements(limit=20)
        return {"status": "success", "data": data}
    except ServerSelectionTimeoutError:
        raise HTTPException(status_code=503, detail="MongoDB is not reachable (is Docker running?)")

@router.get("/geocode")
async def proxy_geocode(address: str):
    async with httpx.AsyncClient() as client:
        base = os.path.dirname(GEO_AGENT_URL)
        try:
            res = await client.get(f"{base}/geocode", params={"address": address}, timeout=10.0)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"Proxy geocode failed for address '{address}': {e}")
            # Try to get more detail from response if possible
            error_detail = str(e)
            if 'res' in locals() and res.content:
                try: error_detail = res.json().get('detail', str(e))
                except: pass
            raise HTTPException(status_code=502, detail=f"Geo Agent Error: {error_detail}")

@router.get("/announcements/{announcement_id}")
async def get_announcement_details(announcement_id: str):
    from main import db_service

    houses = await execute_announcement_detail_pipeline(
        announcement_id=announcement_id,
        mongo_service=mongo_service,
        db_service=db_service,
    )
    if houses is None:
        raise HTTPException(status_code=404, detail="Not found")
    return {"status": "success", "data": houses}
