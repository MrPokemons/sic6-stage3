import secrets
from typing import List, Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from .agentic import Agentic
from .schemas import ConfigSchema, ConfigurableSchema, SessionState, InterruptSchema
from .subflows import (
    FlowFeatureType,
    FlowFeatureNodeType,
    FlowFeatureNodeMapping,
    FlowFeatureClassMapping,
)


class AgentState(SessionState):
    selected_features: List[FlowFeatureType]


class PawPal(Agentic):
    @staticmethod
    async def _start(
        state: AgentState, config: ConfigSchema
    ) -> Command[Literal["randomize_features"]]:
        messages = []  # system msg for guiding through the system
        # need to welcome the child message
        return Command(
            update={
                "messages": messages,
                "from_node": "start",
                "next_node": "randomize_features",
            },
            goto="talk",
        )

    @staticmethod
    async def _talk(state: AgentState, config: ConfigSchema):
        # just central to use interrupt without worrying reprocessing something, so don't need included into the Graph
        # this interrupt is to send the message from previous node
        # something like introduce bot himself, then lets randomize features
        if state.from_node == "start":
            interrupt(
                [InterruptSchema(action="speaker", message="send from last AI Message")]
            )
        elif state.from_node == "randomize_features":
            interrupt(
                [InterruptSchema(action="speaker", message="Are you ready here we go")]
            )
        elif state.from_node == "check_and_save_session":
            if state.next_node == END:
                # thank you for playing and have a great time
                ...
        return Command(goto=state.next_node)

    @staticmethod
    async def _randomize_features(
        state: AgentState, config: ConfigSchema
    ) -> Command[FlowFeatureNodeType]:
        #  each subflow will welcome and explain the rule or straight to the stuff
        next_feature: str = secrets.choice(state.selected_features)
        next_node = FlowFeatureNodeMapping[next_feature]
        return Command(
            update={
                "from_node": "randomize_features",
                "next_node": next_node,
            },
            goto="talk",
        )

    @staticmethod
    async def _check_and_save_session(state: AgentState, config: ConfigSchema) -> Command[Literal["randomize_features", END]]:  # type: ignore
        if len(state.sessions) >= state.total_sessions:
            # store to mongodb
            return Command(
                update={"from_node": "check_and_save_session", "next_node": END},
                goto="talk",
            )
        return Command(
            update={
                "from_node": "check_and_save_session",
                "next_node": "randomize_features",
            },
            goto="talk",
        )

    def build_workflow(self) -> CompiledStateGraph:
        builder = StateGraph(AgentState, config_schema=ConfigurableSchema)

        # Node & Subflow
        builder.add_node("start", self._start)
        builder.add_node("talk", self._talk)
        builder.add_node("randomize_features", self._randomize_features)
        builder.add_node("check_and_save_session", self._check_and_save_session)
        for flow_feature_name, flow_feature_class in FlowFeatureClassMapping.items():
            _agentic_object: Agentic = flow_feature_class(
                mongodb_engine=self.mongodb_engine,
                collection_name=flow_feature_name,
            )
            _agentic_workflow = _agentic_object.build_workflow()
            builder.add_node(
                FlowFeatureNodeMapping[flow_feature_name], _agentic_workflow
            )

        # Edge
        builder.add_edge(START, "start")
        for flow_feature_node in FlowFeatureNodeType.__args__:
            builder.add_edge(flow_feature_node, "check_and_save_session")

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
