from fastapi import APIRouter, UploadFile, File, HTTPException
from services.pdf_service import PDFService
from services.excel_service import ExcelService
from services.llm_service import LLMService
import uuid
import sys
import os

# To access global kafka_producer from main.py without circular import
from main import kafka_producer

router = APIRouter()
llm_service = LLMService()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename.lower()
    if not (filename.endswith('.pdf') or filename.endswith('.xlsx')):
        raise HTTPException(status_code=400, detail="Only PDF and XLSX files are allowed")

    try:
        file_bytes = await file.read()
        
        # 1. 텍스트 추출 (확장자별 분기)
        if filename.endswith('.pdf'):
            extracted_text = PDFService.extract_text(file_bytes)
        else:
            extracted_text = ExcelService.extract_text(file_bytes)
            
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from file")
            
        # 2. LLM 구조화
        housing_data_list = await llm_service.parse_housing_data(extracted_text)
        if not housing_data_list:
            return {"status": "warning", "message": "No housing data successfully parsed", "raw_text_preview": extracted_text[:200]}

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
