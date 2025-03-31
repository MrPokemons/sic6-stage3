from typing import Sequence

from pydantic import BaseModel


class Question(BaseModel):
    question: str
    answer: str
    hints: Sequence[str]


class Questions(BaseModel):
    questions: Sequence[Question]