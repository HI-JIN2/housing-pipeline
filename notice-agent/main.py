import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from api.routes import monitor_service, router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Notice Agent starting up...")
    scheduler_task = asyncio.create_task(monitor_service.run_forever())
    yield
    logging.info("Notice Agent shutting down...")
    await monitor_service.stop()
    await scheduler_task


app = FastAPI(title="Housing Notice Agent", lifespan=lifespan)

Instrumentator().instrument(app).expose(app)
app.include_router(router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "notice-agent",
        "scheduler_enabled": monitor_service.enabled,
        "crawl_interval_seconds": monitor_service.interval_seconds,
    }
