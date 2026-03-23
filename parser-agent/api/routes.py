from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, Header, BackgroundTasks
from typing import Optional, List
import httpx
import asyncio
from services.pdf_service import PDFService
from services.excel_service import ExcelService
from services.llm_service import LLMService
from services.mongo_service import MongoService
import uuid
import os

router = APIRouter()
llm_service = LLMService()
mongo_service = MongoService()

@router.get("/ping")
def ping():
    return {"status": "pong", "message": "API server is reachable"}

GEO_AGENT_URL = os.getenv("GEO_AGENT_URL", "http://localhost:8001/api/enrich")

@router.get("/config")
def get_config():
    # .env 파일에 유효한 gemini key가 설정되어 있는지 확인합니다.
    api_key = getattr(llm_service, "api_key", None)
    has_key = bool(api_key and api_key != "your_gemini_api_key_here")
    return {"has_gemini_key": has_key}

@router.get("/announcements")
async def get_announcements():
    data = await mongo_service.get_recent_announcements(limit=20)
    return {"status": "success", "data": data}

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
    data = await mongo_service.get_announcement(announcement_id)
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    
    parsed_houses = data.get("parsed_houses", [])
    if not parsed_houses:
        return {"status": "success", "data": []}
        
    # Get enriched data for these houses (lat, lng, etc.)
    from main import db_service
    house_ids = [h.get("id") for h in parsed_houses if h.get("id")]
    enriched_data_list = await db_service.get_enriched_data_by_ids(house_ids)
    
    # Merge enriched data into parsed_houses
    enriched_map = {item["id"]: item for item in enriched_data_list}
    
    results = []
    for house in parsed_houses:
        house_id = house.get("id")
        if house_id in enriched_map:
            # Merge enriched fields
            merged = {**house, **enriched_map[house_id]}
            results.append(merged)
        else:
            results.append(house)
            
    return {"status": "success", "data": results}


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    try:
        # Check job_status collection in MongoDB
        status = await mongo_service.db.job_status.find_one({"job_id": job_id})
        if not status:
            return {"count": 0, "step": "PENDING", "total": 0}
        
        result_data = None
        partial_result_data = []
        error_message = None

        if status.get("step") == "COMPLETED":
            text_hash = status.get("hash")
            if text_hash:
                result_data = await mongo_service.get_cache(text_hash)
        else:
            # Provide incremental results and error if not completed
            partial_result_data = status.get("partial_houses", [])
            error_message = status.get("last_error")
        
        return {
            "count": status.get("count", 0),
            "step": status.get("step", ""),
            "total": status.get("total", 0),
            "model": status.get("model", ""),
            "provider": status.get("provider", ""),
            "key_idx": status.get("key_idx", -1),
            "result": result_data,
            "partial_result": partial_result_data,
            "error": error_message
        }
    except Exception as e:
        return {"count": 0, "step": "ERROR", "detail": str(e)}


