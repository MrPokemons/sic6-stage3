from typing import Tuple, Annotated, Optional, List
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


class MongoDBEngine:
    def __init__(
        self,
        uri: str = None,
        db_name: str = None,
    ):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

    async def get_doc(
        self, collection_name: str, filter: Optional[dict] = None
    ) -> Optional[dict]:
        collection = self.db[collection_name]
        doc = await collection.find_one(filter)
        if isinstance(doc, dict):
            doc["id"] = str(doc.pop("_id"))
        return doc

    async def get_docs(
        self, collection_name: str, filter: Optional[dict] = None
    ) -> List[dict]:
        collection = self.db[collection_name]
        docs = []
        async for doc in collection.find(filter):
            if isinstance(doc, dict):
                doc["id"] = str(doc.pop("_id"))
            docs.append(doc)
        return docs

    async def insert_doc(self, collection_name: str, doc: dict):
        collection = self.db[collection_name]
        id = await collection.insert_one(doc).inserted_id
        return str(id)

    async def update_doc(
        self, collection_name: str, doc_id: str, new_doc: dict, *, upsert=False
    ) -> Tuple[Annotated[int, "matched count"], Annotated[int, "modified count"]]:
        collection = self.db[collection_name]
        update_result = await collection.update_one(
            filter={"_id": ObjectId(doc_id)}, update={"$set": new_doc}, upsert=upsert
        )
        return update_result.matched_count, update_result.modified_count

    async def delete_doc(
        self, collection_name: str, doc_id: str
    ) -> Annotated[int, "deleted count"]:
        collection = self.db[collection_name]
        delete_result = await collection.delete_one(filter={"_id": ObjectId(doc_id)})
        return delete_result.deleted_count
