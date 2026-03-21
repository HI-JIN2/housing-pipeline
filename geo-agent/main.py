from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import os
import sys

# Load shared models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

from services.enrich_service import enrich_and_save, db_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Geo Agent...")
    await db_service.init_pool()
    yield
    print("Shutting down Geo Agent...")
    await db_service.close_pool()

app = FastAPI(title="Geo Agent (Housing Pipeline)", lifespan=lifespan)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "geo-agent"}

@app.post("/api/enrich")
async def enrich_data(data: dict):
    # This replaces the Kafka consumer logic
    await enrich_and_save(data)
    return {"status": "success"}
