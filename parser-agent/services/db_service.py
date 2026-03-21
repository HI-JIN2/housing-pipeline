import asyncpg
import os
from typing import Optional, List

class DBService:
    def __init__(self):
        self.dsn = os.getenv("POSTGRES_DSN", "postgresql://housing_user:housing_password@127.0.0.1:5433/housing_db")
        self.pool = None

    async def init_pool(self):
        import asyncio
        for i in range(10):
            try:
                self.pool = await asyncpg.create_pool(self.dsn)
                print("Database (Postgres) connected gracefully in Parser Agent")
                return
            except Exception as e:
                print(f"Waiting for Postgres to initialize... ({i+1}/10) - {e}")
                await asyncio.sleep(2)
        raise Exception("Could not connect to Database after 10 retries.")

    async def close_pool(self):
        if self.pool:
            await self.pool.close()

    async def get_enriched_data_by_ids(self, ids: List[str]) -> List[dict]:
        """Fetches enriched housing data from PostgreSQL for a list of IDs."""
        if not self.pool:
            return []
            
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, address, house_type, deposit, monthly_rent,
                       lat, lng, nearest_station, distance_meters, walking_time_mins
                FROM housing_data
                WHERE id = ANY($1::varchar[])
            """, ids)
            
            return [dict(r) for r in rows]
