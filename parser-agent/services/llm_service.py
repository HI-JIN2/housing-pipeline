from openai import AsyncOpenAI
from shared.models import ParsedHousingData
from typing import List
import os

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("Warning: OPENAI_API_KEY is not set properly.")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def parse_housing_data(self, text: str) -> List[ParsedHousingData]:
        prompt = """
        다음은 주택청약 공고문 또는 주택 목록 PDF에서 추출한 텍스트입니다.
        여기에서 각 주택(아파트/호실)의 정보를 추출하여 JSON 리스트 형태로 반환하세요.
        반드시 지정된 JSON 스키마를 준수해야 합니다.
        여러 개의 주택이 있다면 모두 추출해야 합니다.
        
        [JSON 모델 필드 설명]
        - id: 고유 ID (공고명+순번 등으로 만들어주세요)
        - name: 아파트/주택 이름 (예: OO아파트, 행복주택 등)
        - address: 상세 주소
        - house_type: 주택 유형 (예: 투룸, 59A, 84B 등)
        - deposit: 보증금 (단위: 만원값 정수)
        - monthly_rent: 월세 (단위: 만원값 정수, 없으면 0)
        - raw_text_reference: 이 결과를 도출해낸 원문 내용 일부
        
        [텍스트]
        {text}
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts housing information perfectly into JSON format."},
                {"role": "user", "content": prompt.format(text=text[:10000])} # 제한된 길이 (필요시 청킹 로직 추가 가능)
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            import json
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            # GPT가 {"주택목록": [...]} 형태로 감싸서 줄 수 있으므로 리스트를 찾습니다.
            results = []
            for k, v in parsed.items():
                if isinstance(v, list):
                    results.extend(v)
                    break
            if not results and isinstance(parsed, dict) and "id" in parsed:
                # 단건인 경우
                results.append(parsed)
                
            housing_list = [ParsedHousingData(**item) for item in results]
            return housing_list
        except Exception as e:
            print(f"Error parsing LLM output: {e}")
            print(f"Raw output: {response.choices[0].message.content}")
            return []
