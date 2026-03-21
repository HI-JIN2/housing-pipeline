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
    return {"status": "success", "data": data.get("parsed_houses", [])}

@router.post("/upload")
async def upload_file(files: list[UploadFile] = File(...), gemini_key: Optional[str] = Form(None)):
    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 files allowed")

    try:
        housing_data_list = []
        for file in files:
            filename = file.filename.lower()
            if not (filename.endswith('.pdf') or filename.endswith('.xlsx')):
                continue

            file_bytes = await file.read()
            
            # 1. 텍스트 추출 (확장자별 분기)
            if filename.endswith('.pdf'):
                extracted_text = PDFService.extract_text(file_bytes)
            else:
                extracted_text = ExcelService.extract_text(file_bytes)
                
            if not extracted_text.strip():
                continue
                
            # 2. LLM 구조화
            try:
                parsed_result = await llm_service.parse_housing_data(extracted_text, api_key=gemini_key)
                if parsed_result:
                    houses = parsed_result.get("houses", [])
                    housing_data_list.extend(houses)
                    
                    # Store full announcement for future flexibility
                    await mongo_service.save_announcement({
                        "filename": filename,
                        "raw_text": extracted_text,
                        "announcement_title": parsed_result.get("announcement_title"),
                        "announcement_description": parsed_result.get("announcement_description"),
                        "parsed_houses": houses
                    })
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))

        if not housing_data_list:
            return {"status": "warning", "message": "No housing data successfully parsed from the provided files"}

        # 3. Geo Agent에게 직접 전송 (HTTP POST)
        published_count = 0
        async with httpx.AsyncClient() as client:
            for data in housing_data_list:
                message = data
                try:
                    # Geo Agent의 신규 엔드포인트로 JSON 전송
                    response = await client.post(GEO_AGENT_URL, json=message, timeout=10.0)
                    if response.status_code == 200:
                        published_count += 1
                    else:
                        print(f"Failed to send to Geo Agent: {response.text}")
                except Exception as e:
                    print(f"Error calling Geo Agent: {e}")

        return {
            "status": "success",
            "message": f"Successfully parsed and enriched {published_count} records via Geo Agent",
            "data": housing_data_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
