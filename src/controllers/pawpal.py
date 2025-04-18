import asyncio
import logging
from typing import Annotated, List, Optional, Dict, Union
from bson.objectid import ObjectId

from fastapi.routing import APIRouter
from fastapi.websockets import WebSocket
from pydantic import BaseModel, PositiveInt

from langgraph.types import Command, Interrupt
from langgraph.graph import END

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


def pawpal_router(
    pawpal: PawPal,
    stt: SpeechToText,
    tts: TextToSpeech,
    logger: logging.Logger,
):
    router = APIRouter(prefix="/api/v1/pawpal", tags=["pawpal"])
    pawpal_workflow = pawpal.build_workflow()

    @router.get("/conversation/{device_id}")
    async def get_conversations(device_id: str) -> List[ConversationOutput]:
        docs = await pawpal.get_agent_results(device_id=device_id)
        docs = [ConversationDoc.model_validate(doc) for doc in docs]
        docs = sorted(docs, key=lambda x: x.created_datetime, reverse=True)
        return docs

    @router.post("/conversation/start")
    async def start_conversation(
        conversation_input: StartConversationInput,
    ) -> ConversationOutput:
        new_chat_id = str(ObjectId())
        new_conversation_doc = ConversationDoc(
            id=new_chat_id,
            device_id=conversation_input.device_id,
            user=conversation_input.user,
            feature_params=conversation_input.feature_params,
            selected_features=conversation_input.selected_features,
            total_sessions=conversation_input.total_sessions,
        )
        await pawpal.create_agent_conversation(conv_doc=new_conversation_doc)
        return new_conversation_doc

    @router.websocket("/conversation/{device_id}")
    async def conversation(websocket: WebSocket, device_id: str):
        await websocket.accept()
        while 1:
            docs = await pawpal.get_agent_results(device_id=device_id)
            active_convo_docs: List[ConversationDoc] = [
                convo_doc
                for convo_doc in sorted(
                    [ConversationDoc.model_validate(doc) for doc in docs],
                    key=lambda convo_doc: convo_doc.created_datetime,
                )
                if convo_doc.ongoing
            ]
            curr_convo_doc: Optional[ConversationDoc] = None
            for convo_doc in active_convo_docs:
                if convo_doc.ongoing:
                    curr_convo_doc = convo_doc.model_copy(deep=True)
                    break

            if curr_convo_doc is None:
                print(f"Device '{device_id}' waiting for new chat.")
                await asyncio.sleep(15)
                continue

            print(f"Device '{device_id}' starting chat '{curr_convo_doc.id}'.")
            workflow_config = ConfigSchema(
                configurable=ConfigurableSchema(
                    thread_id=curr_convo_doc.id,
                    device_id=curr_convo_doc.device_id,
                    user=curr_convo_doc.user,
                    feature_params=curr_convo_doc.feature_params,
                )
            )

            workflow_input = {
                "total_sessions": curr_convo_doc.total_sessions,
                "selected_features": curr_convo_doc.selected_features,
            }

            keep_running = True
            while keep_running:
                async for _subgraph, event in pawpal_workflow.astream(
                    workflow_input,
                    config=workflow_config,
                    stream_mode="updates",
                    subgraphs=True,
                ):
                    event: Dict[str, Union[dict, list, tuple]]
                    for node, state in event.items():
                        if node == "talk":
                            continue

                        if (
                            isinstance(state, dict)
                            and state.get("next_node") == END
                            and not _subgraph
                        ):
                            keep_running = False

                        if node == "__interrupt__":
                            for interrupt_ in state:
                                interrupt_: Interrupt
                                list_interrupts: List[InterruptSchema] = (
                                    interrupt_.value
                                )
                                for interrupt_schema in list_interrupts:
                                    if interrupt_schema["action"] == "speaker":
                                        await websocket.send_text("speaker")
                                        tts_audio_data = tts.synthesize(
                                            interrupt_schema["message"]
                                        )
                                        await websocket.send_bytes(tts_audio_data)
                                        workflow_input = Command(resume="")
                                    elif interrupt_schema["action"] == "microphone":
                                        await websocket.send_text("microphone")
                                        mic_audio_data = await websocket.receive_bytes()
                                        user_answer = stt.transcribe(mic_audio_data)
                                        workflow_input = Command(resume=user_answer)

    return router
