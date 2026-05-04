from google import genai
from google.genai import types
from openai import AsyncOpenAI
from shared.models import ParsedHousingData
from typing import List, Optional
import os
import json
import hashlib
import logging
from services.mongo_service import MongoService

EXTRA_INFO_KEY_MAP = {
    "max_conversion_deposit": "최대전환보증금",
    "max_conversion_rent": "최대전환월세",
    "min_conversion_deposit": "최소전환보증금",
    "min_conversion_rent": "최소전환월세",
}


def normalize_extra_info_keys(extra_info):
    if not isinstance(extra_info, dict):
        return {}

    normalized = {}
    for key, value in extra_info.items():
        if not isinstance(key, str):
            normalized[key] = value
            continue
        normalized[EXTRA_INFO_KEY_MAP.get(key, key)] = value
    return normalized

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
            self.openai_client = AsyncOpenAI(api_key=self.openai_api_key)
        
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
            
        logging.info(f"📦 Context-Aware Chunking: Split {len(pages)} pages into {len(chunks)} chunks.")
        return chunks

    async def parse_housing_data(
        self,
        text: str,
        expected_count: Optional[int] = None,
        job_id: Optional[str] = None,
        provider: str = "gemini",
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        all_houses = []
        
        # Configure Provider & Model (Default values)
        active_model = model_name or self.active_gemini_model
        gemini_client = self.gemini_client
        client = self.openai_client

        # Helper to update progress - Defined FIRST to avoid NameError
        async def update_status(
            count: int,
            step: str,
            message: Optional[str] = None,
            error: Optional[str] = None,
            meta: Optional[dict] = None,
        ):
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
                        "partial_houses": all_houses[-20:]
                    }
                    if message:
                        update_fields["message"] = message
                    if meta:
                        update_fields["meta"] = meta
                    if error:
                        update_fields["last_error"] = error
                        
                    await self.mongo_service.db.job_status.update_one(
                        {"job_id": job_id},
                        {"$set": update_fields},
                        upsert=True
                    )
                except Exception as e:
                    logging.error(f"Failed to update status: {e}")

        # Initialize status record immediately
        await update_status(0, "STARTING_ANALYSIS", message="요청을 수신했습니다. LLM 분석 준비 중...")

        # Configure Provider & Model (Override if needed)
        if provider == "openai":
            client = AsyncOpenAI(api_key=api_key) if api_key else self.openai_client
            active_model = model_name or "gpt-4o"
            if active_model.startswith("models/"):
                active_model = active_model.replace("models/", "")
            
            if not client:
                await update_status(0, "ERROR_OPENAI_NOT_CONFIGURED", message="OpenAI 클라이언트가 설정되지 않았습니다.")
                return {"error": "OpenAI client not configured. Check OPENAI_API_KEY in .env"}
        else:
            if api_key:
                gemini_client = genai.Client(api_key=api_key)
            # active_model already set above

        try:
            await update_status(0, "CHECKING_CACHE", message="Mongo 캐시 조회 중...")
            cached_data = await self.mongo_service.get_cache(text_hash)
            if cached_data:
                logging.info(f"Cache hit from MongoDB for hash {text_hash}")
                await update_status(
                    len(cached_data.get("houses", [])),
                    "COMPLETED",
                    message="캐시 히트: 기존 분석 결과를 반환합니다.",
                    meta={"cache": True},
                )
                return cached_data
        except Exception as e:
            logging.error(f"Error reading mongo cache: {e}")
            await update_status(0, "CACHE_READ_ERROR", message="캐시 조회 실패. 새로 분석을 진행합니다.", error=str(e))

        # --- Optimized Chunking for Rate Limits ---
        # Larger chunks = fewer requests. 
        # Gemini Flash supports 1M context, so 10k-20k is very safe and efficient for parsing.
        await update_status(0, "CHUNKING_TEXT", message="문서 텍스트를 분석 단위로 분할 중...")
        chunks = self._chunk_text(text)

        await update_status(
            0,
            "CHUNKING_TEXT_DONE",
            message=f"텍스트 분할 완료: {len(chunks)}개 청크.",
            meta={"chunk_total": len(chunks), "text_len": len(text)},
        )

        logging.info(f"Total text length: {len(text)}. Chunked into {len(chunks)} fragments for rate-limit safety.")
        
        # --- Retry Loop for Expected Count ---
        max_retries = 2
        retry_count = 0
        final_houses = []
        final_title = ""
        
        import asyncio

        try:
            while retry_count < max_retries:
                all_houses = []
                final_title = ""
                completed_chunks = 0
                semaphore = asyncio.Semaphore(3)

                async def process_chunk_worker(idx, chunk_text):
                    nonlocal completed_chunks, final_title

                    async with semaphore:
                        logging.info(
                            f"📡 Processing Chunk {idx+1}/{len(chunks)} (Attempt {retry_count+1})..."
                        )

                        await update_status(
                            len(all_houses),
                            "CALLING_LLM",
                            message=f"LLM 호출 중: Chunk {idx+1}/{len(chunks)} (Attempt {retry_count+1})",
                            meta={
                                "chunk_idx": idx + 1,
                                "chunk_total": len(chunks),
                                "attempt": retry_count + 1,
                            },
                        )

                        retry_hint = ""
                        if retry_count > 0:
                            retry_hint = (
                                "\n[RETRY HINT] Previous attempt missed some items. "
                                "BE EVEN MORE EXHAUSTIVE. DO NOT MISS ANY ROWS."
                            )

                        prompt = f"""
                        [EXTRACTOR MODE: MECHANICAL & EXHAUSTIVE]
                        You are a data extraction robot. Your purpose is FULL DATA RECALL.{retry_hint}

                        [INPUT FORMAT]
                        The text below contains CSV-formatted tables (bounded by [TABLE START (CSV)]) and layout-preserved text from an official housing announcement PDF.

                        [CRITICAL INSTRUCTIONS]
                        1. ANALYZE every row in the CSV tables.
                        2. Extract EVERY SINGLE housing unit/item mentioned
                        3. Mandatory Fields:
                           - "index": Number corresponding to '번호'.
                           - "district": '자치구' (e.g. 성북구, 은평구).
                           - "complex_no": '단지번호'.
                           - "address": '주소'.
                           - "unit_no": '호' or '동호'.
                           - "area": '면적' or '전용면적' (as a number).
                           - "elevator": '승강기' (있음/없음 or Y/N).
                           - "deposit": '보증금' (number in 만원).
                           - "monthly_rent": '임대료' (number in 만원).
                        4. [FLEIXIBLE EXTRA INFO]: Every other column or piece of text not in mandatory list MUST be captured in "extra_info". Use the original Korean column names whenever possible. Do not invent unnecessary English keys when a Korean label exists.
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
                                await update_status(
                                    len(all_houses),
                                    "LLM_REQUEST_IN_FLIGHT",
                                    message=(
                                        f"응답 대기 중: Chunk {idx+1}/{len(chunks)} "
                                        f"(Attempt {retry_count+1}, Call {call_retry+1}/5)"
                                    ),
                                    meta={
                                        "chunk_idx": idx + 1,
                                        "chunk_total": len(chunks),
                                        "attempt": retry_count + 1,
                                        "call_retry": call_retry + 1,
                                        "model": local_model,
                                    },
                                )
                                if provider == "openai":
                                    response = await client.chat.completions.create(
                                        model=local_model,
                                        messages=[{"role": "user", "content": prompt}],
                                        response_format={"type": "json_object"},
                                        temperature=0.2 if retry_count > 0 else 0.0,
                                    )
                                    response_text = response.choices[0].message.content
                                else:
                                    response = await gemini_client.aio.models.generate_content(
                                        model=local_model,
                                        contents=prompt,
                                        config=types.GenerateContentConfig(
                                            response_mime_type="application/json",
                                            temperature=0.2 if retry_count > 0 else 0.0,
                                        ),
                                    )
                                    response_text = response.text

                                logging.info(f"✅ Chunk {idx+1} successfully extracted.")
                                parsed = json.loads(response_text)
                                chunk_houses = parsed.get("houses", [])

                                if not final_title and parsed.get("announcement_title"):
                                    final_title = parsed.get("announcement_title")

                                completed_chunks += 1
                                await update_status(
                                    len(all_houses) + len(chunk_houses),
                                    f"ANALYZED_{completed_chunks}_OF_{len(chunks)}_CHUNKS",
                                    message=(
                                        f"Chunk {idx+1}/{len(chunks)} 완료: {len(chunk_houses)}건 추출 "
                                        f"(누적 {len(all_houses) + len(chunk_houses)}건)"
                                    ),
                                    meta={
                                        "chunk_done": completed_chunks,
                                        "chunk_total": len(chunks),
                                    },
                                )

                                if provider == "gemini":
                                    await asyncio.sleep(0.5)

                                return chunk_houses

                            except Exception as e:
                                error_msg = str(e).lower()
                                logging.error(
                                    f"⚠️ Error in Chunk {idx+1} (Call {call_retry+1}): {e}"
                                )

                                await update_status(
                                    len(all_houses),
                                    "LLM_CALL_ERROR",
                                    message=(
                                        f"LLM 호출 오류: Chunk {idx+1}/{len(chunks)} "
                                        f"(Call {call_retry+1}/5)"
                                    ),
                                    error=str(e),
                                    meta={
                                        "chunk_idx": idx + 1,
                                        "chunk_total": len(chunks),
                                        "attempt": retry_count + 1,
                                        "call_retry": call_retry + 1,
                                    },
                                )

                                if "429" in error_msg:
                                    wait_time = 5 + (call_retry * 5)
                                    if "quota" in error_msg or "limit exceeded" in error_msg:
                                        if provider == "gemini":
                                            self._switch_model()
                                            local_model = self.active_gemini_model
                                            print(f"🔄 Switched to {local_model}")
                                            wait_time = 2
                                    else:
                                        print(f"RPM Limit. Waiting {wait_time}s...")

                                    await update_status(
                                        len(all_houses),
                                        "RATE_LIMIT_BACKOFF",
                                        message=(
                                            f"레이트리밋 대기: {wait_time}s "
                                            f"(Chunk {idx+1}/{len(chunks)})"
                                        ),
                                        meta={
                                            "wait_seconds": wait_time,
                                            "chunk_idx": idx + 1,
                                            "chunk_total": len(chunks),
                                        },
                                    )

                                    await asyncio.sleep(wait_time)
                                    continue

                                if "404" in error_msg or "not found" in error_msg:
                                    if provider == "gemini":
                                        await update_status(
                                            len(all_houses),
                                            "SWITCHING_MODEL",
                                            message=f"모델 오류로 전환 중: {local_model}",
                                        )
                                        local_model = self._switch_model(remove_current=True)
                                        print(f"🚫 Model not found. Switched to {local_model}")
                                        continue
                                    break

                                await asyncio.sleep(2)
                                continue

                        return []

                tasks = [process_chunk_worker(i, chunk) for i, chunk in enumerate(chunks)]
                results = await asyncio.gather(*tasks)

                for chunk_houses in results:
                    if chunk_houses:
                        all_houses.extend(chunk_houses)

                if expected_count and len(all_houses) < (expected_count * 0.95):
                    retry_count += 1
                    if len(all_houses) > len(final_houses):
                        final_houses = all_houses

                    logging.info(
                        f"Count mismatch: Got {len(all_houses)}, Expected {expected_count}. "
                        f"Retrying ({retry_count}/{max_retries})..."
                    )
                    await update_status(
                        len(final_houses),
                        f"RETRYING_ATTEMPT_{retry_count+1}",
                        message=(
                            f"누락 가능성 감지: {len(all_houses)}건 / 기대 {expected_count}건. "
                            "재시도 중..."
                        ),
                        meta={"attempt": retry_count + 1, "max_retries": max_retries},
                    )
                    await asyncio.sleep(5)
                else:
                    final_houses = all_houses
                    break

        except Exception as e:
            await update_status(
                0,
                "ERROR",
                message="LLM 분석 중 예외가 발생했습니다.",
                error=str(e),
            )
            raise

        await update_status(len(final_houses), "VALIDATING_RESULTS", message="추출 결과 검증/정규화 중...")

        valid_houses = []
        skip_count = 0
        for index, item in enumerate(final_houses):
            try:
                house_identity = f"{final_title}|{item.get('name')}|{item.get('address')}|{item.get('house_type')}|{item.get('deposit')}"
                stable_id = hashlib.md5(house_identity.encode()).hexdigest()
                # Append index to prevent ID collisions for identical units in the same building
                item["id"] = f"h-{stable_id}-{index}"
                item["extra_info"] = normalize_extra_info_keys(item.get("extra_info"))
                valid_houses.append(ParsedHousingData(**item).model_dump())
                if (index + 1) % 25 == 0:
                    await update_status(
                        len(valid_houses),
                        "VALIDATING_RESULTS",
                        message=f"검증 진행: {index+1}/{len(final_houses)} (유효 {len(valid_houses)}건)",
                        meta={"validated": index + 1, "extracted": len(final_houses)},
                    )
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
            await update_status(len(valid_houses), "CACHING_RESULT", message="Mongo 캐시에 결과 저장 중...")
            await self.mongo_service.save_cache(text_hash, final_result)
            await update_status(len(valid_houses), "COMPLETED", message="분석 완료. 프리뷰 데이터를 준비했습니다.")
            logging.info(f"FINAL RESULT: {len(valid_houses)} items stored.")
        except Exception as e:
            print(f"Cache write error: {e}")
            await update_status(len(valid_houses), "CACHE_WRITE_ERROR", message="캐시 저장 실패. 결과는 반환하지만 재사용 캐시는 없습니다.", error=str(e))
            
        return final_result
