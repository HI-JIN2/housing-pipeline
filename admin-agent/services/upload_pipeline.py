from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from fastapi import HTTPException

from shared.pipeline import AsyncFinishJob, AsyncJob, AsyncPipeline


@dataclass
class UploadStore:
    filename: str
    file_bytes: bytes
    job_id: str
    provider: str
    model_name: Optional[str]
    background_tasks: Any
    llm_service: Any
    pdf_service: Any
    excel_service: Any
    extracted_text: str = ""
    expected_count: Optional[int] = None


class InitUploadJob(AsyncJob[UploadStore]):
    async def process(self, store: UploadStore) -> None:
        return None


class ExtractUploadTextJob(AsyncJob[UploadStore]):
    async def process(self, store: UploadStore) -> None:
        lowered = store.filename.lower()
        if lowered.endswith(".pdf"):
            store.extracted_text = store.pdf_service.extract_text(store.file_bytes)
            return

        if lowered.endswith((".xlsx", ".xls")):
            store.extracted_text, store.expected_count = store.excel_service.extract_text(store.file_bytes)
            return

        raise HTTPException(status_code=400, detail="Unsupported file format.")


class QueueParsingJob(AsyncJob[UploadStore]):
    async def process(self, store: UploadStore) -> None:
        store.background_tasks.add_task(
            store.llm_service.parse_housing_data,
            text=store.extracted_text,
            expected_count=store.expected_count,
            job_id=store.job_id,
            provider=store.provider,
            model_name=store.model_name,
        )


class FinishUploadJob(AsyncFinishJob[UploadStore, dict[str, str]]):
    async def process(self, store: UploadStore) -> dict[str, str]:
        return {"status": "processing", "job_id": store.job_id}


async def execute_upload_pipeline(
    *,
    filename: str,
    file_bytes: bytes,
    job_id: str,
    provider: str,
    model_name: Optional[str],
    background_tasks: Any,
    llm_service: Any,
    pdf_service: Any,
    excel_service: Any,
) -> dict[str, str]:
    pipeline = AsyncPipeline(
        store=UploadStore(
            filename=filename,
            file_bytes=file_bytes,
            job_id=job_id,
            provider=provider,
            model_name=model_name,
            background_tasks=background_tasks,
            llm_service=llm_service,
            pdf_service=pdf_service,
            excel_service=excel_service,
        ),
        init_job=InitUploadJob(),
        jobs=[
            ExtractUploadTextJob(),
            QueueParsingJob(),
        ],
        finish_job=FinishUploadJob(),
    )
    return await pipeline.execute()
