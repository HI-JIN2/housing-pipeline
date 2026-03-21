import json
import os
from aiokafka import AIOKafkaConsumer

from services.kakao_api import KakaoGeoClient
from services.db_service import DBService
from shared.models import ParsedHousingData, EnrichedHousingData

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

consumer = None
db_service = DBService()
kakao_client = KakaoGeoClient()

async def start_consumer():
    global consumer
    await db_service.init_pool()
    
    # We delay consumer import/start to let Kafka boot if needed
    consumer = AIOKafkaConsumer(
        "parsed_data",
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="geo_enricher_group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset="earliest"
    )
    
    await consumer.start()
    print("Kafka Consumer started listening to parsed_data")
    try:
        async for msg in consumer:
            print(f"Received message: {msg.value}")
            await process_message(msg.value)
    finally:
        await consumer.stop()

async def stop_consumer():
    if consumer:
        await consumer.stop()
    await db_service.close_pool()

async def process_message(data: dict):
    try:
        # validate input
        parsed_data = ParsedHousingData(**data)
        
        # 1. Geocoding
        lat, lng = await kakao_client.get_coordinates(parsed_data.address)
        if not lat or not lng:
            print(f"Could not geocode address: {parsed_data.address}")
            return
            
        # 2. Nearest Station
        station_name, distance_meters = await db_service.find_nearest_station(lat, lng)
        
        if not station_name:
            station_name = "알수없음"
            distance_meters = 0
            
        # 3. Walking time approx (1.3 multiplier for MVP)
        # Average walking speed is about 1.2 meters/second (approx 72 meters/minute)
        # So 400m * 1.3 / 72 ≈ 7 minutes
        walking_time_mins = int((distance_meters * 1.3) / 72)
        
        enriched = EnrichedHousingData(
            **data,
            lat=lat,
            lng=lng,
            nearest_station=station_name,
            distance_meters=distance_meters,
            walking_time_mins=walking_time_mins
        )
        
        # 4. Save to DB
        await db_service.save_enriched_data(enriched.model_dump())
        print(f"Processed and saved: {enriched.name} -> {station_name} ({distance_meters}m)")

        # Optional: Producer can also sink this to 'enriched_data' topic if needed for Step 4
        
    except Exception as e:
        print(f"Failed to process message: {e}")
