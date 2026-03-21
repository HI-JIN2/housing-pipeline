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

        # --- Micro-Chunking Implementation (Nuclear Fix) ---
        # Extremely small chunks to prevent LLM from summarizing.
        chunk_size = 2000
        overlap = 1000
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
            if i + chunk_size >= len(text):
                break

        print(f"Total text length: {len(text)}. Micro-chunked into {len(chunks)} fragments.")
        
        # --- Retry Loop for Expected Count ---
        max_retries = 2
        retry_count = 0
        final_houses = []
        final_title = ""
        
        while retry_count < max_retries:
            all_houses = []
            seen_keys = set()
            
            for idx, chunk_text in enumerate(chunks):
                print(f"Processing Micro-chunk {idx+1}/{len(chunks)} (Attempt {retry_count+1})...")
                
                # Dynamic hint for retries
                retry_hint = ""
                if retry_count > 0:
                    retry_hint = f"\n[RETRY HINT] Previous attempt only found {len(final_houses)} items but we expect {expected_count}. BE EVEN MORE EXHAUSTIVE. DO NOT MISS ANY ROWS."

                prompt = f"""
                [EXTRACTOR MODE: MECHANICAL]
                You are a data extraction robot. Your purpose is EXHAUSTIVE EXTRACTION.{retry_hint}
                
                [CHUNK CONTEXT] Part {idx+1} of {len(chunks)}.
                
                [CRITICAL] Extract EVERY SINGLE housing unit/item mentioned in the [INPUT TEXT].
                - DO NOT SUMMARIZE.
                - DO NOT SKIP.
                - DO NOT GENERALIZE.
                - Extract even if the item is partial (the overlap will catch it).
                - Return ONLY a valid JSON object.

                [JSON SCHEMA]
                {{
                    "announcement_title": "string",
                    "houses": [
                        {{
                            "name": "string",
                            "address": "string", 
                            "house_type": "string",
                            "deposit": number (만원),
                            "monthly_rent": number (만원),
                            "extra_info": {{}}
                        }}
                    ]
                }}
                
                [INPUT TEXT]
                {chunk_text}
                """
                
                try:
                    response = await self.model.generate_content_async(
                        contents=prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            temperature=0.2 if retry_count > 0 else 0.0
                        )
                    )
                    
                    parsed = json.loads(response.text)
                    houses = parsed.get("houses", [])
                    
                    for h in houses:
                        h_key = f"{h.get('name')}-{h.get('address')}-{h.get('house_type')}-{h.get('deposit')}"
                        if h_key not in seen_keys:
                            all_houses.append(h)
                            seen_keys.add(h_key)
                    
                    if not final_title: final_title = parsed.get("announcement_title", "")
                        
                except Exception as e:
                    print(f"Error in Micro-chunk {idx+1}: {e}")
                    continue

            final_houses = all_houses
            
            # Check if we should retry
            if expected_count and len(final_houses) < (expected_count * 0.95):
                retry_count += 1
                print(f"Count mismatch: Got {len(final_houses)}, Expected {expected_count}. Retrying ({retry_count}/{max_retries})...")
            else:
                break

        valid_houses = []
        for index, item in enumerate(final_houses):
            try:
                house_identity = f"{final_title}|{item.get('name')}|{item.get('address')}|{item.get('house_type')}|{item.get('deposit')}"
                stable_id = hashlib.md5(house_identity.encode()).hexdigest()
                item["id"] = f"h-{stable_id}"
                valid_houses.append(ParsedHousingData(**item).model_dump())
            except Exception as e:
                pass

        final_result = {
            "announcement_title": final_title,
            "announcement_description": f"Extracted via Nuclear Micro-chunking. Total items: {len(valid_houses)}",
            "houses": valid_houses
        }

        # Save to MongoDB cache
        try:
            await self.mongo_service.save_cache(text_hash, final_result)
            print(f"FINAL RESULT: {len(valid_houses)} items stored.")
        except Exception as e:
            print(f"Cache write error: {e}")
            
        return final_result
