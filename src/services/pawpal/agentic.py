from abc import ABC, abstractmethod
from typing import Any, Optional

from uuid import UUID
from bson.objectid import ObjectId

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from .schemas import ConfigSchema
from ..nosql import MongoDBEngine


class Agentic(ABC):
    model: BaseChatModel
    mongodb_engine: MongoDBEngine
    collection_name: str

    @classmethod
    @abstractmethod
    def build_workflow(cls) -> CompiledStateGraph: ...

    @staticmethod
    async def resume_workflow(
        workflow: CompiledStateGraph, value: Any, config: ConfigSchema
    ):
        resume_command = Command(resume=value)
        return await workflow.ainvoke(resume_command, config=config)

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

    @classmethod
    def set_model(cls, model: BaseChatModel):
        cls.model = model

    @classmethod
    def set_mongodb_engine(cls, mongodb_engine: MongoDBEngine):
        cls.mongodb_engine = mongodb_engine

    @classmethod
    def set_collection_name(cls, collection_name: str):
        cls.collection_name = collection_name

    @classmethod
    def set_agentic_cls(cls, model: BaseChatModel, mongodb_engine: MongoDBEngine, collection_name: str):
        cls.model = model
        cls.mongodb_engine = mongodb_engine
        cls.collection_name = collection_name
