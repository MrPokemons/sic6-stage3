from typing import Literal
from datetime import datetime, timezone
from pydantic import Field

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from ..agentic import Agentic
from ..schemas import ConfigSchema, ConfigurableSchema, SessionState, InterruptSchema


class TTMSessionState(SessionState):
    start_datetime: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TalkToMe(Agentic):
    @staticmethod
    async def _start(
        state: TTMSessionState, config: ConfigSchema
    ) -> Command[Literal["responding"]]:
        # add the system base for more specialized prompt
        messages = []
        return Command(
            update={
                "messages": messages,
                "from_node": "start",
                "next_node": "responding",
            },
            goto="talk",
        )

    @staticmethod
    async def _talk(state: TTMSessionState, config: ConfigSchema):
        # just central to use interrupt without worrying reprocessing something, so don't need included into the Graph
        # this interrupt is to send the message from previous node
        # something like introduce bot himself, then lets randomize features
        if state.from_node == "start":
            interrupt(
                [InterruptSchema(action="speaker", message="send from last AI Message")]
            )
        elif state.from_node == "responding":
            interrupt(
                [InterruptSchema(action="speaker", message="Are you ready here we go")]
            )
        elif state.from_node == "check_session":
            if state.next_node == END:
                # thank you for playing and have a great time
                ...
        return Command(goto=state.next_node)

    @staticmethod
    async def _responding(
        state: TTMSessionState, config: ConfigSchema
    ) -> Command[Literal["check_session"]]:
        messages = []
        return Command(
            update={
                "messages": messages,
                "from_node": "responding",
                "next_node": "check_session",
            },
            goto="talk",
        )

    @staticmethod
    async def _check_session(state: TTMSessionState, config: ConfigSchema) -> Command[Literal["listen", END]]:  # type: ignore
        if (datetime.now(timezone.utc) - state.start_datetime).seconds >= config[
            "configurable"
        ]["feature_params"]["talk_to_me"]["duration"]:
            # model answer again, telling its over
            # model summarize, then append to session in the state
            return Command(
                update={"from_node": "check_session", "next_node": END}, goto="talk"
            )
        return Command(
            update={"from_node": "check_session", "next_node": "listen"}, goto="talk"
        )

    @staticmethod
    async def _listen(
        state: TTMSessionState, config: ConfigSchema
    ) -> Command[Literal["responding"]]:
        # just interrupt to listen the user respond, then update the message with human message
        user_message = interrupt([InterruptSchema(action="microphone")])
        messages = [HumanMessage(content=[{"type": "text", "text": user_message}])]
        return Command(
            update={
                "messages": messages,
                "from_node": "listen",
                "next_node": "responding",
            },
            goto="responding",
        )

    @classmethod
    def build_workflow(self) -> CompiledStateGraph:
        builder = StateGraph(TTMSessionState, config_schema=ConfigurableSchema)

        # Node
        builder.add_node("start", self._start)
        builder.add_node("talk", self._talk)
        builder.add_node("responding", self._responding)
        builder.add_node("check_session", self._check_session)
        builder.add_node("listen", self._listen)

        # Edge
        builder.add_edge(START, "start")

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
