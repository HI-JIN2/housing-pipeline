from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os
import sys

# Add root directory to sys.path to allow importing from shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.kafka_client import KafkaProducerClient
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
kafka_producer = KafkaProducerClient(KAFKA_BOOTSTRAP_SERVERS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Parser Agent...")
    await kafka_producer.start()
    yield
    print("Shutting down Parser Agent...")
    await kafka_producer.stop()

app = FastAPI(title="Parser Agent (Housing Pipeline)", lifespan=lifespan)

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

