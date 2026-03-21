from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from services.pdf_service import PDFService
from services.excel_service import ExcelService
from services.llm_service import LLMService
from services.mongo_service import MongoService
import uuid
import sys
import os

# To access global kafka_producer from main.py without circular import
from main import kafka_producer

router = APIRouter()
llm_service = LLMService()
mongo_service = MongoService()

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
                parsed_data = await llm_service.parse_housing_data(extracted_text, api_key=gemini_key)
                if parsed_data:
                    housing_data_list.extend(parsed_data)
                    
                    # Store full announcement for future flexibility
                    await mongo_service.save_announcement({
                        "filename": filename,
                        "raw_text": extracted_text,
                        "parsed_houses": [d.model_dump() for d in parsed_data]
                    })
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))

        if not housing_data_list:
            return {"status": "warning", "message": "No housing data successfully parsed from the provided files"}

        # 3. Kafka 에 프로듀스
        published_count = 0
        for data in housing_data_list:
            # Pydantic dict
            message = data.model_dump()
            await kafka_producer.send_message("parsed_data", message)
            published_count += 1

        return {
            "status": "success",
            "message": f"Successfully parsed and sent {published_count} records to Kafka",
            "data": [d.model_dump() for d in housing_data_list]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
