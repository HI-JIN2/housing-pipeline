from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, BackgroundTasks
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

@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    expected_count: Optional[int] = Form(None),
    gemini_key: Optional[str] = Form(None),
    x_job_id: Optional[str] = Header(None)
):
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 files allowed")

    try:
        all_text = ""
        for file in files:
            content = await file.read()
            if file.filename.lower().endswith('.pdf'):
                all_text += PDFService.extract_text(content)
            elif file.filename.lower().endswith(('.xlsx', '.xls')):
                all_text += ExcelService.extract_text(content)
        
        # Parse data with LLM
        # We pass job_id (from header) for real-time progress tracking
        result = await llm_service.parse_housing_data(
            all_text, 
            api_key=gemini_key, 
            expected_count=expected_count,
            job_id=x_job_id
        )
        
        return result
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    try:
        # Check job_status collection in MongoDB
        status = await mongo_service.db.job_status.find_one({"job_id": job_id})
        if not status:
            return {"count": 0, "step": "PENDING", "total": 0}
        
        return {
            "count": status.get("count", 0),
            "step": status.get("step", ""),
            "total": status.get("total", 0),
            "model": status.get("model", ""),
            "key_idx": status.get("key_idx", -1)
        }
    except Exception as e:
        return {"count": 0, "step": "ERROR", "detail": str(e)}

@router.post("/save")
async def save_announcement(data: dict):
    announcement_title = data.get("announcement_title", "Untitled")
    houses = data.get("houses", [])
    
    if not houses:
        raise HTTPException(status_code=400, detail="No houses to save")

    # 1. Save to Mongo
    # Use title as a stable identifier for duplicate prevention in Mongo if needed,
    # or just create a new one. Here we create a new one or update existing by title.
    announcement_id = str(uuid.uuid4()) # For internal grouping
    
    await mongo_service.save_announcement({
        "announcement_title": announcement_title,
        "announcement_description": data.get("announcement_description"),
        "parsed_houses": houses,
        "created_at": str(uuid.uuid1()) # Timestamp surrogate
    })

    # 2. Sync to Geo Agent (Postgres)
    # First, delete existing data for this title to avoid duplicates
    async with httpx.AsyncClient() as client:
        await client.delete(f"{os.path.dirname(GEO_AGENT_URL)}/housing/{announcement_title}")
        
        tasks = []
        for house in houses:
            house['announcement_id'] = announcement_title
            tasks.append(client.post(GEO_AGENT_URL, json=house, timeout=60.0))
        
        await asyncio.gather(*tasks, return_exceptions=True)

    return {"status": "success", "message": f"Saved {len(houses)} records"}

@router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str):
    # 1. Get title from Mongo first to clean up Postgres
    doc = await mongo_service.get_announcement(announcement_id)
    if doc:
        title = doc.get("announcement_title")
        if title:
            async with httpx.AsyncClient() as client:
                await client.delete(f"{os.path.dirname(GEO_AGENT_URL)}/housing/{title}")
    
    # 2. Delete from Mongo
    success = await mongo_service.delete_announcement(announcement_id)
    if not success:
        raise HTTPException(status_code=404, detail="Announcement not found")
        
    return {"status": "success"}
