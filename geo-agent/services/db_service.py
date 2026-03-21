import asyncpg
import os
from typing import Optional

class DBService:
    def __init__(self):
        self.dsn = os.getenv("POSTGRES_DSN", "postgresql://housing_user:housing_password@localhost:5432/housing_db")
        self.pool = None

    async def init_pool(self):
        import asyncio
        for i in range(10):
            try:
                self.pool = await asyncpg.create_pool(self.dsn)
                print("Database connected gracefully")
                break
            except Exception as e:
                print(f"Waiting for Postgres to initialize... ({i+1}/10) - {e}")
                await asyncio.sleep(2)
        raise Exception("Could not connect to Database after 10 retries.")
        await self._init_schema()

    async def close_pool(self):
        if self.pool:
            await self.pool.close()

    async def _init_schema(self):
        # Initialize PostGIS extension and tables
        async with self.pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            
            # Stations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    location GEOMETRY(Point, 4326)
                );
            """)
            
            # Insert a dummy station for testing (Gangnam Station)
            await conn.execute("""
                INSERT INTO stations (name, location)
                SELECT '강남역', ST_SetSRID(ST_MakePoint(127.0276, 37.4979), 4326)
                WHERE NOT EXISTS (SELECT 1 FROM stations WHERE name = '강남역');
            """)

            # Location Cache Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS location_cache (
                    address VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255),
                    lat FLOAT,
                    lng FLOAT,
                    nearest_station VARCHAR(100),
                    distance_meters INTEGER,
                    walking_time_mins INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Enriched Housing Data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS housing_data (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255),
                    address TEXT,
                    house_type VARCHAR(100),
                    deposit INTEGER,
                    monthly_rent INTEGER,
                    lat FLOAT,
                    lng FLOAT,
                    nearest_station VARCHAR(100),
                    distance_meters INTEGER,
                    walking_time_mins INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    async def find_nearest_station(self, lat: float, lng: float) -> tuple[Optional[str], int]:
        """Returns (station_name, distance_in_meters). Walking time can be approximated later."""
        async with self.pool.acquire() as conn:
            # Using ST_DistanceSphere for approximate distance in meters
            row = await conn.fetchrow("""
                SELECT name, 
                       ST_DistanceSphere(location, ST_SetSRID(ST_MakePoint($1, $2), 4326)) as dist_meters
                FROM stations
                ORDER BY location <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
                LIMIT 1;
            """, lng, lat)

            if row:
                return row['name'], int(row['dist_meters'])
            return None, 0

    async def get_cached_location(self, address: str) -> Optional[dict]:
        """Returns cached location data for a given address if it exists."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT address, name, lat, lng, nearest_station, distance_meters, walking_time_mins
                FROM location_cache
                WHERE address = $1;
            """, address)
            
            if row:
                return dict(row)
            return None

    async def save_cached_location(self, data_dict: dict):
        """Saves API/DB computed geodata to the location cache table."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO location_cache (
                    address, name, lat, lng, nearest_station, distance_meters, walking_time_mins
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7
                ) ON CONFLICT (address) DO UPDATE SET
                    name = EXCLUDED.name,
                    lat = EXCLUDED.lat,
                    lng = EXCLUDED.lng,
                    nearest_station = EXCLUDED.nearest_station,
                    distance_meters = EXCLUDED.distance_meters,
                    walking_time_mins = EXCLUDED.walking_time_mins;
            """,
            data_dict.get('address'), data_dict.get('name'), 
            data_dict.get('lat'), data_dict.get('lng'),
            data_dict.get('nearest_station'), data_dict.get('distance_meters'), data_dict.get('walking_time_mins'))

    async def save_enriched_data(self, data_dict: dict):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO housing_data (
                    id, name, address, house_type, deposit, monthly_rent,
                    lat, lng, nearest_station, distance_meters, walking_time_mins
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
                ) ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    nearest_station = EXCLUDED.nearest_station,
                    distance_meters = EXCLUDED.distance_meters,
                    walking_time_mins = EXCLUDED.walking_time_mins;
            """,
            data_dict.get('id'), data_dict.get('name'), data_dict.get('address'), 
            data_dict.get('house_type'), data_dict.get('deposit'), data_dict.get('monthly_rent'),
            data_dict.get('lat'), data_dict.get('lng'), 
            data_dict.get('nearest_station'), data_dict.get('distance_meters'), data_dict.get('walking_time_mins'))
