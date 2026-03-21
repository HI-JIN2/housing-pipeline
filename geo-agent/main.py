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
    # Initialize DB in the background
    asyncio.create_task(db_service.init_pool())
    yield
    print("Shutting down Geo Agent...")
    await db_service.close_pool()

app = FastAPI(title="Geo Agent (공고zip)", lifespan=lifespan)

# Direct health check
@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Geo Agent is running"}

@app.get("/")
def health_check():
    return {"status": "ok", "service": "geo-agent"}

@app.post("/api/enrich")
async def enrich_data(data: dict):
    print(f"Received data for enrichment: {data.get('name')} at {data.get('address')}")
    # This replaces the Kafka consumer logic
    await enrich_and_save(data)
    return {"status": "success"}

@app.delete("/api/housing/{announcement_id}")
async def delete_housing_data(announcement_id: str):
    await db_service.delete_housing_data_by_announcement(announcement_id)
    return {"status": "success"}
