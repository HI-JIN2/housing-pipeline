from services.db_service import DBService
from services.kakao_api import KakaoGeoClient
from services.enrichment_pipeline import execute_enrichment_pipeline

db_service = DBService()
kakao_client = KakaoGeoClient()

async def enrich_and_save(data: dict):
    try:
        return await execute_enrichment_pipeline(
            raw_data=data,
            db_service=db_service,
            kakao_client=kakao_client,
        )
    except Exception as e:
        print(f"Failed to process message: {e}")
