from services.kakao_api import KakaoGeoClient
from services.db_service import DBService
from shared.models import ParsedHousingData, EnrichedHousingData

db_service = DBService()
kakao_client = KakaoGeoClient()

async def enrich_and_save(data: dict):
    # Ensure pool is initialized if not already
    if not db_service.pool:
        await db_service.init_pool()
        
    try:
        # validate input
        try:
            parsed_data = ParsedHousingData(**data)
        except Exception as ve:
            print(f"Validation Error in Geo Agent for {data.get('name')}: {ve}")
            return
            
        # Check cache first
        cached_location = await db_service.get_cached_location(parsed_data.address)
        
        if cached_location:
            print(f"Cache Hit: Used cached location for {parsed_data.address}")
            lat = cached_location['lat']
            lng = cached_location['lng']
            station_name = cached_location['nearest_station']
            distance_meters = cached_location['distance_meters']
            walking_time_mins = cached_location['walking_time_mins']
        else:
            print(f"Cache Miss: Calling Kakao API for {parsed_data.address}")
            # 1. Geocoding
            lat, lng = await kakao_client.get_coordinates(parsed_data.address)
            if not lat or not lng:
                print(f"FAILED TO GEOCODE: '{parsed_data.address}' for house '{parsed_data.name}'")
                return
                
            # 2. Nearest Station
            station_name, distance_meters = await db_service.find_nearest_station(lat, lng)
            
            if not station_name:
                station_name = "알수없음"
                distance_meters = 0
                
            # 3. Walking time approx (1.3 multiplier for MVP)
            walking_time_mins = int((distance_meters * 1.3) / 72)
            
            # Save to cache for future use
            await db_service.save_cached_location({
                "address": parsed_data.address,
                "name": parsed_data.name,
                "lat": lat,
                "lng": lng,
                "nearest_station": station_name,
                "distance_meters": distance_meters,
                "walking_time_mins": walking_time_mins
            })
        
        enriched = EnrichedHousingData(
            **data,
            lat=lat,
            lng=lng,
            nearest_station=station_name,
            distance_meters=distance_meters,
            walking_time_mins=walking_time_mins
        )
        
        # 4. Save to DB (Include announcement_id if present in data)
        enriched_dict = enriched.model_dump()
        enriched_dict['announcement_id'] = data.get('announcement_id')
        
        await db_service.save_enriched_data(enriched_dict)
        print(f"Processed and saved: {enriched.name} -> {station_name} ({distance_meters}m)")

    except Exception as e:
        print(f"Failed to process message: {e}")
