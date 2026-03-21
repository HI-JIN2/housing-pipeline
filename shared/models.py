from pydantic import BaseModel, Field
from typing import Optional

class ParsedHousingData(BaseModel):
    id: str = Field(description="고유 ID (보통 공고문명+순번)")
    name: str = Field(description="아파트/주택 이름")
    address: str = Field(description="주택 상세 주소")
    house_type: str = Field(description="주택 유형 (예: 59A, 투룸 등)")
    deposit: float = Field(description="보증금 (단위: 만원)")
    monthly_rent: float = Field(description="월세 (단위: 만원)")
    raw_text_reference: Optional[str] = Field(None, description="파싱에 사용된 원본 텍스트 조각")
    extra_info: dict = Field(default_factory=dict, description="기타 추가 정보 (방 개수, 주차, 승강기 등)")

class EnrichedHousingData(ParsedHousingData):
    lat: float = Field(description="위도 (Latitude)")
    lng: float = Field(description="경도 (Longitude)")
    nearest_station: str = Field(description="인접 지하철역 이름")
    distance_meters: int = Field(description="인접 지하철역과의 도보 거리 (미터)")
    walking_time_mins: int = Field(description="도보 소요 시간 (분)")
