from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from src.storage.interfaces import DocumentStore


class MongoDBDocumentStore(DocumentStore):
    def __init__(self, client: AsyncIOMotorClient, db_name: str) -> None:
        self.client = client
        self.db_name = db_name

    def _get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        return self.client[self.db_name][collection_name]

    @staticmethod
    def _convert_entity_id_to_mongo_id(document: dict) -> dict:
        if "entity_id" in document and "_id" not in document:
            document["_id"] = document.pop("entity_id")
        return document

    @staticmethod
    def _convert_mongo_id_to_entity_id(document: dict) -> dict:
        if "_id" in document:
            mongo_id = document.pop("_id")
            # Convert ObjectId to string if needed
            document["entity_id"] = str(mongo_id)
        return document

    async def create(self, collection: str, document: dict) -> str:
        coll = self._get_collection(collection)
        document = self._convert_entity_id_to_mongo_id(document)
        result = await coll.insert_one(document)
        return str(result.inserted_id)

    async def read(self, collection: str, entity_id: str) -> dict | None:
        coll = self._get_collection(collection)
        doc = await coll.find_one({"_id": entity_id})

        if doc:
            doc = self._convert_mongo_id_to_entity_id(doc)
        return doc

    async def update(self, collection: str, entity_id: str, document: dict) -> bool:
        coll = self._get_collection(collection)
        document = self._convert_entity_id_to_mongo_id(document)
        result = await coll.update_one({"_id": entity_id}, {"$set": document})
        return result.modified_count > 0

    async def delete(self, collection: str, entity_id: str) -> bool:
        coll = self._get_collection(collection)
        result = await coll.delete_one({"_id": entity_id})
        return result.deleted_count > 0

    async def find(self, collection: str, query: dict) -> list[dict]:
        coll = self._get_collection(collection)
        cursor = coll.find(query)
        docs = []
        async for doc in cursor:
            result = self._convert_mongo_id_to_entity_id(doc)
            if result:
                docs.append(result)
        return docs
