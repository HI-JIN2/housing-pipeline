from pydantic import BaseModel, Field
from typing import Optional

class ParsedHousingData(BaseModel):
    id: str = Field(description="고유 ID")
    index: Optional[int] = Field(None, description="번호")
    district: str = Field(description="자치구")
    complex_no: Optional[str] = Field(None, description="단지번호")
    name: str = Field(description="단지명/주택명")
    address: str = Field(description="주택 상세 주소")
    unit_no: Optional[str] = Field(None, description="호수")
    area: float = Field(description="면적 (전용면적)")
    house_type: Optional[str] = Field(None, description="주택 유형/타입")
    elevator: Optional[str] = Field(None, description="승강기 여부")
    deposit: float = Field(description="보증금 (단위: 만원)")
    monthly_rent: float = Field(description="월세 (단위: 만원)")
    raw_text_reference: Optional[str] = Field(None, description="파싱 원본 텍스트")
    extra_info: dict = Field(default_factory=dict, description="기타 모든 추가 정보 (MongoDB 활용)")

class EnrichedHousingData(ParsedHousingData):
    lat: float = Field(description="위도 (Latitude)")
    lng: float = Field(description="경도 (Longitude)")
    nearest_station: str = Field(description="인접 지하철역 이름")
    distance_meters: int = Field(description="인접 지하철역과의 도보 거리 (미터)")
    walking_time_mins: int = Field(description="도보 소요 시간 (분)")
