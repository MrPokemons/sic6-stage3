import uuid

from typing import Sequence
from pydantic import BaseModel, PositiveInt
from fastapi import APIRouter, WebSocket, HTTPException

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from ..services.agent import Agent
from ..schemas.state import ConversationState, ConversationQuestion


class StartConversationInput(BaseModel):
    topic: str
    subtopic: str
    description: str
    language: str = "Indonesian"
    TOTAL_QUESTIONS: PositiveInt = 10

class StartConversationOutput(BaseModel):
    chat_id: str
    questions: Sequence[ConversationQuestion]


def pawpal_conversation_router(pawpal_workflow: CompiledStateGraph, model: BaseChatModel):
    router = APIRouter(
        prefix="/api/v1/pawpal",
        tags=["pawpal"]
    )

    @router.get("/conversation/{chat_id}")
    async def get_conversation(chat_id: str) -> ConversationState:
        curr_config = Agent.create_config(chat_id=chat_id)
        state_snapshot = pawpal_workflow.get_state(config=curr_config)
        if not state_snapshot.values:
            raise HTTPException(status_code=404, detail="invalid chat_id")
        convo_state: ConversationState = ConversationState.model_validate(state_snapshot.values)
        return convo_state

    @router.post("/conversation/start")
    async def start_conversation(conversation_input: StartConversationInput) -> StartConversationOutput:
        new_chat_id = str(uuid.uuid1())
        new_config = Agent.create_config(chat_id=new_chat_id)
        resp_state = await pawpal_workflow.ainvoke({
            "llm": model,
            **conversation_input.model_dump()
        }, config=new_config)
        convo_state: ConversationState = ConversationState.model_validate(resp_state)
        return StartConversationOutput(
            chat_id=new_chat_id,
            questions=convo_state.questions
        )

    @router.websocket("/conversation")
    async def conversation(websocket: WebSocket):
        await websocket.accept()
        while True:
            audio_data = await websocket.receive_bytes()
            # stt
            user_answer = audio_data

            # llm


            # tts

    return router