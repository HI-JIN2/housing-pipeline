import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional

class MongoService:
    def __init__(self):
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client.housing_db
        self.cache_collection = self.db.llm_cache
        self.announcements_collection = self.db.announcements

    async def get_cache(self, text_hash: str) -> List[Dict[str, Any]]:
        doc = await self.cache_collection.find_one({"text_hash": text_hash})
        if doc and "data" in doc:
            return doc["data"]
        return None

    async def save_cache(self, text_hash: str, data: Dict[str, Any]):
        await self.cache_collection.update_one(
            {"text_hash": text_hash},
            {"$set": {"text_hash": text_hash, "data": data}},
            upsert=True
        )

    async def save_announcement(self, announcement_data: Dict[str, Any]):
        await self.announcements_collection.insert_one(announcement_data)

    async def get_recent_announcements(self, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = self.announcements_collection.find({}, {"_id": 1, "filename": 1, "parsed_houses": 1, "announcement_title": 1, "announcement_description": 1}).sort([("_id", -1)]).limit(limit)
        results = await cursor.to_list(length=limit)
        
        summary = []
        for doc in results:
            filename = doc.get("filename", "Unknown")
            houses = doc.get("parsed_houses", [])
            house_count = len(houses)
            
            # Use the extracted announcement title if available
            title = doc.get("announcement_title") or filename
            description = doc.get("announcement_description") or ""
            
            if not doc.get("announcement_title") and house_count > 0:
                # Fallback to first house name for older records
                first_house = houses[0]
                title = first_house.get("name", filename)
                
                parts = []
                if first_house.get("house_type"):
                    parts.append(first_house.get("house_type"))
                if first_house.get("address"):
                    parts.append(first_house.get("address"))
                description = " | ".join(parts) if parts else ""
                
            summary.append({
                "id": str(doc["_id"]),
                "filename": filename,
                "title": title,
                "description": description,
                "house_count": house_count
            })
        return summary

    async def get_announcement(self, announcement_id: str) -> Optional[Dict[str, Any]]:
        from bson.objectid import ObjectId
        try:
            doc = await self.announcements_collection.find_one({"_id": ObjectId(announcement_id)})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception:
            return None
