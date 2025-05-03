import copy
from typing import Literal, Annotated, Optional, List, Sequence, TypeAlias, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, PositiveInt

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from .document import SessionResult
from .topic import TopicResultsType
from .topic_flow import TopicFlowType
from ....utils.validator import OneOrMany, one_or_many


class SessionState(BaseModel):
    total_sessions: PositiveInt
    from_node: Optional[str] = None
    next_node: Optional[str] = None
    sessions: List[SessionResult] = []
    messages: Annotated[Sequence[BaseMessage], add_messages] = []

    def add_session(self, session_type: TopicFlowType, messages: Sequence[BaseMessage]):
        self.sessions.append(
            SessionResult(type=session_type, messages=copy.deepcopy(messages))
        )
        # maybe send to mongo if you want, need collection name, or dont? dep injection?

    def verify_last_session(self, session_type: TopicFlowType) -> SessionResult:
        last_session = self.sessions[-1]
        if last_session.type != session_type:
            raise Exception(
                f"Not the appropriate type {last_session.model_dump(mode='json')}"
            )
        return last_session

    def add_message_to_last_session(
        self, session_type: TopicFlowType, messages: OneOrMany[BaseMessage]
    ):
        last_session = self.verify_last_session(session_type=session_type)
        messages = one_or_many(messages)
        last_session.messages.extend(messages)

    def add_result_to_last_session(
        self, session_type: TopicFlowType, result: TopicResultsType
    ):
        last_session = self.verify_last_session(session_type=session_type)
        last_session.result = result

    def get_sessions(self, *, deep=False):
        return copy.deepcopy(self.sessions)

    def last_ai_message(
        self, *, raise_if_none: bool = False, details: Optional[Any] = None
    ) -> Optional[BaseMessage]:
        try:
            return next(
                self.messages[i]
                for i in range(len(self.messages) - 1, -1, -1)
                if self.messages[i].type in ("ai",)
            )
        except StopIteration:
            if raise_if_none:
                raise Exception(f"How no last ai message? {details}")


InterruptAction: TypeAlias = Literal["speaker", "microphone"]


class InterruptSchema(TypedDict):
    action: InterruptAction
    message: Optional[str]
