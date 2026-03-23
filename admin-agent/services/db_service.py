import asyncpg
import os
from typing import Optional, List

class DBService:
    def __init__(self):
        self.dsn = os.getenv("POSTGRES_DSN", "postgresql://housing_user:housing_password@127.0.0.1:5433/housing_db")
        self.pool = None

    async def init_pool(self):
        import asyncio
        # Try both 127.0.0.1 and localhost for robustness on Mac/Developer environments
        dsns_to_try = [self.dsn]
        if "127.0.0.1" in self.dsn:
            dsns_to_try.append(self.dsn.replace("127.0.0.1", "localhost"))
        elif "localhost" in self.dsn:
            dsns_to_try.append(self.dsn.replace("localhost", "127.0.0.1"))

        for i in range(10):
            for dsn in dsns_to_try:
                try:
                    self.pool = await asyncpg.create_pool(dsn)
                    print(f"Database (Postgres) connected gracefully in Parser Agent using {dsn}")
                    return
                except Exception:
                    continue
            
            print(f"Waiting for Postgres to initialize... ({i+1}/10)")
            await asyncio.sleep(2)
        raise Exception(f"Could not connect to Database after 10 retries. Tried: {dsns_to_try}")

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
