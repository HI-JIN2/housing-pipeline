import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any, Optional
import re

class MongoService:
    def __init__(self):
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        # Fail fast when DB is down to avoid hanging the API/UI.
        self.client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
            socketTimeoutMS=20000,
        )
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
        cursor = self.announcements_collection.find({}, {"_id": 1, "filename": 1, "filenames": 1, "parsed_houses": 1, "announcement_title": 1, "announcement_description": 1}).sort([("_id", -1)]).limit(limit)
        results = await cursor.to_list(length=limit)
        
        summary = []
        for doc in results:
            filenames = doc.get("filenames", [doc.get("filename", "Unknown")])
            primary_filename = filenames[0] if filenames else "Unknown"
            
            houses = doc.get("parsed_houses", [])
            house_count = len(houses)
            
            # Use the extracted announcement title if available
            title = doc.get("announcement_title") or primary_filename
            description = doc.get("announcement_description") or ""
            
            if not doc.get("announcement_title") and house_count > 0:
                # Fallback to first house name for older records
                first_house = houses[0]
                title = first_house.get("name", primary_filename)
                
                parts = []
                if first_house.get("house_type"):
                    parts.append(first_house.get("house_type"))
                if first_house.get("address"):
                    parts.append(first_house.get("address"))
                description = " | ".join(parts) if parts else ""
                
            summary.append({
                "id": str(doc["_id"]),
                "filename": primary_filename,
                "title": title,
                "description": description,
                "house_count": house_count
            })
        return summary

    def _build_search_query(self, q: Optional[str]) -> Dict[str, Any]:
        if not q:
            return {}
        safe = re.escape(q)
        rx = {"$regex": safe, "$options": "i"}
        return {
            "$or": [
                {"announcement_title": rx},
                {"announcement_description": rx},
                {"filename": rx},
                {"filenames": rx},
            ]
        }

    async def list_announcements(self, limit: int = 50, skip: int = 0, q: Optional[str] = None):
        query = self._build_search_query(q)
        total = await self.announcements_collection.count_documents(query)
        cursor = (
            self.announcements_collection
            .find(
                query,
                {
                    "_id": 1,
                    "filename": 1,
                    "filenames": 1,
                    "parsed_houses": 1,
                    "announcement_title": 1,
                    "announcement_description": 1,
                    "created_at": 1,
                },
            )
            .sort([("_id", -1)])
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)

        items = []
        for doc in docs:
            filenames = doc.get("filenames", [doc.get("filename", "Unknown")])
            primary_filename = filenames[0] if filenames else "Unknown"
            houses = doc.get("parsed_houses", [])
            house_count = len(houses)

            title = doc.get("announcement_title") or primary_filename
            description = doc.get("announcement_description") or ""
            items.append(
                {
                    "id": str(doc["_id"]),
                    "filename": primary_filename,
                    "title": title,
                    "description": description,
                    "house_count": house_count,
                    "created_at": doc.get("created_at"),
                }
            )

        return items, total

    async def get_stats(self) -> Dict[str, Any]:
        total_announcements = await self.announcements_collection.count_documents({})

        # Sum of parsed_houses lengths (aggregation to avoid pulling documents)
        total_houses = 0
        try:
            pipeline = [
                {"$project": {"hc": {"$size": {"$ifNull": ["$parsed_houses", []]}}}},
                {"$group": {"_id": None, "total": {"$sum": "$hc"}}},
            ]
            agg = self.announcements_collection.aggregate(pipeline)
            out = await agg.to_list(length=1)
            if out:
                total_houses = int(out[0].get("total", 0))
        except Exception as e:
            logging.error(f"Failed to compute total houses: {e}")

        latest = None
        try:
            latest_doc = await self.announcements_collection.find_one(
                {},
                {"_id": 1, "announcement_title": 1, "filename": 1, "filenames": 1},
                sort=[("_id", -1)],
            )
            if latest_doc:
                filenames = latest_doc.get("filenames", [latest_doc.get("filename", "Unknown")])
                primary_filename = filenames[0] if filenames else "Unknown"
                latest = {
                    "id": str(latest_doc["_id"]),
                    "title": latest_doc.get("announcement_title") or primary_filename,
                }
        except Exception as e:
            logging.error(f"Failed to get latest announcement: {e}")

        return {
            "status": "success",
            "total_announcements": total_announcements,
            "total_houses": total_houses,
            "latest": latest,
        }

    async def get_announcement(self, announcement_id: str) -> Optional[Dict[str, Any]]:
        from bson.objectid import ObjectId
        try:
            doc = await self.announcements_collection.find_one({"_id": ObjectId(announcement_id)})
            if doc:
                doc['_id'] = str(doc['_id'])
            return doc
        except Exception as e:
            logging.error(f"Failed to retrieve announcement {announcement_id}: {e}")
            return None
    async def delete_announcement(self, announcement_id: str):
        from bson.objectid import ObjectId
        try:
            await self.announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
            return True
        except Exception as e:
            logging.error(f"Failed to delete announcement {announcement_id}: {e}")
            return False
