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

        # --- Deep Chunking Implementation ---
        # 261 items is a lot. Smaller chunks (4k) with high overlap (1.5k) ensure Gemini doesn't get overwhelmed.
        chunk_size = 4000
        overlap = 1500
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
            if i + chunk_size >= len(text):
                break

        print(f"Total text length: {len(text)}. Divided into {len(chunks)} smaller chunks (size={chunk_size}, overlap={overlap})")
        
        all_houses = []
        final_title = ""
        final_description = ""
        seen_ids = set() # Prevent duplicates from overlap
        
        for idx, chunk_text in enumerate(chunks):
            print(f"Processing chunk {idx+1}/{len(chunks)}...")
            
            prompt = f"""
            You are a rigorous data extraction robot. 
            Extract ALL housing units mentioned in the text below. 
            
            [CHUNK INFO] Part {idx+1} of {len(chunks)}.
            [EXPECTED TOTAL] Around {expected_count or "hundreds"}.

            [MUST-FOLLOW RULES]
            1. **Exhaustive Extraction**: Extract EVERY SINGLE ROW/ITEM. Do not summarize. Do not skip. Even if there are 50 items in this chunk, list all 50.
            2. **JSON Format**: Return ONLY a valid JSON object.
            3. **Fields**: id, name, address, house_type, deposit (만원), monthly_rent (만원), raw_text_reference, extra_info (dict).
            
            [TEXT CHUNK]
            {chunk_text}
            """
            
            try:
                response = await self.model.generate_content_async(
                    contents=prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.1 # Lower temperature for higher accuracy
                    )
                )
                
                parsed = json.loads(response.text)
                houses = parsed.get("houses", [])
                
                chunk_added = 0
                for h in houses:
                    # Create a unique key to avoid duplicates from overlaps
                    h_key = f"{h.get('name')}-{h.get('address')}-{h.get('house_type')}"
                    if h_key not in seen_ids:
                        all_houses.append(h)
                        seen_ids.add(h_key)
                        chunk_added += 1
                
                print(f"Chunk {idx+1}: Found {len(houses)} items, added {chunk_added} new items. (Total so far: {len(all_houses)})")
                
                if not final_title: final_title = parsed.get("announcement_title", "")
                if not final_description: final_description = parsed.get("announcement_description", "")
                    
            except Exception as e:
                print(f"Error parsing chunk {idx+1}: {e}")
                continue

        # Convert to Pydantic models to validate and then dump
        valid_houses = []
        for index, item in enumerate(all_houses):
            try:
                # Ensure unique ID
                item["id"] = f"house-{idx}-{index}"
                valid_houses.append(ParsedHousingData(**item).model_dump())
            except Exception as e:
                # Silently skip bad items in the final list
                pass

        final_result = {
            "announcement_title": final_title,
            "announcement_description": final_description,
            "houses": valid_houses
        }

        # Save to MongoDB cache
        try:
            await self.mongo_service.save_cache(text_hash, final_result)
            print(f"COMPLETED: Total {len(valid_houses)} results saved.")
        except Exception as e:
            print(f"Error writing mongo cache: {e}")
            
        return final_result
