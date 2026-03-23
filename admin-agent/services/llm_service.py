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
        
        import logging
        if not self.api_keys:
            logging.warning("No GEMINI_API_KEY found in environment.")
        
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
            logging.info(f"🚫 Removing unsupported model: {removed}")
            if self.current_model_idx >= len(self.available_models):
                self.current_model_idx = 0
        else:
            self.current_model_idx = (self.current_model_idx + 1) % len(self.available_models)
            
        model_name = self.available_models[self.current_model_idx]
        logging.info(f"🔄 Switching model to: {model_name}")
        self.active_gemini_model = model_name
        return model_name

    def _switch_key(self):
        if not self.api_keys or len(self.api_keys) <= 1:
            logging.warning("⚠️ No more keys to switch to.")
            return False
            
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        new_key = self.api_keys[self.current_key_idx]
        logging.info(f"🔑 Switching API Key to index {self.current_key_idx} (Ends in ...{new_key[-4:]})")
        
        self.gemini_client = genai.Client(api_key=new_key)
        self.current_model_idx = 0
        self.active_gemini_model = self.available_models[0]
        return True

    def _chunk_text(self, text: str, max_chunk_size: int = 30000) -> List[str]:
        """
        Group pages into chunks until max_chunk_size is reached.
        This preserves page-level context and avoids cutting rows/tables in half.
        """
        import re
        # Split by page marker: --- PAGE N ---
        pages = re.split(r'(?=--- PAGE \d+ ---)', text)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for page in pages:
            if not page.strip(): continue
            
            page_size = len(page)
            # If a single page is bigger than max_chunk_size, we have to split it (rare but possible)
            if page_size > max_chunk_size:
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Split huge page by character (fallback)
                for i in range(0, page_size, max_chunk_size):
                    chunks.append(page[i:i + max_chunk_size])
                continue

            if current_size + page_size > max_chunk_size:
                chunks.append("".join(current_chunk))
                current_chunk = [page]
                current_size = page_size
            else:
                current_chunk.append(page)
                current_size += page_size
        
        if current_chunk:
            chunks.append("".join(current_chunk))
            
        import logging
        logging.info(f"📦 Context-Aware Chunking: Split {len(pages)} pages into {len(chunks)} chunks.")
        return chunks

    async def parse_housing_data(self, text: str, expected_count: Optional[int] = None, job_id: Optional[str] = None, provider: str = "gemini", model_name: Optional[str] = None, api_key: Optional[str] = None):
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        # Configure Provider & Model (Default values)
        active_model = model_name or self.active_gemini_model
        gemini_client = self.gemini_client
        client = self.openai_client

        # Helper to update progress - Defined FIRST to avoid NameError
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
                        "partial_houses": all_houses[-20:] if 'all_houses' in locals() else []
                    }
                    if error:
                        update_fields["last_error"] = error
                        
                    await self.mongo_service.db.job_status.update_one(
                        {"job_id": job_id},
                        {"$set": update_fields},
                        upsert=True
                    )
                except Exception as e:
                    import logging
                    logging.error(f"Failed to update status: {e}")

        # Initialize status record immediately
        await update_status(0, "STARTING_ANALYSIS")

        # Configure Provider & Model (Override if needed)
        if provider == "openai":
            client = OpenAI(api_key=api_key) if api_key else self.openai_client
            active_model = model_name or "gpt-4o"
            if active_model.startswith("models/"):
                active_model = active_model.replace("models/", "")
            
            if not client:
                await update_status(0, "ERROR_OPENAI_NOT_CONFIGURED")
                return {"error": "OpenAI client not configured. Check OPENAI_API_KEY in .env"}
        else:
            if api_key:
                gemini_client = genai.Client(api_key=api_key)
            # active_model already set above

        try:
            cached_data = await self.mongo_service.get_cache(text_hash)
            if cached_data:
                import logging
                logging.info(f"Cache hit from MongoDB for hash {text_hash}")
                await update_status(len(cached_data.get("houses", [])), "COMPLETED")
                return cached_data
        except Exception as e:
            import logging
            logging.error(f"Error reading mongo cache: {e}")

        # --- Optimized Chunking for Rate Limits ---
        # Larger chunks = fewer requests. 
        # Gemini Flash supports 1M context, so 10k-20k is very safe and efficient for parsing.
        chunks = self._chunk_text(text)

        logging.info(f"Total text length: {len(text)}. Chunked into {len(chunks)} fragments for rate-limit safety.")
        
        # --- Retry Loop for Expected Count ---
        max_retries = 2
        retry_count = 0
        final_houses = []
        final_title = ""
        
        import asyncio

        while retry_count < max_retries:
            all_houses = []
            final_title = ""
            completed_chunks = 0
            semaphore = asyncio.Semaphore(3)

            async def process_chunk_worker(idx, chunk_text):
                nonlocal completed_chunks, final_title
                
                async with semaphore:
                    logging.info(f"📡 Processing Chunk {idx+1}/{len(chunks)} (Attempt {retry_count+1})...")
                    
                    retry_hint = ""
                    if retry_count > 0:
                        retry_hint = f"\n[RETRY HINT] Previous attempt missed some items. BE EVEN MORE EXHAUSTIVE. DO NOT MISS ANY ROWS."

                    prompt = f"""
                    [EXTRACTOR MODE: MECHANICAL & EXHAUSTIVE]
                    You are a data extraction robot. Your purpose is FULL DATA RECALL.{retry_hint}
                    
                    [INPUT FORMAT] 
                    The text below contains CSV-formatted tables (bounded by [TABLE START (CSV)]) and layout-preserved text from an official housing announcement PDF.
                    
                    [CRITICAL INSTRUCTIONS]
                    1. ANALYZE every row in the CSV tables.
                    2. Extract EVERY SINGLE housing unit/item mentioned                    3. Mandatory Fields:
                       - "index": Number corresponding to '번호'.
                       - "district": '자치구' (e.g. 성북구, 은평구).
                       - "complex_no": '단지번호'.
                       - "address": '주소'.
                       - "unit_no": '호' or '동호'.
                       - "area": '면적' or '전용면적' (as a number).
                       - "elevator": '승강기' (있음/없음 or Y/N).
                       - "deposit": '보증금' (number in 만원).
                       - "monthly_rent": '임대료' (number in 만원).
                    4. [FLEIXIBLE EXTRA INFO]: Every other column or piece of text not in mandatory list MUST be captured in "extra_info" using descriptive keys. Use MongoDB's schema flexibility - capture everything you find in the PDF.
                    5. Return ONLY a valid JSON object.

                    [JSON SCHEMA]
                    {{
                        "announcement_title": "string",
                        "houses": [
                            {{
                                "index": number,
                                "district": "string",
                                "complex_no": "string",
                                "address": "string", 
                                "unit_no": "string",
                                "area": number,
                                "house_type": "string",
                                "elevator": "string",
                                "deposit": number,
                                "monthly_rent": number,
                                "extra_info": {{ "any_other_column": "value" }}
                            }}
                        ]
                    }}
                    
                    [INPUT TEXT]
                    {chunk_text}
                    """
                    
                    local_model = active_model
                    for call_retry in range(5):
                        try:
                            if provider == "openai":
                                response = client.chat.completions.create(
                                    model=local_model,
                                    messages=[{"role": "user", "content": prompt}],
                                    response_format={ "type": "json_object" },
                                    temperature=0.2 if retry_count > 0 else 0.0
                                )
                                response_text = response.choices[0].message.content
                            else:
                                response = await gemini_client.aio.models.generate_content(
                                    model=local_model,
                                    contents=prompt,
                                    config=types.GenerateContentConfig(
                                        response_mime_type="application/json",
                                        temperature=0.2 if retry_count > 0 else 0.0
                                    )
                                )
                                response_text = response.text
                            
                            logging.info(f"✅ Chunk {idx+1} successfully extracted.")
                            parsed = json.loads(response_text)
                            chunk_houses = parsed.get("houses", [])
                            
                            if not final_title and parsed.get("announcement_title"):
                                final_title = parsed.get("announcement_title")
                            
                            completed_chunks += 1
                            await update_status(len(all_houses) + len(chunk_houses), f"ANALYZED_{completed_chunks}_OF_{len(chunks)}_CHUNKS")
                            
                            if provider == "gemini":
                                await asyncio.sleep(0.5)
                                
                            return chunk_houses

                        except Exception as e:
                            error_msg = str(e).lower()
                            logging.error(f"⚠️ Error in Chunk {idx+1} (Call {call_retry+1}): {e}")
                            
                            if "429" in error_msg:
                                # Rate Limit handling
                                wait_time = 5 + (call_retry * 5)
                                if "quota" in error_msg or "limit exceeded" in error_msg:
                                    # Hard quota limit, switch something
                                    if provider == "gemini":
                                        self._switch_model()
                                        local_model = self.active_gemini_model
                                        print(f"🔄 Switched to {local_model}")
                                        wait_time = 2
                                else:
                                    print(f"RPM Limit. Waiting {wait_time}s...")
                                
                                await asyncio.sleep(wait_time)
                                continue
                            
                            elif "404" in error_msg or "not found" in error_msg:
                                if provider == "gemini":
                                    local_model = self._switch_model(remove_current=True)
                                    print(f"🚫 Model not found. Switched to {local_model}")
                                    continue
                                else:
                                    break
                            else:
                                # Other errors
                                await asyncio.sleep(2)
                                continue
                    return []

            # Execute all chunks as concurrent tasks
            tasks = [process_chunk_worker(i, chunk) for i, chunk in enumerate(chunks)]
            results = await asyncio.gather(*tasks)
            
            # Aggregate results
            for chunk_houses in results:
                if chunk_houses:
                    all_houses.extend(chunk_houses)

            # Check if we should retry
            if expected_count and len(all_houses) < (expected_count * 0.95):
                retry_count += 1
                if len(all_houses) > len(final_houses):
                    final_houses = all_houses # Keep the best found so far
                
                logging.info(f"Count mismatch: Got {len(all_houses)}, Expected {expected_count}. Retrying ({retry_count}/{max_retries})...")
                await update_status(len(final_houses), f"RETRYING_ATTEMPT_{retry_count+1}")
                await asyncio.sleep(5) 
            else:
                final_houses = all_houses
                break

        valid_houses = []
        skip_count = 0
        for index, item in enumerate(final_houses):
            try:
                house_identity = f"{final_title}|{item.get('name')}|{item.get('address')}|{item.get('house_type')}|{item.get('deposit')}"
                stable_id = hashlib.md5(house_identity.encode()).hexdigest()
                # Append index to prevent ID collisions for identical units in the same building
                item["id"] = f"h-{stable_id}-{index}"
                valid_houses.append(ParsedHousingData(**item).model_dump())
            except Exception as e:
                skip_count += 1
                if skip_count <= 5:
                    print(f"⚠️ Validation skipped for item {index}: {e}")
                elif skip_count == 6:
                    print("⚠️ More validation errors suppressed...")
        
        if skip_count > 0:
            print(f"❌ Total {skip_count} items skipped due to validation errors.")

        final_result = {
            "announcement_title": final_title,
            "announcement_description": f"Extracted via Nuclear Micro-chunking. Total items: {len(valid_houses)}",
            "houses": valid_houses
        }

        # Save to MongoDB cache
        try:
            await self.mongo_service.save_cache(text_hash, final_result)
            await update_status(len(valid_houses), "COMPLETED")
            logging.info(f"FINAL RESULT: {len(valid_houses)} items stored.")
        except Exception as e:
            print(f"Cache write error: {e}")
            
        return final_result
