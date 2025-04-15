from abc import ABC, abstractmethod
from typing import Optional

from uuid import UUID
from bson.objectid import ObjectId

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from ..nosql import MongoDBEngine
from .schemas.document import ConversationDoc


class Agentic(ABC):
    model: BaseChatModel
    mongodb_engine: MongoDBEngine
    COLLECTION_NAME: str

    @classmethod
    @abstractmethod
    def build_workflow(cls) -> CompiledStateGraph: ...

    async def get_agent_results(
        self, chat_id: Optional[ObjectId] = None, device_id: Optional[UUID] = None
    ) -> dict:
        result_filter = {}
        if chat_id:
            result_filter["_id"] = chat_id
        if device_id:
            result_filter["device_id"] = str(device_id)
        results = await self.mongodb_engine.get_docs(
            collection_name=self.COLLECTION_NAME, filter=result_filter
        )
        return results

    async def create_agent_conversation(self, conv_doc: ConversationDoc):
        conv_doc_dict = conv_doc.model_dump(mode="json")
        conv_doc_dict["_id"] = ObjectId(conv_doc.id)
        await self.mongodb_engine.insert_doc(
            collection_name=self.COLLECTION_NAME, doc=conv_doc_dict
        )

    @classmethod
    def set_model(cls, model: BaseChatModel):
        cls.model = model

    @classmethod
    def set_mongodb_engine(cls, mongodb_engine: MongoDBEngine):
        cls.mongodb_engine = mongodb_engine

    @classmethod
    def set_agentic_cls(
        cls, model: Optional[BaseChatModel], mongodb_engine: Optional[MongoDBEngine]
    ):
        if model:
            cls.model = model
        if mongodb_engine:
            cls.mongodb_engine = mongodb_engine
