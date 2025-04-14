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


class SGSessionState(SessionState):
    question: dict


class SpellingGame(Agentic):
    @staticmethod
    async def _start(state: SessionState, config: ConfigSchema):
        print("spellinggame", state, config["configurable"]["thread_id"])

    @classmethod
    def build_workflow(self) -> CompiledStateGraph:
        builder = StateGraph(
            SGSessionState, input=SessionState, config_schema=ConfigurableSchema
        )

        # Node
        builder.add_node("start", self._start)

        # Edge
        builder.add_edge(START, "start")
        builder.add_edge("start", END)

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
