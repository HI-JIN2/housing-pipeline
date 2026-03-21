import google.generativeai as genai
from shared.models import ParsedHousingData
from typing import List
import os
import json

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("Warning: GEMINI_API_KEY is not set properly.")
        
        genai.configure(api_key=self.api_key)
        # Use gemini-1.5-flash for fast and cost-effective text tasks
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def parse_housing_data(self, text: str) -> List[ParsedHousingData]:
        prompt = f"""
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
        
        [출력 형식]
        반드시 다음과 같은 구조를 가진 JSON 텍스트 한 개만 출력하세요:
        {{
            "houses": [
                {{
                    "id": "문자열",
                    "name": "문자열",
                    "address": "문자열",
                    "house_type": "문자열",
                    "deposit": 10000,
                    "monthly_rent": 50,
                    "raw_text_reference": "문자열"
                }}
            ]
        }}
        
        [텍스트]
        {text[:15000]}
        """
        
        try:
            # Generate content asynchronously
            response = await self.model.generate_content_async(
                contents=prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            
            content = response.text
            parsed = json.loads(content)
            
            results = []
            if "houses" in parsed and isinstance(parsed["houses"], list):
                results = parsed["houses"]
            else:
                for k, v in parsed.items():
                    if isinstance(v, list):
                        results.extend(v)
                        break
                if not results and isinstance(parsed, dict) and "id" in parsed:
                    results.append(parsed)
                    
            housing_list = [ParsedHousingData(**item) for item in results]
            return housing_list
            
        except Exception as e:
            print(f"Error parsing LLM output: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Raw output: {response.text}")
            return []
