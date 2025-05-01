from typing import Annotated, List, TypeAlias, Union, TYPE_CHECKING
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from datetime import datetime

from ....utils.typex import EmotionType


if TYPE_CHECKING:
    from ..subflows.math_game import MathQnA

class TopicParams(TypedDict):
    class TalkToMeParam(TypedDict):
        duration: Annotated[int, "in seconds"]

    class MathGameParam(TypedDict):
        total_question: int

    class SpellingGameParam(TypedDict):
        total_question: int

    class WouldYouRatherParam(TypedDict):
        duration: Annotated[int, "in seconds"]

    talk_to_me: TalkToMeParam
    math_game: MathGameParam
    spelling_game: SpellingGameParam
    would_you_rather: WouldYouRatherParam


class BaseExtractionTopic(BaseModel):
    overview: str = Field(
        description="Summarize the chat history, oriented to user's progress and achievement"
    )
    emotion: EmotionType = Field(
        description=f"Based on the user's response behaviour, analyze the user's overall emotion based on the provided list of emotions: {', '.join(EmotionType.__args__)}"
    )
    keypoints: List[str] = Field(
        description="List major event or behaviour for overall of the conversation, it can be achievement from the user or something that user need to know about themselve throughout the conversation"
    )


class TopicResults(BaseModel):
    class TalkToMeResult(BaseModel):
        class _Extraction(BaseExtractionTopic): ...
        extraction: _Extraction
        start_datetime: datetime
        modified_datetime: datetime

    class MathGameResult(BaseModel):
        class _Extraction(BaseExtractionTopic): ...
        extraction: _Extraction
        list_qna: List[MathQnA]
        start_datetime: datetime
        modified_datetime: datetime

    class SpellingGameResult(BaseModel): ...

    class WouldYouRatherResult(BaseModel): ...


TopicResultsType: TypeAlias = Union[
    TopicResults.TalkToMeResult,
    TopicResults.MathGameResult,
    TopicResults.SpellingGameResult,
    TopicResults.WouldYouRatherResult,
]
