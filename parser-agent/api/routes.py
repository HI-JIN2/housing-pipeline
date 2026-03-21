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
async def upload_file(files: list[UploadFile] = File(...)):
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
            parsed_data = await llm_service.parse_housing_data(extracted_text)
            if parsed_data:
                housing_data_list.extend(parsed_data)

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
