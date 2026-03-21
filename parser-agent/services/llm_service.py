import google.generativeai as genai
from shared.models import ParsedHousingData
from typing import List
import os
import json
import hashlib
from services.mongo_service import MongoService

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("Warning: GEMINI_API_KEY is not set properly.")
        
        # Use gemini-flash-latest base alias to fix 404 error with v1beta
        self.model = genai.GenerativeModel("gemini-flash-latest")
        
        self.mongo_service = MongoService()

    async def parse_housing_data(self, text: str, api_key: str = None, expected_count: Optional[int] = None):
        current_api_key = api_key or self.api_key
        if not current_api_key or current_api_key == "your_gemini_api_key_here":
            raise ValueError("Gemini API key is not set. Please provide it in the UI or .env file.")
        
        # Override key for this call
        genai.configure(api_key=current_api_key)
        
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        try:
            cached_data = await self.mongo_service.get_cache(text_hash)
            if cached_data:
                print(f"Cache hit from MongoDB for hash {text_hash}")
                if isinstance(cached_data, dict):
                    return cached_data
                elif isinstance(cached_data, list):
                    return {"houses": cached_data}
        except Exception as e:
            print(f"Error reading mongo cache: {e}")

        count_instruction = f"I expect exactly {expected_count} housing units in this text. DO NOT SKIP ANY." if expected_count else ""

        prompt = f"""
        You are an expert real estate data extraction agent. 
        Your task is to extract structural information for EVERY housing unit/apartment mentioned in the provided text.
        
        {count_instruction}

        [CRITICAL INSTRUCTIONS]
        1. **Completeness**: Do not skip any items. Even if there are hundreds of items in a table, extract all of them. Use all your available output capacity.
        2. **Monthly Rent Accuracy**: Pay extremely close attention to columns labeled "월임대료", "임대료", or "월세". 
           - Ensure you do not default to 0 if a value is present later in the table.
           - Check if there are different rent values for different social brackets (e.g., General vs. Vulnerable groups) and pick the standard/general one unless specified.
        3. **Accuracy**: Ensure the address, deposit, and rent are captured exactly as they appear.
        4. **Handling Units**: 
           - Deposit and Monthly Rent should be in 'ten thousand KRW' (만원) units. 
           - Example: 150,000,000 KRW -> 15000. 500,000 KRW -> 50.
        
        [JSON SCHEMA]
        Extract each item into the following format:
        - id: Unique ID (announcement name + index)
        - name: Apartment/Housing name
        - address: Full detailed address
        - house_type: Housing type/size
        - deposit: Security deposit (Integer, unit: 10,000 KRW)
        - monthly_rent: Monthly rent (Integer, unit: 10,000 KRW, 0 if not applicable)
        - raw_text_reference: A snippet of original text
        - extra_info: A dictionary containing ALL other discovered columns (e.g., "방개수", "저층여부", "전용면적", "승강기설치여부", "주차대수", "전용면적", "자치구" 등)
        
        [OUTPUT FORMAT]
        Return ONLY a single valid JSON object:
        {{
            "announcement_title": "string",
            "announcement_description": "string",
            "houses": [
                {{
                    "id": "string",
                    "name": "string",
                    "address": "string",
                    "house_type": "string",
                    "deposit": 10000,
                    "monthly_rent": 50,
                    "raw_text_reference": "string",
                    "extra_info": {{
                        "방개수": "3개",
                        "주차대수": "1.2대",
                        "승강기": "있음"
                    }}
                }},
                ...
            ]
        }}
        
        [TEXT TO PROCESS]
        {text[:30000]}
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
            title = parsed.get("announcement_title", "")
            description = parsed.get("announcement_description", "")
            
            if "houses" in parsed and isinstance(parsed["houses"], list):
                results = parsed["houses"]
            else:
                # Fallback for older formats or mis-formatted LLM output
                for k, v in parsed.items():
                    if isinstance(v, list):
                        results.extend(v)
                        break
            
            housing_list = [ParsedHousingData(**item) for item in results]
            
            # Save to MongoDB cache
            cache_data = {
                "announcement_title": title,
                "announcement_description": description,
                "houses": [item.model_dump() for item in housing_list]
            }
            try:
                await self.mongo_service.save_cache(text_hash, cache_data)
                print(f"Saved results to MongoDB cache for hash {text_hash}")
            except Exception as e:
                print(f"Error writing mongo cache: {e}")
                
            return cache_data
            
        except Exception as e:
            print(f"Error parsing LLM output: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Raw output: {response.text}")
            return []
