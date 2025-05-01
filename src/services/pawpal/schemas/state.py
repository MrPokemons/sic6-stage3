import copy
from typing import Literal, Annotated, Optional, List, Sequence, TypeAlias
from typing_extensions import TypedDict
from pydantic import BaseModel, PositiveInt

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from .document import SessionResult
from .topic_flow import TopicFlowType


class SessionState(BaseModel):
    total_sessions: PositiveInt
    from_node: Optional[str] = None
    next_node: Optional[str] = None
    sessions: List[SessionResult] = []
    messages: Annotated[Sequence[BaseMessage], add_messages] = []

    def add_session(self, session_type: Literal[TopicFlowType], messages: Sequence[BaseMessage]):
        self.sessions.append(
            SessionResult(
                type=session_type,
                messages=copy.deepcopy(messages)
            )
        )
        # maybe send to mongo if you want, need collection name, or dont? dep injection?

    def get_sessions(self, *, deep=False):
        return copy.deepcopy(self.sessions)


InterruptAction: TypeAlias = Literal["speaker", "microphone"]


class InterruptSchema(TypedDict):
    action: InterruptAction
    message: Optional[str]
