from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import os
import sys
import asyncio

# Add root directory to sys.path to allow importing from shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from services.db_service import DBService
db_service = DBService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logging.info("Starting Parser Agent...")
    # Initialize DB in the background so the server starts listening immediately
    asyncio.create_task(db_service.init_pool())
    yield
    logging.info("Shutting down Parser Agent...")
    await db_service.close_pool()

app = FastAPI(title="Parser Agent (공고zip)", lifespan=lifespan)

# Instrument FastAPI for Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Direct health check to verify container is up
@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Parser Agent is running"}

from api.routes import router as api_router
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Housing Pipeline Parser Agent API"}

