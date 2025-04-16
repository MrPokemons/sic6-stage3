from typing import Optional, Literal
from typing_extensions import TypedDict


class UserData(TypedDict):
    name: str
    gender: Optional[Literal["male", "female"]]
    age: Optional[int]
    description: str = ""
    language: str = "Indonesian"
