from langgraph.types import Command
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from ..agentic import Agentic
from ..schemas.config import ConfigSchema, ConfigurableSchema
from ..schemas.state import SessionState


class GTSSessionState(SessionState):
    question: dict


class GuessTheSound(Agentic):
    COLLECTION_NAME = "guess_the_sound-topic"

    @staticmethod
    async def _start(state: SessionState, config: ConfigSchema):
        print("guessthesound", state, config["configurable"]["thread_id"])
        return Command(goto=END)

    @classmethod
    def build_workflow(cls) -> CompiledStateGraph:
        builder = StateGraph(
            GTSSessionState, input=SessionState, config_schema=ConfigurableSchema
        )

        # Node
        builder.add_node("start", cls._start)

        # Edge
        builder.add_edge(START, "start")
        builder.add_edge("start", END)

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
