from typing import Literal, Sequence
from langchain_core.messages import SystemMessage, HumanMessage

from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from ..schemas.question import Questions
from ..schemas.state import InputState, ConversationState, OutputState, ConversationQuestion, ConversationUserAnswer
from ..utils.prompt_loader import BASE_PROMPT, SCOPE_PROMPT, GUIDELINE_PROMPT, GENERATE_QUESTION_PROMPT, VERIFY_ANSWER_PROMPT


class PawPal:
    @staticmethod
    def _start_training(state: InputState) -> Command[Literal["wait_and_evaluate_answer"]]:
        # message for what material should ask, what topic and maybe RAG for wanted material as referencee (?)
        messages = [
            SystemMessage(content=[
                {"type": "text", "text": BASE_PROMPT}
            ]),
            SystemMessage(content=[
                {"type": "text", "text": SCOPE_PROMPT.format(topic=state.topic, subtopic=state.subtopic, description=state.description)}
            ]),
            SystemMessage(content=[
                {"type": "text", "text": GUIDELINE_PROMPT}
            ]),
            SystemMessage(content=[
                {"type": "text", "text": GENERATE_QUESTION_PROMPT.format(total_questions=state.TOTAL_QUESTIONS, language=state.language)}
            ])
        ]
        new_questions: Questions = state.llm.with_structured_output(Questions).invoke(messages)
        questions_state: Sequence[ConversationQuestion] = [ConversationQuestion(**q.model_dump()) for q in new_questions.questions]
        return Command(update={"messages": messages, "questions": questions_state}, goto="wait_and_evaluate_answer")

    @staticmethod
    def _wait_and_evaluate_answer(state: ConversationState) -> Command[Literal["wait_and_evaluate_answer", END]]:
        next_question = state.last_answered_question
        if next_question is None or next_question.done:
            next_question = state.next_question
            if next_question is None:
                return Command(goto=END)

        # interrupt for sending question to answer and getting the answer from user
        user_answer = interrupt("what is the answer?")
        messages = [
            # SystemMessage(content=[
            #     {"type": "text", "text": BASE_PROMPT}
            # ]),
            # SystemMessage(content=[
            #     {"type": "text", "text": SCOPE_PROMPT.format(topic=state.topic, subtopic=state.subtopic, description=state.description)}
            # ]),
            # SystemMessage(content=[
            #     {"type": "text", "text": GUIDELINE_PROMPT}
            # ]),
            HumanMessage(content=[
                {"type": "text", "text": VERIFY_ANSWER_PROMPT.format(question=next_question.question, correct_answer=next_question.answer, user_answer=user_answer, language=state.language)}
            ])
        ]
        evaluated_user_answer: ConversationUserAnswer = state.llm.with_structured_output(ConversationUserAnswer).invoke(messages)
        evaluated_user_answer.answer = user_answer
        next_question.done = evaluated_user_answer.correct
        next_question.user_answers.append(evaluated_user_answer)
        return Command(update={"messages": messages[3:]}, goto="wait_and_evaluate_answer")

    def build_workflow(self):
        builder = StateGraph(ConversationState, input=InputState, output=OutputState)

        builder.add_node("start_training", self._start_training)
        builder.add_node("wait_and_evaluate_answer", self._wait_and_evaluate_answer)

        builder.add_edge(START, "start_training")

        workflow = builder.compile(checkpointer=MemorySaver())
        return workflow  # when doing invoke or stream, remember to set thread_id in config 
