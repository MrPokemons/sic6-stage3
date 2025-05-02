from typing import Optional, Literal
from typing_extensions import TypedDict


class UserData(TypedDict):
    name: str
    gender: Optional[Literal["female", "male", "Female", "Male"]]
    age: Optional[int]
    description: Optional[str]
    language: Literal["indonesian", "english", "Indonesian", "English"]
