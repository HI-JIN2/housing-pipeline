from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, BackgroundTasks
import logging
from typing import Optional, List
import httpx
import asyncio
import uuid
import os
from services.pdf_service import PDFService
from services.excel_service import ExcelService
from services.llm_service import LLMService
from services.mongo_service import MongoService

router = APIRouter()
llm_service = LLMService()
mongo_service = MongoService()

GEO_AGENT_URL = os.getenv("GEO_AGENT_URL", "http://localhost:8001/api/enrich")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "PLEASE_SET_ADMIN_PASSWORD_IN_DOTENV")

def verify_admin(x_admin_password: Optional[str] = Header(None)):
    if x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized: Admin password required or incorrect.")

@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_job_id: str = Header(None),
    x_gemini_key: str = Header(None),
    x_provider: str = Header("gemini"),
    x_model: str = Header(None),
    x_admin_password: Optional[str] = Header(None)
):
    verify_admin(x_admin_password)
    contents = await file.read()
    filename = file.filename
    
    text = ""
    expected_count = None
    
    if filename.lower().endswith(".pdf"):
        text = PDFService.extract_text(contents)
    elif filename.lower().endswith((".xlsx", ".xls")):
        text, expected_count = ExcelService.extract_text(contents)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format.")

    background_tasks.add_task(
        llm_service.parse_housing_data,
        text=text,
        api_key=x_gemini_key,
        expected_count=expected_count,
        job_id=x_job_id,
        provider=x_provider,
        model_name=x_model
    )
    
    return {"status": "processing", "job_id": x_job_id}

@router.post("/save")
async def save_announcement(data: dict, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    announcement_title = data.get("announcement_title", "Untitled")
    houses = data.get("houses", [])
    
    if not houses:
        raise HTTPException(status_code=400, detail="No houses to save")

    await mongo_service.save_announcement({
        "announcement_title": announcement_title,
        "announcement_description": data.get("announcement_description"),
        "parsed_houses": houses,
        "created_at": str(uuid.uuid1())
    })

    # Sync to Geo Agent
    async with httpx.AsyncClient() as client:
        base_url = GEO_AGENT_URL.rsplit('/', 1)[0]
        try:
            from urllib.parse import quote
            await client.delete(f"{base_url}/housing/{quote(announcement_title)}", timeout=10.0)
        except Exception as e:
            logging.error(f"Postgres cleanup failed: {e}")
        
        tasks = []
        for house in houses:
            house['announcement_id'] = announcement_title
            tasks.append(client.post(GEO_AGENT_URL, json=house, timeout=60.0))
        
        await asyncio.gather(*tasks, return_exceptions=True)

    return {"status": "success", "message": f"Saved {len(houses)} records"}

@router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    doc = await mongo_service.get_announcement(announcement_id)
    if doc:
        title = doc.get("announcement_title")
        if title:
            from urllib.parse import quote
            async with httpx.AsyncClient() as client:
                base_url = GEO_AGENT_URL.rsplit('/', 1)[0]
                try:
                    await client.delete(f"{base_url}/housing/{quote(title)}", timeout=10.0)
                except Exception as e:
                    logging.error(f"Geo Agent cleanup failed: {e}")
    
    success = await mongo_service.delete_announcement(announcement_id)
    if not success:
        raise HTTPException(status_code=404, detail="Announcement not found")
        
    return {"status": "success"}

@router.get("/status/{job_id}")
async def get_job_status(job_id: str, x_admin_password: Optional[str] = Header(None)):
    verify_admin(x_admin_password)
    # Status needs to be accessible for admin to track upload progress
    try:
        status = await mongo_service.db.job_status.find_one({"job_id": job_id})
        if not status:
            return {"count": 0, "step": "PENDING", "total": 0}
        
        result_data = None
        if status.get("step") == "COMPLETED":
            text_hash = status.get("hash")
            if text_hash:
                result_data = await mongo_service.get_cache(text_hash)
        
        return {
            "count": status.get("count", 0),
            "step": status.get("step", ""),
            "total": status.get("total", 0),
            "result": result_data,
            "partial_result": status.get("partial_houses", []),
            "error": status.get("last_error")
        }
    except Exception as e:
        return {"count": 0, "step": "ERROR", "detail": str(e)}
