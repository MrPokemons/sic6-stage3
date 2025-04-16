from typing import Annotated, List, TypeAlias, Union
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


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


class TopicResults(BaseModel):
    class TalkToMeResult(BaseModel):
        overview: str = Field(description="Summarize the chat history")
        emotion: str = Field(
            description="Analyze the emotion based on the behaviour and chatting style, or how he/she feeling from the chat history provided"
        )
        keypoints: List[str] = Field(
            description="List the key points from the chat history, which pointing out the important section or behaviour from the chat history provided"
        )

    class MathGameResult(BaseModel): ...

    class SpellingGameResult(BaseModel): ...

    class WouldYouRatherResult(BaseModel): ...


TopicResultsType: TypeAlias = Union[
    TopicResults.TalkToMeResult,
    TopicResults.MathGameResult,
    TopicResults.SpellingGameResult,
    TopicResults.WouldYouRatherResult,
]
