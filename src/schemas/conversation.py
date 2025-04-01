from typing import Sequence, List, Optional, Literal, Annotated
from pydantic import BaseModel, Field, PositiveInt
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class Question(BaseModel):
    content: str
    answer: str
    hints: Sequence[str]


class Answer(BaseModel):
    type: Literal["user"] = "user"
    content: str = Field(
        description="The provided answer; just set as empty string if you aren't sure."
    )


class AnswerWithEvaluation(Answer):
    correct: bool = Field(
        description="The provided answer accuracy towards the given question"
    )
    feedback: str = Field(description="feedback towards the provided answer")


class ConversationSettings(BaseModel):
    model: BaseChatModel
    topic: str
    subtopic: str
    description: Optional[str] = None
    language: Literal["Indonesian", "English"] = "Indonesian"
    total_questions: PositiveInt = 10


class ConversationQnA(BaseModel):
    finish: bool = False
    question: Question
    answers: List[AnswerWithEvaluation] = []


class Conversation(BaseModel):
    chat_id: str
    messages: Annotated[Sequence[BaseMessage], add_messages] = []
    active: bool
    questions: Sequence[ConversationQnA]
    settings: ConversationSettings

    @property
    def count_finish_questions(self) -> int:
        return sum(q.finish for q in self.questions)

    @property
    def next_question(self) -> Optional[ConversationQnA]:
        try:
            return next(q for q in self.questions if not q.finish)
        except StopIteration:
            ...

    @property
    def last_answered_question(self) -> Optional[ConversationQnA]:
        last_q: Optional[ConversationQnA] = None
        for q in self.questions:
            if not q.answers:
                break
            last_q = q
        return last_q
