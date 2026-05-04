from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

# This allows importing from the shared/ directory
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load env from repo root (.env). start_all.sh runs from subdirs.
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize shared services if needed
    print("Admin Agent starting up...")
    yield
    # Shutdown
    print("Admin Agent shutting down...")

app = FastAPI(title="Housing Admin Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Add Prometheus metrics
Instrumentator().instrument(app).expose(app)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "admin-agent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
