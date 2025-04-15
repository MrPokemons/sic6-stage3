import asyncio
import uuid
import logging
import traceback
from typing import Annotated, List

from fastapi import status
from fastapi.routing import APIRouter
from fastapi.websockets import WebSocket
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, PositiveInt

from langchain_core.language_models import BaseChatModel
from langgraph.types import Command, Interrupt

from ..services.stt import SpeechToText
from ..services.tts import TextToSpeech
from ..services.pawpal import PawPal
from ..services.pawpal.schemas.config import ConfigSchema, ConfigurableSchema
from ..services.pawpal.schemas.user import UserData
from ..services.pawpal.schemas.topic import TopicParams
from ..services.pawpal.schemas.topic_flow import TopicFlowType
from ..services.pawpal.schemas.state import InterruptSchema
from ..services.pawpal.schemas.document import ConversationDoc


class StartConversationInput(BaseModel):
    device_id: Annotated[str, "iot_device_id"]
    user: UserData
    feature_params: TopicParams
    selected_features: List[TopicFlowType]
    total_sessions: PositiveInt


class ConversationOutput(ConversationDoc): ...


class TestAudioInput(BaseModel):
    audio_data: bytes


def pawpal_router(
    pawpal: PawPal,
    model: BaseChatModel,
    stt: SpeechToText,
    tts: TextToSpeech,
    logger: logging.Logger,
):
    router = APIRouter(prefix="/api/v1/pawpal", tags=["pawpal"])
    pawpal_workflow = pawpal.build_workflow()

    @router.get("/conversation/{device_id}")
    async def get_conversation(device_id: str) -> List[ConversationOutput]:
        docs = await pawpal.get_agent_results(device_id=device_id)
        docs = [ConversationDoc.model_validate(doc) for doc in docs]
        return docs

    @router.post("/conversation/start")
    async def start_conversation(
        conversation_input: StartConversationInput,
    ) -> ConversationOutput:
        new_chat_id = str(uuid.uuid1())
        new_conversation_doc = ConversationDoc(
            id=new_chat_id,
            device_id=conversation_input.device_id,
            user=conversation_input.user,
            feature_params=conversation_input.feature_params,
            selected_features=conversation_input.selected_features,
            total_sessions=conversation_input.total_sessions,
        )
        await pawpal.create_agent_conversation(conv_doc=new_conversation_doc)
        return {"message": "success"}, 201

    @router.websocket("/conversation/{device_id}")
    async def conversation(websocket: WebSocket, device_id: str):
        await websocket.accept()
        while 1:
            docs = await pawpal.get_agent_results(device_id=device_id)
            convo_docs: List[ConversationDoc] = sorted(
                [ConversationDoc.model_validate(doc) for doc in docs],
                key=lambda convo_doc: convo_doc.created_datetime,
                reverse=True,
            )
            curr_convo_doc = None
            for convo_doc in convo_docs:
                if convo_doc.ongoing:
                    curr_convo_doc = convo_doc.model_copy(deep=True)
                    break

            if curr_convo_doc is None:
                await asyncio.sleep(10)
                continue

            workflow_config = ConfigSchema(
                configurable=ConfigurableSchema(
                    thread_id=curr_convo_doc.id,
                    device_id=curr_convo_doc.device_id,
                    user=curr_convo_doc.user,
                    feature_params=curr_convo_doc.feature_params
                )
            )

            keep_running = True
            curr_input = {
                "total_sessions": curr_convo_doc.total_sessions,
                "selected_features": curr_convo_doc.selected_features
            }
            idk_just_run = 0
            while keep_running:
                async for _subgraph, event in pawpal_workflow.astream(
                    curr_input,
                    config=workflow_config,
                    stream_mode="updates",
                    subgraphs=True
                ):
                    for node, state in event.items():
                        if node == "talk":
                            continue

                        if node == "__interrupt__":
                            for interrupt_ in state:
                                interrupt_: Interrupt
                                for interrupt_schema in interrupt_.value:
                                    interrupt_schema: InterruptSchema
                                    if interrupt_schema["action"] == "speaker":
                                        tts_audio_data = tts.synthesize(interrupt_schema["message"])
                                        await websocket.send_bytes(tts_audio_data)
                                        curr_input = Command(resume="")
                                    elif interrupt_schema["action"] == "microphone":
                                        mic_audio_data = await websocket.receive_bytes()
                                        user_answer = stt.transcribe(mic_audio_data)
                                        curr_input = Command(resume=user_answer)
                                keep_running = interrupt_.resumable  # use i.resumable as the breaker for while loop
                            idk_just_run = 0

                idk_just_run += 1
                if idk_just_run >= 10000:
                    break

    @router.post("/test/audio")
    async def test_post_audio(test_audio_input: TestAudioInput):
        transcribed_text = stt.transcribe(test_audio_input.audio_data)
        print("Transcribed Text:", transcribed_text)
        return {"data": transcribed_text}

    @router.websocket("/test/audio")
    async def test_ws_audio(websocket: WebSocket):
        await websocket.accept()
        audio_data = await websocket.receive_bytes()
        audio_text = stt.transcribe(audio_data)
        print("Transcribed Text:", audio_text)
        await websocket.send(audio_text)
        await websocket.close()

    return router
