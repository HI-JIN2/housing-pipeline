import google.generativeai as genai
from shared.models import ParsedHousingData
from typing import List, Optional
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
        
        # Configure once
        genai.configure(api_key=current_api_key)
        
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        try:
            cached_data = await self.mongo_service.get_cache(text_hash)
            if cached_data:
                print(f"Cache hit from MongoDB for hash {text_hash}")
                return cached_data
        except Exception as e:
            print(f"Error reading mongo cache: {e}")

        # --- Chunking Implementation ---
        # 261 items can be huge. We split the text into chunks of ~10,000 chars.
        chunk_size = 10000
        overlap = 1000
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
            if i + chunk_size >= len(text):
                break

        print(f"Divided text into {len(chunks)} chunks for processing.")
        
        all_houses = []
        final_title = ""
        final_description = ""
        
        for idx, chunk_text in enumerate(chunks):
            print(f"Processing chunk {idx+1}/{len(chunks)}...")
            count_instruction = f"This is part {idx+1} of a large document. Extract ALL housing units found in THIS SPECIFIC TEXT."
            
            prompt = f"""
            You are an expert real estate data extraction agent. 
            Extract structural information for EVERY housing unit mentioned in the provided text snippet.
            
            {count_instruction}

            [CRITICAL INSTRUCTIONS]
            1. **Completeness**: Do not skip any items in this chunk.
            2. **JSON SCHEMA**: 
               Extract each item into:
               - id, name, address, house_type, deposit (만원), monthly_rent (만원), raw_text_reference, extra_info (dict)

            [OUTPUT FORMAT]
            Return ONLY a single valid JSON object:
            {{
                "announcement_title": "string",
                "announcement_description": "string",
                "houses": [ ... ]
            }}
            
            [TEXT CHUNK TO PROCESS]
            {chunk_text}
            """
            
            try:
                response = await self.model.generate_content_async(
                    contents=prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json"
                    )
                )
                
                parsed = json.loads(response.text)
                houses = parsed.get("houses", [])
                if not isinstance(houses, list):
                    # Fallback
                    for k, v in parsed.items():
                        if isinstance(v, list):
                            houses = v
                            break
                            
                all_houses.extend(houses)
                if not final_title:
                    final_title = parsed.get("announcement_title", "")
                if not final_description:
                    final_description = parsed.get("announcement_description", "")
                    
            except Exception as e:
                print(f"Error parsing chunk {idx+1}: {e}")
                continue

        # Convert to Pydantic models to validate and then dump
        valid_houses = []
        for item in all_houses:
            try:
                # Basic cleanup
                if not item.get("id"): item["id"] = f"house-{hashlib.md5(str(item).encode()).hexdigest()[:8]}"
                valid_houses.append(ParsedHousingData(**item).model_dump())
            except Exception as e:
                print(f"Validation failed for one item: {e}")

        final_result = {
            "announcement_title": final_title,
            "announcement_description": final_description,
            "houses": valid_houses
        }

        # Save to MongoDB cache
        try:
            await self.mongo_service.save_cache(text_hash, final_result)
            print(f"Saved total {len(valid_houses)} results to MongoDB cache.")
        except Exception as e:
            print(f"Error writing mongo cache: {e}")
            
        return final_result
