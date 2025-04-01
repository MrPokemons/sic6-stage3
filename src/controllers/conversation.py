import uuid

from typing import Literal
from fastapi import APIRouter, WebSocket, HTTPException, status

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from ..utils.typex import ExcludedField
from ..services.agent import Agent
from ..schemas.conversation import Conversation, ConversationSettings


class StartConversationInput(ConversationSettings):
    model: Literal["qwen2.5:3b"]


class ConversationOutput(Conversation):
    messages: ExcludedField


def pawpal_conversation_router(
    pawpal_workflow: CompiledStateGraph, model: BaseChatModel
):
    router = APIRouter(prefix="/api/v1/pawpal", tags=["pawpal"])

    @router.get("/conversation/{chat_id}")
    async def get_conversation(chat_id: str) -> ConversationOutput:
        curr_config = Agent.create_config(chat_id=chat_id)
        state_snapshot = pawpal_workflow.get_state(config=curr_config)
        if not state_snapshot.values:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invalid chat_id")
        convo: Conversation = Conversation.model_validate(state_snapshot.values)
        return convo

    @router.post("/conversation/start")
    async def start_conversation(
        conversation_input: StartConversationInput,
    ) -> ConversationOutput:
        new_chat_id = str(uuid.uuid1())
        new_config = Agent.create_config(chat_id=new_chat_id)
        resp_state = await pawpal_workflow.ainvoke(
            {"model": model, **conversation_input.model_dump()}, config=new_config
        )
        convo: Conversation = Conversation.model_validate(resp_state)
        return convo

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
