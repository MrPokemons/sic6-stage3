from typing import Literal, Annotated, Optional, List, Sequence, TypeAlias
from typing_extensions import TypedDict
from pydantic import BaseModel, PositiveInt

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from .document import SessionResult


class SessionState(BaseModel):
    total_sessions: PositiveInt
    from_node: Optional[str] = None
    next_node: Optional[str] = None
    sessions: List[SessionResult] = []
    messages: Annotated[Sequence[BaseMessage], add_messages] = []


InterruptAction: TypeAlias = Literal["speaker", "microphone"]


class InterruptSchema(TypedDict):
    action: InterruptAction
    message: Optional[str]
