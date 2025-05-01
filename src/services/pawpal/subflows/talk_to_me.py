from typing import Literal
from datetime import datetime, timezone
from pydantic import Field

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

from ..agentic import Agentic
from ..schemas.config import ConfigSchema, ConfigurableSchema
from ..schemas.state import SessionState, InterruptSchema
from ..schemas.topic import TopicResults
from ..utils import prompt_loader


class TTMSessionState(SessionState):
    start_datetime: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_datetime: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TalkToMe(Agentic):
    COLLECTION_NAME = "talk_to_me-topic"

    @classmethod
    async def _start(
        cls, state: TTMSessionState, config: ConfigSchema
    ) -> Command[Literal["listening"]]:
        # add the system base for more specialized prompt
        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            'Introduce the "Talk to Me" session warmly and naturally in the child\'s language. '
                            "Invite the child to share anything on their mind—their day, their feelings, something fun, something that bothered them, "
                            "or anything at all. Be gentle, caring, and respectful. Show that you're here to listen fully, without judgment. "
                            "Make them feel safe, heard, and supported—like you're their closest friend. Keep it short, kind, and encouraging."
                        ),
                    }
                ]
            ),
            SystemMessage(
                content=[{"type": "text", "text": prompt_loader.talk_to_me.opening}]
            ),
        ]
        opening_message = await cls.model.ainvoke([*state.messages, *messages])
        state.add_session(
            session_type="talk_to_me",
            messages=[*messages, opening_message]
        )
        return Command(
            update={
                "start_datetime": datetime.now(timezone.utc),
                "modified_datetime": datetime.now(timezone.utc),
                "messages": [*messages, opening_message],
                "sessions": state.get_sessions(deep=True),
                "from_node": "start",
                "next_node": "listening",
            },
            goto="talk",
        )

    @staticmethod
    async def _talk(state: TTMSessionState, config: ConfigSchema):
        """
        Every node that requires interruption for sending/receiving message,
        then it will be directed to this node. Provides the interruption with ease,
        not needing to worry about the interrupt side-effect or best practice to
        put it in beginning of the node.

        This node won't be included into the graph since its just the redirector.
        """
        if state.from_node == "start":
            last_ai_msg = state.last_ai_message()
            if last_ai_msg is None:
                raise Exception(f"How no last ai message? {state.model_dump(mode='json')}")
            interrupt(
                [InterruptSchema(action="speaker", message=last_ai_msg.text())]
            )
        elif state.from_node == "responding":
            last_ai_msg = state.last_ai_message()
            if last_ai_msg is None:
                raise Exception(f"How no last ai message? {state.model_dump(mode='json')}")
            interrupt(
                [InterruptSchema(action="speaker", message=last_ai_msg.text())]
            )
        elif state.from_node == "check_session":
            if state.next_node == END:
                last_ai_msg = state.last_ai_message()
                if last_ai_msg is None:
                    raise Exception(f"How no last ai message? {state.model_dump(mode='json')}")
                interrupt(
                    [
                        InterruptSchema(
                            action="speaker", message=last_ai_msg.text()
                        )
                    ]
                )
        return Command(goto=state.next_node)

    @staticmethod
    async def _listening(
        state: TTMSessionState, config: ConfigSchema
    ) -> Command[Literal["responding"]]:
        _ = state.verify_last_session(session_type="talk_to_me")
        user_response: str = interrupt([InterruptSchema(action="microphone")])
        messages = [HumanMessage(content=[{"type": "text", "text": user_response}])]
        state.add_message_to_last_session(
            session_type="talk_to_me",
            messages=messages,
        )
        return Command(
            update={
                "modified_datetime": datetime.now(timezone.utc),
                "messages": messages,
                "sessions": state.get_sessions(deep=True),
                "from_node": "listening",
                "next_node": "responding",
            },
            goto="responding",
        )

    @classmethod
    async def _responding(
        cls, state: TTMSessionState, config: ConfigSchema
    ) -> Command[Literal["check_session"]]:
        _ = state.verify_last_session(session_type="talk_to_me")
        response_message = await cls.model.ainvoke(state.messages)
        state.add_message_to_last_session(
            session_type="talk_to_me",
            messages=response_message
        )
        return Command(
            update={
                "modified_datetime": datetime.now(timezone.utc),
                "messages": response_message,
                "sessions": state.get_sessions(deep=True),
                "from_node": "responding",
                "next_node": "check_session",
            },
            goto="talk",
        )

    @classmethod
    async def _check_session(cls, state: TTMSessionState, config: ConfigSchema) -> Command[Literal["listening", END]]:  # type: ignore
        last_session = state.verify_last_session(session_type="talk_to_me")

        configurable = config["configurable"]
        ongoing_duration = (datetime.now(timezone.utc) - state.start_datetime).seconds
        if ongoing_duration < configurable["feature_params"]["talk_to_me"]["duration"]:
            return Command(
                update={"from_node": "check_session", "next_node": "listening"},
                goto="talk",
            )

        messages = [
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "End the Session, while saying thank you for participating for the session."
                            + "\n"
                            + prompt_loader.language_template.format(
                                user_language=configurable["user"].get(
                                    "language", "English"
                                )
                            )
                        ),
                    }
                ]
            ),
        ]
        end_conversation_message = await cls.model.ainvoke([*state.messages, *messages])
        state.add_message_to_last_session(
            session_type="talk_to_me",
            messages=[*messages, end_conversation_message],
        )
        model_with_session_result = cls.model.with_structured_output(
            TopicResults.TalkToMeResult._Extraction
        )
        _extracted_result: TopicResults.TalkToMeResult._Extraction = await model_with_session_result.ainvoke(
            last_session.get_messages()
        )

        modified_datetime = datetime.now(timezone.utc)
        state.add_result_to_last_session(
            session_type="talk_to_me",
            result=TopicResults.TalkToMeResult(
                extraction=_extracted_result,
                start_datetime=state.start_datetime,
                modified_datetime=modified_datetime,
            )
        )
        return Command(
            update={
                "modified_datetime": modified_datetime,
                "messages": [*messages, end_conversation_message],
                "sessions": state.get_sessions(deep=True),
                "from_node": "check_session",
                "next_node": END,
            },
            goto="talk",
        )

    @classmethod
    def build_workflow(self) -> CompiledStateGraph:
        builder = StateGraph(TTMSessionState, config_schema=ConfigurableSchema)

        # Node
        builder.add_node("start", self._start)
        builder.add_node("talk", self._talk)
        builder.add_node("responding", self._responding)
        builder.add_node("check_session", self._check_session)
        builder.add_node("listening", self._listening)

        # Edge
        builder.add_edge(START, "start")

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
