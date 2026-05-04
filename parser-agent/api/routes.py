from fastapi import APIRouter, HTTPException
import httpx
from services.llm_service import LLMService
from services.mongo_service import MongoService
from services.announcement_detail_pipeline import execute_announcement_detail_pipeline
import os
from pymongo.errors import ServerSelectionTimeoutError

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
