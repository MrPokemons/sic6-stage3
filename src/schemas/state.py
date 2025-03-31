from typing import Annotated, Sequence, List, Optional

from pydantic import BaseModel, PositiveInt, Field

from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph.message import add_messages

from .question import Question


class BaseState(BaseModel):
    llm: BaseChatModel
    messages: Annotated[Sequence[BaseMessage], add_messages] = []  # pydantic auto deep copy
    topic: str
    subtopic: str
    description: str
    TOTAL_QUESTIONS: PositiveInt = 10


class InputState(BaseState):
    ...


class ConversationUserAnswer(BaseModel):
    answer: str = Field(description="user's answer")
    correct: bool = Field(description="user's answer accuracy towards the given question")
    feedback: str = Field(description="feedback towards user's answer")

class ConversationQuestion(Question):
    done: bool = False
    user_answers: List[ConversationUserAnswer] = []

class ConversationState(BaseState):
    questions: Sequence[ConversationQuestion]

    @property
    def count_done(self) -> int:
        return sum(q.done for q in self.questions)

    @property
    def next_question(self) -> Optional[ConversationQuestion]:
        try:
            return next(q for q in self.questions if not q.done)
        except StopIteration:
            ...
    
    @property
    def last_answered_question(self) -> Optional[ConversationQuestion]:
        last_q: Optional[ConversationQuestion] = None
        for q in self.questions:
            if not q.user_answers:
                break
            last_q = q
        return last_q


class OutputState(ConversationState):
    ...
    