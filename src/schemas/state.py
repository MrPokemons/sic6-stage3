from typing import Annotated, Sequence

from pydantic import BaseModel, PositiveInt

from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph.message import add_messages


class BaseState(BaseModel):
    llm: BaseChatModel
    messages: Annotated[Sequence[BaseMessage], add_messages] = []  # pydantic auto deep copy
    topic: str
    TOTAL_HINT: PositiveInt = 3
    TOTAL_QUESTION: PositiveInt = 10

class InputState(BaseState):
    ...

class ConversationState(BaseState):
    class Question(BaseModel):
        class UserAnswer(BaseModel):
            answer: str
            correct: bool
            skip: bool = False

        question: str
        answer: str
        hints: Sequence[str] = []  # length = length_answer - 1
        user_answers: Sequence[UserAnswer] = []

    questions: Sequence[Question] = []

class OutputState(ConversationState):
    ...
    