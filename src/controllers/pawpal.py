import math
import asyncio
import logging
import numpy as np
import soundfile as sf
from typing import Annotated, List, Optional, Dict, Union, Tuple
from io import BytesIO
from bson.objectid import ObjectId

from fastapi.routing import APIRouter
from fastapi.websockets import WebSocket, WebSocketDisconnect
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
from ..services.pawpal.schemas.state import InterruptSchema, InterruptAction
from ..services.pawpal.schemas.document import ConversationDoc

from ..utils.message_packer import MessagePacker, MessageMetadata


class StartConversationInput(BaseModel):
    device_id: Annotated[str, "iot_device_id"]
    user: UserData
    feature_params: TopicParams
    selected_features: List[TopicFlowType]
    total_sessions: PositiveInt


class ConversationOutput(ConversationDoc): ...

# need to debug the send and recv chunking audio.
class ConnectionManager:
    def __init__(self, logger: logging.Logger, chunk_duration_ms: int = 20, message_packer: Optional[MessagePacker] = None):
        if message_packer is None:
            message_packer = MessagePacker(separator=b"---ENDJSON---")

        self.logger = logger
        self.chunk_duration_ms = chunk_duration_ms
        self.message_packer = message_packer

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def disconnect(self, websocket: WebSocket): ...

    async def send_text(
        self,
        websocket: WebSocket,
        message: str,
    ):
        await websocket.send_text(message)

    async def send_audio(self, websocket: WebSocket, audio_data: bytes):
        audio_array, sample_rate = sf.read(BytesIO(audio_data), dtype="int16")
        num_channels = 1 if len(audio_array.shape) == 1 else audio_array.shape[1]
        samples_per_chunk = self.get_samples_per_chunk(sample_rate=sample_rate)
        total_seq = math.ceil(audio_array.shape[0] / samples_per_chunk)
        for seq in range(total_seq):
            chunk = audio_array[samples_per_chunk*seq:samples_per_chunk*(seq+1)]
            chunk_metadata = MessageMetadata(
                seq=seq+1,
                total_seq=total_seq,
                sample_rate=sample_rate,
                channels=num_channels,
                dtype=str(audio_array.dtype)
            )
            packet = self.message_packer.pack(
                metadata=chunk_metadata,
                data=chunk
            )
            await websocket.send_bytes(packet)

    async def recv_audio(self, websocket: WebSocket) -> Tuple[np.ndarray, int]:
        list_chunk: List[Optional[np.ndarray]] = None
        sample_rate = None
        while 1:
            packet = await websocket.receive_bytes()
            metadata, chunk = self.message_packer.unpack(packet=packet)
            if list_chunk is None:
                list_chunk = [None] * metadata["total_seq"]

            sample_rate = metadata["sample_rate"]
            if metadata["channels"] > 1:
                chunk = chunk.reshape(-1, metadata["channels"])
                chunk = chunk.mean(axis=1)  # convert into mono

            list_chunk[metadata["seq"] - 1] = chunk
            if metadata["seq"] == metadata["total_seq"]:
                break

        missing_chunk_index_str = ', '.join([str(i) for i in range(len(list_chunk)) if list_chunk[i] is None])
        if missing_chunk_index_str:
            self.logger.warning(
                f"Missing chunk in index: {missing_chunk_index_str}"
            )
        audio_array = np.concatenate([_c for _c in list_chunk if isinstance(_c, np.ndarray)])
        return audio_array, sample_rate

    def get_samples_per_chunk(self, sample_rate: int):
        return sample_rate * self.chunk_duration_ms // 1000


def pawpal_router(
    pawpal: PawPal,
    stt: SpeechToText,
    tts: TextToSpeech,
    logger: logging.Logger,
):
    router = APIRouter(prefix="/api/v1/pawpal", tags=["pawpal"])
    pawpal_workflow = pawpal.build_workflow()
    ws_manager = ConnectionManager(logger=logger)

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
        logger.info(
            f"Device '{conversation_input.device_id}': Started new chat with id '{new_chat_id}'"
        )
        return new_conversation_doc

    @router.websocket("/conversation/{device_id}")
    async def conversation(websocket: WebSocket, device_id: str):
        await ws_manager.connect(websocket=websocket)
        logger.info(f"Device '{device_id}' has connected to server")
        try:
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
                    logger.info(f"Device '{device_id}' is waiting for new chat")
                    await asyncio.sleep(15)
                    continue

                if len(curr_convo_doc.sessions) == 0:
                    logger.info(
                        f"Device '{device_id}' is starting chat with id '{curr_convo_doc.id}'"
                    )
                else:
                    logger.info(
                        f"Device {device_id} is continuing chat with id '{curr_convo_doc.id}'"
                    )

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

                            if node != "__interrupt__":
                                continue

                            for interrupt_ in state:
                                interrupt_: Interrupt
                                list_interrupts: List[InterruptSchema] = (
                                    interrupt_.value
                                )
                                for interrupt_schema in list_interrupts:
                                    _action = interrupt_schema["action"]
                                    if _action not in InterruptAction.__args__:
                                        logger.warning(
                                            "Unknown interrupt action '{_action}'"
                                        )
                                        continue

                                    await ws_manager.send_text(websocket=websocket, message=_action)
                                    if _action == "speaker":
                                        tts_audio_data = tts.synthesize(
                                            interrupt_schema["message"]
                                        )
                                        logger.info("Sending audio to device")
                                        await ws_manager.send_audio(
                                            websocket=websocket,
                                            audio_data=tts_audio_data
                                        )
                                        logger.info("Sent, continue chat.")
                                        workflow_input = Command(resume="")
                                    elif _action == "microphone":
                                        logger.info(
                                            "Request audio recorded from microphone"
                                        )
                                        audio_array, sample_rate = await ws_manager.recv_audio(websocket=websocket)
                                        user_answer = stt.transcribe(audio_array, sample_rate=sample_rate)
                                        logger.info(
                                            f'Received, continue chat with new user answer "{user_answer}".'
                                        )
                                        workflow_input = Command(resume=user_answer)
                logger.info(
                    f"Device '{device_id}': Chat '{curr_convo_doc.id}' has ended"
                )
        except WebSocketDisconnect as e:
            ws_manager.disconnect(websocket=websocket)
            logger.info(f"Device '{device_id}' has disconnected, due to {e}")

    @router.websocket("/conversation-test")
    async def conversation_test(websocket: WebSocket):
        await websocket.accept()
        logger.info("Someone has connected to conversation test websocket")

        logger.info("Sending Audio to client using chunking")
        with open("tests/test.wav", "rb") as f:
            await websocket.send_bytes(f.read())

        logger.info("Trying to receive chunked audio from client")
        audio_bytes = await websocket.receive_bytes()

        logger.info("Received the audio successfully, trying to play")
        audio_array, sample_rate = sf.read(BytesIO(audio_bytes), dtype="int16")

        try:
            import sounddevice as sd
            sd.play(data=audio_array, samplerate=sample_rate)
            sd.wait()
        except OSError:
            _fp = "tests/conversation-test-result.wav"
            logger.info(f"failed to play due to unsupported OS, will just write to '{_fp}'")
            sf.write(_fp, data=audio_array, samplerate=sample_rate)

        logger.info("Testing successfully been executed")


    @router.websocket("/conversation-chunking-test")
    async def conversation_chunking_test(websocket: WebSocket):
        await ws_manager.connect(websocket=websocket)
        logger.info("Someone has connected to conversation chunking test websocket")

        logger.info("Sending Audio to client using chunking")
        with open("tests/test.wav", "rb") as f:
            await ws_manager.send_audio(
                websocket=websocket,
                audio_data=f.read()
            )

        logger.info("Trying to receive chunked audio from client")
        audio_array, sample_rate = await ws_manager.recv_audio(websocket=websocket)

        logger.info("Received the audio successfully, trying to play")
        try:
            import sounddevice as sd
            sd.play(data=audio_array, samplerate=sample_rate)
            sd.wait()
        except OSError:
            _fp = "tests/conversation-chunking-test-result.wav"
            logger.info(f"failed to play due to unsupported OS, will just write to '{_fp}'")
            sf.write(_fp, data=audio_array, samplerate=sample_rate)

        logger.info("Testing successfully been executed")

    return router
