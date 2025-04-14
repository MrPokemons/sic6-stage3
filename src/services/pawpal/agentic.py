from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID
from bson.objectid import ObjectId
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from .schemas import ConfigSchema
from ..nosql import MongoDBEngine


class Agentic(ABC):
    def __init__(self, mongodb_engine: MongoDBEngine, collection_name: str):
        self.mongodb_engine = mongodb_engine
        self.COLLECTION_NAME = collection_name

    @abstractmethod
    def build_workflow(self) -> CompiledStateGraph: ...

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
