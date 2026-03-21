from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import os
import sys

# Load shared models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

from kafka_module.consumer import start_consumer, stop_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Geo Agent...")
    consumer_task = asyncio.create_task(start_consumer())
    yield
    print("Shutting down Geo Agent...")
    await stop_consumer()
    # Cancel the consumer background task gracefully if needed
    consumer_task.cancel()

app = FastAPI(title="Geo Agent (Housing Pipeline)", lifespan=lifespan)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "geo-agent"}
