from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os
import sys

# Add root directory to sys.path to allow importing from shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from services.db_service import DBService
db_service = DBService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Parser Agent...")
    await db_service.init_pool()
    yield
    print("Shutting down Parser Agent...")
    await db_service.close_pool()

app = FastAPI(title="Parser Agent (공고zip)", lifespan=lifespan)

from api.routes import router as api_router
app.include_router(api_router, prefix="/api")

# Serve UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def health_check():
    # Redirect root to the UI
    return RedirectResponse(url="/static/index.html")

