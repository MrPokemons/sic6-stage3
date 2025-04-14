from typing import Literal, Annotated, Optional, List, Sequence
from typing_extensions import TypedDict
from pydantic import BaseModel, PositiveInt

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables.config import RunnableConfig
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class FeatureParams(TypedDict):
    class TalkToMeParam(TypedDict):
        duration: Annotated[int, "in seconds"]

    class MathGameParam(TypedDict):
        total_question: int
        hint: int = 3

    class SpellingGameParam(TypedDict):
        total_question: int

    class WouldYouRatherParam(TypedDict):
        duration: Annotated[int, "in seconds"]

    talk_to_me: TalkToMeParam
    math_game: MathGameParam
    spelling_game: SpellingGameParam
    would_you_rather: WouldYouRatherParam


class UserData(TypedDict):
    name: str
    gender: Optional[Literal["male", "female"]]
    age: Optional[int]
    decsription: str = ""


class ConfigurableSchema(TypedDict):
    thread_id: Annotated[str, "chat_id"]
    device_id: Annotated[str, "iot_device_id"]
    model: BaseChatModel
    user: UserData
    feature_params: FeatureParams


class ConfigSchema(RunnableConfig):
    configurable: ConfigurableSchema


class SessionState(BaseModel):
    total_sessions: PositiveInt
    from_node: Optional[str] = None
    next_node: Optional[str] = None
    sessions: List[Annotated[dict, "feature's session result"]] = []
    messages: Annotated[Sequence[BaseMessage], add_messages] = []


class InterruptSchema(TypedDict):
    action: Literal["speaker", "microphone"]
    message: Optional[str]
