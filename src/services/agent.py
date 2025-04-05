from abc import ABC, abstractmethod
from typing import Literal, Sequence, Annotated, Any
from pydantic import BaseModel

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from ..schemas.conversation import (
    Question,
    ConversationSettings,
    ConversationQnA,
    Conversation,
    AnswerWithEvaluation,
    Answer,
)
from ..utils.prompt_loader import (
    BASE_PROMPT,
    SCOPE_PROMPT,
    GUIDELINE_PROMPT,
    GENERATE_QUESTION_PROMPT,
    VERIFY_ANSWER_PROMPT,
)


class InputState(ConversationSettings):
    chat_id: str
    messages: Annotated[Sequence[BaseMessage], add_messages] = []


class ConversationState(Conversation):
    model: BaseChatModel   # the .settings.model doesn't persist, so this is the alternative


class OutputState(Conversation): ...


class GenerateQuestionsPrompt(BaseModel):
    questions: Sequence[Question]


class Agent(ABC):
    @abstractmethod
    def build_workflow(self) -> CompiledStateGraph: ...

    @staticmethod
    def create_config(chat_id: str) -> dict:
        config = {"configurable": {"thread_id": chat_id}}
        return config

    @staticmethod
    async def resume_workflow(workflow: CompiledStateGraph, value: Any, config: dict):
        resume_command = Command(resume=value)
        return await workflow.ainvoke(resume_command, config=config)


class PawPal(Agent):
    @staticmethod
    async def _start_training(
        state: InputState,
    ) -> Command[Literal["wait_and_evaluate_answer"]]:
        # message for what material should ask, what topic and maybe RAG for wanted material as referencee (?)
        messages = [
            SystemMessage(content=[{"type": "text", "text": BASE_PROMPT}]),
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": SCOPE_PROMPT.format(
                            topic=state.topic,
                            subtopic=state.subtopic,
                            description=state.description,
                        ),
                    }
                ]
            ),
            SystemMessage(content=[{"type": "text", "text": GUIDELINE_PROMPT}]),
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": GENERATE_QUESTION_PROMPT.format(
                            total_questions=state.total_questions,
                            language=state.language,
                        ),
                    }
                ]
            ),
        ]
        new_generated_questions: GenerateQuestionsPrompt = (
            await state.model.with_structured_output(GenerateQuestionsPrompt).ainvoke(
                messages
            )
        )
        questions_state: Sequence[ConversationQnA] = [
            ConversationQnA(question=q) for q in new_generated_questions.questions
        ]
        return Command(
            update={
                "chat_id": state.chat_id,
                "messages": messages,
                "active": True,
                "questions": questions_state,
                "settings": ConversationSettings.model_validate(state, strict=True),
                "model": state.model
            },
            goto="wait_and_evaluate_answer",
        )

    @staticmethod
    async def _wait_and_evaluate_answer(state: ConversationState) -> Command[Literal["wait_and_evaluate_answer", END]]:  # type: ignore
        next_question = state.last_answered_question
        if next_question is None or next_question.finish:
            next_question = state.next_question
            if next_question is None:
                return Command(update={"active": False}, goto=END)

        user_answer = interrupt(
            f"Question: {next_question.question.content}\nWhat is your answer?"
        )

        messages = [
            SystemMessage(content=[{"type": "text", "text": BASE_PROMPT}]),
            SystemMessage(
                content=[
                    {
                        "type": "text",
                        "text": SCOPE_PROMPT.format(
                            topic=state.settings.topic,
                            subtopic=state.settings.subtopic,
                            description=state.settings.description,
                        ),
                    }
                ]
            ),
            SystemMessage(content=[{"type": "text", "text": GUIDELINE_PROMPT}]),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": VERIFY_ANSWER_PROMPT.format(
                            question=next_question.question.content,
                            correct_answer=next_question.question.answer,
                            user_answer=user_answer,
                            language=state.settings.language,
                        ),
                    }
                ]
            ),
        ]
        evaluated_answer: AnswerWithEvaluation = (
            await state.model.with_structured_output(
                AnswerWithEvaluation
            ).ainvoke(messages)
        )
        evaluated_answer.content = Answer(role="user", content=user_answer)
        next_question.finish = evaluated_answer.correct
        next_question.answers.append(evaluated_answer)
        return Command(
            update={"messages": messages[3:]}, goto="wait_and_evaluate_answer"
        )

    def build_workflow(self) -> CompiledStateGraph:
        builder = StateGraph(ConversationState, input=InputState, output=OutputState)

        builder.add_node("start_training", self._start_training)
        builder.add_node("wait_and_evaluate_answer", self._wait_and_evaluate_answer)

        builder.add_edge(START, "start_training")

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow
