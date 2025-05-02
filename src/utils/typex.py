from typing import TypeAlias, Annotated, Any, Literal
from pydantic import Field, AfterValidator
from pydantic.json_schema import SkipJsonSchema


ExcludedField: TypeAlias = SkipJsonSchema[
    Annotated[Any, Field(default=None, exclude=True), AfterValidator(lambda x: None)]
]

EmotionType: TypeAlias = Literal[
    "Happy",
    "Sad",
    "Angry",
    "Afraid",
    "Embarrassed",
    "Loving",
    "Confused",
    "Frustrated",
    "Confident",
    "Proud",
    "Jealous",
    "Relieved",
    "Tired",
    "Excited",
    "Nervous",
    "Disappointed",
    "Amazed",
    "Bored",
    "Doubtful",
]
