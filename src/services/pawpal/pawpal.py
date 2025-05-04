import secrets
import copy
from typing import List, Literal

from langchain_core.messages import SystemMessage
from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from .agentic import Agentic
from .subflows import TopicFlowClassMapping
from .schemas.config import ConfigSchema, ConfigurableSchema
from .schemas.state import SessionState, InterruptSchema
from .schemas.document import ConversationDoc
from .schemas.topic_flow import (
    TopicFlowType,
    TopicFlowNodeType,
    TopicFlowNodeMapping,
)
from .utils import PromptLoader


class AgentState(SessionState):
    selected_features: List[TopicFlowType]


class PawPal(Agentic):
    COLLECTION_NAME = "pawpal-conversation-2"

    @classmethod
    async def _start(
        cls, state: AgentState, config: ConfigSchema
    ) -> Command[Literal["randomize_features"]]:
        user_data = config["configurable"]["user"]
        messages = [
            SystemMessage(content=[{"type": "text", "text": PromptLoader().baseline}]),
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": PromptLoader().welcome_template.format(
                            user_name=user_data.get("name", ""),
                            user_gender=user_data.get("gender", ""),
                            user_age=user_data.get("age", ""),
                            user_description=user_data.get("description", ""),
                            user_language=user_data.get("language", "English"),
                        ),
                    }
                ]
            ),
        ]
        welcome_message = await cls.model.ainvoke(messages)
        return Command(
            update={
                "messages": [*messages, welcome_message],
                "from_node": "start",
                "next_node": "randomize_features",
            },
            goto="talk",
        )

    @staticmethod
    async def _talk(state: AgentState, config: ConfigSchema):
        """
        Every node that requires interruption for sending/receiving message,
        then it will be directed to this node. Provides the interruption with ease,
        not needing to worry about the interrupt side-effect or best practice to
        put it in beginning of the node.

        This node won't be included into the graph since its just the redirector.
        """
        if state.from_node == "start":
            interrupt(
                [InterruptSchema(action="speaker", message=state.messages[-1].text())]
            )
        elif state.from_node == "randomize_features":
            interrupt(
                [InterruptSchema(action="speaker", message=state.messages[-1].text())]
            )
        elif state.from_node == "check_and_save_session":
            if state.next_node == END:
                interrupt(
                    [
                        InterruptSchema(
                            action="speaker", message=state.messages[-1].text()
                        )
                    ]
                )
        return Command(goto=state.next_node)

    @classmethod
    async def _randomize_features(
        cls, state: AgentState, config: ConfigSchema
    ) -> Command[TopicFlowNodeType]:
        #  each subflow will welcome and explain the rule or straight to the stuff
        next_feature: str = secrets.choice(state.selected_features)
        next_node = TopicFlowNodeMapping[next_feature]

        user_data = config["configurable"]["user"]
        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            # """Say something fun and playful, like PawPal is drawing a surprise session from a magical mystery box. "
                            # "Build excitement with a little drumroll or silly sound effect, then reveal the session name and jump right in, """
                            f"Introduce the next session. **EXPLICITLY MENTION THE WHOLE SESSION NAME**, WHICH IS: {next_feature.replace('_', ' ').capitalize()}'"
                            "If the next session is 'talk-to-me', mention that you want to invite the child to talk freely about their interests."
                            "If the next session is 'math adventures', mention that you want to invite the child to play pretend in a given storyline and solve math questions in order to advance the story."
                            "If the next session is 'guess the sound', mention that you want to playfully challenge the child to guess the sounds played."
                            "If the next session is 'would-you-rather', mention that you want to invite the child to imagine and discuss playful scenarios."
                            "Explain the session in less than 10 words."
                            "Example:"
                            "- 'Yuk, hari ini kita mengobrol bebas dalam sesi 'Talk-To-Me!'"
                            "- 'Aku mau mengajakmu menyelesaikan teka-teki Matematika. Yuk, kita bermain Math Adventures!'"
                            "- 'Hari ini aku mau bermain Menebak Suara! Yuk kita selesaikan tantangan ini bersama!'"
                            "- 'Aku punya ide, deh... Main 'Would-You-Rather' yuk!"
                        )
                        + "\n"
                        + PromptLoader().language_template.format(
                            user_language=user_data.get("language", "English")
                        ),
                    }
                ]
            ),
        ]
        randomize_message = await cls.model.ainvoke([*state.messages, *messages])
        return Command(
            update={
                "messages": [*messages, randomize_message],
                "from_node": "randomize_features",
                "next_node": next_node,
            },
            goto="talk",
        )

    @classmethod
    async def _check_and_save_session(cls, state: AgentState, config: ConfigSchema) -> Command[Literal["randomize_features", END]]:  # type: ignore
        if len(state.sessions) < state.total_sessions:
            return Command(
                update={
                    "from_node": "check_and_save_session",
                    "next_node": "randomize_features",
                },
                goto="randomize_features",
            )

        configurable = config["configurable"]
        saved_session = ConversationDoc(
            id=configurable["thread_id"],
            device_id=configurable["device_id"],
            user=configurable["user"],
            feature_params=configurable["feature_params"],
            selected_features=state.selected_features,
            total_sessions=state.total_sessions,
            sessions=copy.deepcopy(state.sessions),
        )
        saved_session_dict = saved_session.model_dump(mode="json")
        await cls.mongodb_engine.update_doc(
            cls.COLLECTION_NAME,
            doc_id=saved_session.id,
            new_doc=saved_session_dict,
            upsert=True,
        )

        messages = [
            SystemMessage(
                content=(
                    "Generate a short, warm, and friendly goodbye message from PawPal, written entirely in the child's language. The message should include a gentle thank-you for spending time together, a note about how fun it was, and a sweet goodbye. Adjust the tone based on the child's age use playful and simple language for younger children, and a slightly more expressive, thoughtful tone for older ones. Reflect the child's personality in the message to maintain connection. The farewell should feel safe, caring, and emotionally reassuring, ending with excitement about meeting or playing again soon. Keep it short—just 2 to 3 sentences—and respond only with the message."
                    + "\n"
                    + PromptLoader().language_template.format(
                        user_language=configurable["user"].get("language", "English")
                    )
                )
            ),
        ]
        end_conversation_message = await cls.model.ainvoke([*state.messages, *messages])
        return Command(
            update={
                "messages": [*messages, end_conversation_message],
                "from_node": "check_and_save_session",
                "next_node": END,
            },
            goto="talk",
        )

    @classmethod
    def build_workflow(cls) -> CompiledStateGraph:
        builder = StateGraph(AgentState, config_schema=ConfigurableSchema)

        # Node & Subflow
        builder.add_node("start", cls._start)
        builder.add_node("talk", cls._talk)
        builder.add_node("randomize_features", cls._randomize_features)
        builder.add_node("check_and_save_session", cls._check_and_save_session)
        for flow_feature_name, flow_feature_class in TopicFlowClassMapping.items():
            _agentic_object: Agentic = flow_feature_class()
            _agentic_object.set_agentic_cls(
                model=cls.model,
                mongodb_engine=cls.mongodb_engine,
            )
            _agentic_workflow = _agentic_object.build_workflow()
            builder.add_node(TopicFlowNodeMapping[flow_feature_name], _agentic_workflow)

        # Edge
        builder.add_edge(START, "start")
        for flow_feature_node in TopicFlowNodeType.__args__:
            builder.add_edge(flow_feature_node, "check_and_save_session")

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
