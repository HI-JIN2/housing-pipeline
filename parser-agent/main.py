from fastapi import FastAPI
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

@app.get("/")
def health_check():
    return {"status": "ok", "service": "parser-agent"}
