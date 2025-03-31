from typing import Literal
from langchain_core.messages import SystemMessage

from langgraph.types import Command
from langgraph.graph import StateGraph, CompiledStateGraph, START, END

from src.schemas.state import InputState, ConversationState, OutputState


class PawPal:
    @staticmethod
    def _start_training(state: InputState) -> Command[Literal["ask_question"]]:
        # message for what material should ask, what topic and maybe RAG for wanted material as referencee (?)
        messages = [
            SystemMessage(content=[
                {"type": "text", "text": ""}
            ])
        ]
        return Command(update={"messages": messages})

    @staticmethod
    def _ask_question(state: ConversationState) -> Command[Literal["evaluate_answer"]]:
        ...

    @staticmethod
    def _evaluate_answer(state: ConversationState) -> Command[Literal["congratulate_answer", "give_hint"]]:
        # interrupt for getting the answer from user
        ...

    @staticmethod
    def _congratulate_answer(state: ConversationState) -> Command[Literal["review_ground_truth"]]:
        ...

    @staticmethod
    def _give_hint(state: ConversationState) -> Command[Literal["evaluate_answer", "review_ground_truth"]]:
        # review ground truth if no more hint
        ...

    @staticmethod
    def _review_ground_truth(state: ConversationState) -> Command[Literal["ask_question", END]]:
        # if no more question, just end
        ...

    def build_workflow(self) -> CompiledStateGraph:
        builder = StateGraph(ConversationState, input=InputState, output=OutputState)

        builder.add_node("start_training", self._start_training)
        builder.add_node("ask_question", self._ask_question)
        builder.add_node("evaluate_answer", self._evaluate_answer)
        builder.add_node("congratulate_answer", self._congratulate_answer)
        builder.add_node("give_hint", self._give_hint)
        builder.add_node("review_ground_truth", self._review_ground_truth)

        builder.add_edge(START, "start_training")

        workflow = builder.compile()
        return workflow  # when doing invoke or stream, remember to set thread_id in config 
