from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import httpx
from services.pdf_service import PDFService
from services.excel_service import ExcelService
from services.llm_service import LLMService
from services.mongo_service import MongoService
import uuid
import sys
import os

router = APIRouter()
llm_service = LLMService()
mongo_service = MongoService()

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
async def upload_file(files: list[UploadFile] = File(...), gemini_key: Optional[str] = Form(None)):
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 files allowed")

    try:
        all_houses = []
        announcement_title = None
        announcement_desc = None
        
        for file in files:
            filename = file.filename.lower()
            if not (filename.endswith('.pdf') or filename.endswith('.xlsx')):
                continue

            file_bytes = await file.read()
            
            if filename.endswith('.pdf'):
                extracted_text = PDFService.extract_text(file_bytes)
            else:
                extracted_text = ExcelService.extract_text(file_bytes)
                
            if not extracted_text.strip():
                continue
                
            try:
                parsed_result = await llm_service.parse_housing_data(extracted_text, api_key=gemini_key)
                if parsed_result:
                    houses = parsed_result.get("houses", [])
                    all_houses.extend(houses)
                    # Use the first available title/desc as the set's metadata
                    if not announcement_title:
                        announcement_title = parsed_result.get("announcement_title")
                    if not announcement_desc:
                        announcement_desc = parsed_result.get("announcement_description")
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))

        if not all_houses:
            return {"status": "warning", "message": "No housing data successfully parsed from the provided files"}

        # Store as ONE unified announcement set
        await mongo_service.save_announcement({
            "filenames": [f.filename for f in files],
            "announcement_title": announcement_title or files[0].filename,
            "announcement_description": announcement_desc,
            "parsed_houses": all_houses
        })

        # 3. Geo Agent에게 직접 전송 (HTTP POST)
        published_count = 0
        async with httpx.AsyncClient() as client:
            for data in all_houses:
                message = data
                try:
                    response = await client.post(GEO_AGENT_URL, json=message, timeout=10.0)
                    if response.status_code == 200:
                        published_count += 1
                except Exception as e:
                    print(f"Error calling Geo Agent: {e}")

        return {
            "status": "success",
            "message": f"Successfully parsed and enriched {published_count} records",
            "data": all_houses
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
