from typing import Annotated, List, TypeAlias, Union
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from ....utils.typex import EmotionType


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

    class MathGameResult(BaseModel):
        class _Extract(BaseExtractionTopic): ...
        extraction: _Extract

    class SpellingGameResult(BaseModel): ...

    class WouldYouRatherResult(BaseModel): ...


TopicResultsType: TypeAlias = Union[
    TopicResults.TalkToMeResult,
    TopicResults.MathGameResult,
    TopicResults.SpellingGameResult,
    TopicResults.WouldYouRatherResult,
]
