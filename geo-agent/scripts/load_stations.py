import asyncio
import asyncpg
import csv
import os
import sys

# Load shared models and db_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.db_service import DBService

async def main():
    if len(sys.argv) < 2:
        print("Usage: python load_stations.py <path_to_csv>")
        print("CSV must have columns: name, lat, lng")
        return

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    print("Initializing Database connection...")
    db = DBService()
    await db.init_pool()

    print(f"Loading stations from {csv_path}...")
    success_count = 0
    error_count = 0

    async with db.pool.acquire() as conn:
        with open(csv_path, mode='r', encoding='euc-kr') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('역명')
                lat = row.get('위도')
                lng = row.get('경도')

                if not name or not lat or not lng:
                    print(f"Skipping invalid row: {row}")
                    error_count += 1
                    continue

                try:
                    await conn.execute("""
                        INSERT INTO stations (name, location)
                        SELECT $1::VARCHAR, ST_SetSRID(ST_MakePoint($3::FLOAT, $2::FLOAT), 4326)
                        WHERE NOT EXISTS (SELECT 1 FROM stations WHERE name = $1::VARCHAR);
                    """, name, float(lat), float(lng))
                    success_count += 1
                except Exception as e:
                    print(f"Failed to insert {name}: {e}")
                    error_count += 1

    await db.close_pool()
    print(f"Done. Successfully loaded {success_count} stations. (Errors/Skipped: {error_count})")

if __name__ == "__main__":
    asyncio.run(main())
