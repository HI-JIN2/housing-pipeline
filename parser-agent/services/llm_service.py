from google import genai
from google.genai import types
from openai import OpenAI
from shared.models import ParsedHousingData
from typing import List, Optional
import os
import json
import hashlib
from services.mongo_service import MongoService

class LLMService:
    def __init__(self):
        # Collect all available Gemini API keys from environment
        self.api_keys = []
        for i in range(10): # Look for GEMINI_API_KEY, GEMINI_API_KEY1, ..., GEMINI_API_KEY9
            key_name = "GEMINI_API_KEY" if i == 0 else f"GEMINI_API_KEY{i}"
            val = os.getenv(key_name)
            if val and val != "your_gemini_api_key_here":
                self.api_keys.append(val)
        
        if not self.api_keys:
            print("Warning: No GEMINI_API_KEY found in environment.")
        
        self.current_key_idx = 0
        
        # Models to cycle through (Gemini)
        self.available_models = [
            "models/gemini-2.0-flash-exp", 
            "models/gemini-1.5-flash",
            "models/gemini-2.5-flash", 
            "models/gemini-2.5-flash-lite", 
            "models/gemini-3.1-flash-lite-preview", 
            "models/gemini-3-flash-preview",
            "models/gemini-1.5-flash-8b"
        ]
        self.current_model_idx = 0
        
        # Initial Gemini config
        if self.api_keys:
            self.gemini_client = genai.Client(api_key=self.api_keys[self.current_key_idx])
            self.active_gemini_model = self.available_models[self.current_model_idx]
            
        # OpenAI Config
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        if self.openai_api_key and self.openai_api_key != "your_openai_api_key_here":
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        self.mongo_service = MongoService()

    def _switch_model(self, remove_current=False):
        if remove_current and len(self.available_models) > 1:
            removed = self.available_models.pop(self.current_model_idx)
            print(f"🚫 Removing unsupported model: {removed}")
            if self.current_model_idx >= len(self.available_models):
                self.current_model_idx = 0
        else:
            self.current_model_idx = (self.current_model_idx + 1) % len(self.available_models)
            
        model_name = self.available_models[self.current_model_idx]
        print(f"🔄 Switching model to: {model_name}")
        self.active_gemini_model = model_name
        return model_name

    def _switch_key(self):
        if not self.api_keys or len(self.api_keys) <= 1:
            print("⚠️ No more keys to switch to.")
            return False
            
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        new_key = self.api_keys[self.current_key_idx]
        print(f"🔑 Switching API Key to index {self.current_key_idx} (Ends in ...{new_key[-4:]})")
        
        self.gemini_client = genai.Client(api_key=new_key)
        self.current_model_idx = 0
        self.active_gemini_model = self.available_models[0]
        return True

    def _chunk_text(self, text: str, chunk_size: int = 12000, overlap: int = 2000) -> List[str]:
        # Simple character-based chunking with overlap for robustness
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
            if i + chunk_size >= len(text):
                break
        return chunks

    async def parse_housing_data(self, text: str, expected_count: Optional[int] = None, job_id: Optional[str] = None, provider: str = "gemini", model_name: Optional[str] = None, api_key: Optional[str] = None):
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        # Configure Provider & Model
        if provider == "openai":
            client = OpenAI(api_key=api_key) if api_key else self.openai_client
            active_model = model_name or "gpt-4o"
            if active_model.startswith("models/"):
                active_model = active_model.replace("models/", "")
            
            if not client:
                await update_status(0, "ERROR_OPENAI_NOT_CONFIGURED")
                return {"error": "OpenAI client not configured. Check OPENAI_API_KEY in .env"}
        else:
            # Gemini Initialization (using new SDK Client)
            active_model = model_name or self.active_gemini_model
            if api_key:
                # Use per-request key
                gemini_client = genai.Client(api_key=api_key)
            else:
                gemini_client = self.gemini_client
            
            # The actual call will use gemini_client.aio.models.generate_content
            # We don't need to create a model object anymore.

        # Helper to update progress
        async def update_status(count: int, step: str, error: str = None):
            if job_id:
                try:
                    update_fields = {
                        "count": count, 
                        "step": step, 
                        "total": expected_count, 
                        "hash": text_hash,
                        "model": active_model,
                        "provider": provider,
                        "key_idx": self.current_key_idx if provider == "gemini" and not api_key else -1,
                        "partial_houses": all_houses[-20:] # Keep last few houses for preview/status
                    }
                    if error:
                        update_fields["last_error"] = error
                        
                    await self.mongo_service.db.job_status.update_one(
                        {"job_id": job_id},
                        {"$set": update_fields},
                        upsert=True
                    )
                except Exception as e:
                    print(f"Failed to update status: {e}")

        try:
            cached_data = await self.mongo_service.get_cache(text_hash)
            if cached_data:
                print(f"Cache hit from MongoDB for hash {text_hash}")
                await update_status(len(cached_data.get("houses", [])), "COMPLETED")
                return cached_data
        except Exception as e:
            print(f"Error reading mongo cache: {e}")

        # --- Optimized Chunking for Rate Limits ---
        # Larger chunks = fewer requests. 
        # Gemini Flash supports 1M context, so 10k-20k is very safe and efficient for parsing.
        chunks = self._chunk_text(text)

        print(f"Total text length: {len(text)}. Chunked into {len(chunks)} fragments for rate-limit safety.")
        
        # --- Retry Loop for Expected Count ---
        max_retries = 2
        retry_count = 0
        final_houses = []
        final_title = ""
        
        import asyncio

        while retry_count < max_retries:
            all_houses = []
            seen_keys = set()
            
            for idx, chunk_text in enumerate(chunks):
                print(f"Processing Chunk {idx+1}/{len(chunks)} (Attempt {retry_count+1})...")
                
                # Dynamic hint for retries
                retry_hint = ""
                if retry_count > 0:
                    retry_hint = f"\n[RETRY HINT] Previous attempt only found {len(final_houses)} items but we expect {expected_count}. BE EVEN MORE EXHAUSTIVE. DO NOT MISS ANY ROWS."

                prompt = f"""
                [EXTRACTOR MODE: MECHANICAL & EXHAUSTIVE]
                You are a data extraction robot. Your purpose is FULL DATA RECALL.{retry_hint}
                
                [INPUT FORMAT] 
                The text below contains CSV-formatted tables (bounded by [TABLE START (CSV)]) and layout-preserved text from an official housing announcement PDF.
                
                [CRITICAL INSTRUCTIONS]
                1. ANALYZE every row in the CSV tables.
                2. Extract EVERY SINGLE housing unit/item mentioned.
                3. DO NOT SUMMARIZE multiple items into one.
                4. DO NOT SKIP ANY ROWS.
                5. If a row mentions a "complex name" (단지명) and "house type" (주택형/전용면적), it IS a record.
                6. Extract "deposit" (임대보증금) and "monthly_rent" (월임대료) as numbers in "만원" units.
                7. Return ONLY a valid JSON object.

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
                
                model_switch_count = 0
                max_switches = len(self.available_models)

                # Rate-limit aware call with 429 handling
                for call_retry in range(5): # Increase retries for model switching
                    try:
                        await update_status(len(all_houses), f"AI_ANALYZING_CHUNK_{idx+1}")
                        
                        if provider == "openai":
                            # OpenAI Parsing
                            response = client.chat.completions.create(
                                model=active_model,
                                messages=[{"role": "user", "content": prompt}],
                                response_format={ "type": "json_object" },
                                temperature=0.2 if retry_count > 0 else 0.0
                            )
                            response_text = response.choices[0].message.content
                        else:
                            # Gemini Parsing
                            response = await gemini_client.aio.models.generate_content(
                                model=active_model,
                                contents=prompt,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    temperature=0.2 if retry_count > 0 else 0.0
                                )
                            )
                            response_text = response.text
                        
                        parsed = json.loads(response_text)
                        houses = parsed.get("houses", [])
                        
                        for h in houses:
                            h_key = f"{h.get('name')}-{h.get('address')}-{h.get('house_type')}-{h.get('deposit')}"
                            if h_key not in seen_keys:
                                all_houses.append(h)
                                seen_keys.add(h_key)
                        
                        if not final_title: final_title = parsed.get("announcement_title", "")
                        
                        # Success - wait a bit to prevent 429 on next chunk
                        await asyncio.sleep(4) 
                        break

                    except Exception as e:
                        error_msg = str(e).lower()
                        
                        # OpenAI specific error handling (simplified)
                        if provider == "openai":
                            if "429" in error_msg:
                                wait_time = 30 + (call_retry * 15)
                                print(f"OpenAI Rate limited. Waiting {wait_time}s...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                print(f"OpenAI Error: {e}")
                                await update_status(len(all_houses), f"ERROR_CHUNK_{idx+1}", error=str(e))
                                break

                        # Case 1: Model not found (404) - Gemini
                        if "404" in error_msg:
                            model_switch_count += 1
                            if model_switch_count >= max_switches:
                                # Try switching API keys before giving up
                                if self._switch_key():
                                    model_switch_count = 0 
                                    await update_status(len(all_houses), f"KEY_SWITCHED")
                                    continue
                                
                                print(f"All models & keys returned 404 for chunk {idx+1}. Skipping.")
                                await update_status(len(all_houses), f"ERROR_ALL_MODELS_404_CHUNK_{idx+1}")
                                break
                                
                            new_model = self._switch_model(remove_current=True)
                            active_model = new_model
                            print(f"Model not found. Switched to {new_model}")
                            await update_status(len(all_houses), f"MODEL_NOT_FOUND_SWITCHING_TO_{new_model}")
                            await asyncio.sleep(2)
                            continue

                        # Case 2: Rate limit or Quota (429)
                        if "429" in error_msg:
                            # If it's a quota/limit error, try switching models/keys
                            if "quota" in error_msg or "limit" in error_msg or "exceeded" in error_msg:
                                model_switch_count += 1
                                if model_switch_count >= max_switches:
                                    if self._switch_key():
                                        model_switch_count = 0
                                        await update_status(len(all_houses), f"KEY_SWITCHED_DUE_TO_QUOTA")
                                        continue
                                    
                                new_model = self._switch_model()
                                print(f"Quota exceeded. Switched to {new_model}")
                                await update_status(len(all_houses), f"QUOTA_EXCEEDED_SWITCHING_TO_{new_model}")
                                await asyncio.sleep(5) 
                                continue
                            
                            # General rate limit (RPM)
                            wait_time = 45 + (call_retry * 20)
                            print(f"Rate limited (429). Waiting {wait_time}s...")
                            await update_status(len(all_houses), f"RATE_LIMITED_WAITING_{wait_time}S")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            print(f"Error in Chunk {idx+1}: {e}")
                            await update_status(len(all_houses), f"ERROR_CHUNK_{idx+1}", error=str(e))
                            break

            final_houses = all_houses
            
            # Check if we should retry
            if expected_count and len(final_houses) < (expected_count * 0.95):
                retry_count += 1
                print(f"Count mismatch: Got {len(final_houses)}, Expected {expected_count}. Retrying ({retry_count}/{max_retries})...")
                await asyncio.sleep(10) # Cooldown between global retries
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
            await update_status(len(valid_houses), "COMPLETED")
            print(f"FINAL RESULT: {len(valid_houses)} items stored.")
        except Exception as e:
            print(f"Cache write error: {e}")
            
        return final_result
