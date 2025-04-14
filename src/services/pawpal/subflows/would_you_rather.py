from typing import Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from ..agentic import Agentic
from ..schemas import ConfigSchema, ConfigurableSchema, SessionState


class WYRSessionState(SessionState):
    question: dict


class WouldYouRather(Agentic):
    @staticmethod
    async def _start(state: SessionState, config: ConfigSchema):
        print("wouldyourather", state, config["configurable"]["thread_id"])

    def build_workflow(self) -> CompiledStateGraph:
        builder = StateGraph(
            WYRSessionState, input=SessionState, config_schema=ConfigurableSchema
        )

        # Node
        builder.add_node("start", self._start)

        # Edge
        builder.add_edge(START, "start")

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
