import math
import asyncio
import logging
import librosa
import numpy as np
import soundfile as sf
from io import BytesIO
from pathlib import Path
from typing import Annotated, List, Optional, Dict, Union, Tuple, Literal
from bson.objectid import ObjectId
from datetime import datetime, timezone

from fastapi.routing import APIRouter
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, PositiveInt

from langgraph.types import Command, Interrupt
from langgraph.graph import END

from ..services.stt import SpeechToTextCollection
from ..services.tts import TextToSpeechCollection
from ..services.pawpal import PawPal
from ..services.pawpal.schemas.config import ConfigSchema, ConfigurableSchema
from ..services.pawpal.schemas.user import UserData
from ..services.pawpal.schemas.topic import TopicParams
from ..services.pawpal.schemas.topic_flow import TopicFlowType, TopicFlowNodeType
from ..services.pawpal.schemas.state import InterruptSchema, InterruptAction
from ..services.pawpal.schemas.document import ConversationDoc

from ..utils.message_packer import MessagePacker, MessageMetadata
from ..utils.misc import secure_shuffle


STATIC_AUDIO_PATH = Path(__file__).parents[2] / "static" / "audio"


class StartConversationInput(BaseModel):
    device_id: Annotated[str, "iot_device_id"]
    user: UserData
    feature_params: TopicParams
    selected_features: List[TopicFlowType]
    total_sessions: PositiveInt


class ConversationOutput(ConversationDoc): ...


class ConnectionManager:
    def __init__(
        self,
        logger: logging.Logger,
        chunk_duration_ms: int = 20,
        message_packer: Optional[MessagePacker] = None,
    ):
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

    async def send_audio(self, websocket: WebSocket, audio_data: bytes, *, target_sample_rate: Optional[int] = None) -> None:
        audio_array, sample_rate = sf.read(BytesIO(audio_data), dtype="float32")
        if target_sample_rate and sample_rate != target_sample_rate:
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=target_sample_rate, res_type="soxr_qq")
            sample_rate = target_sample_rate

        num_channels = 1 if len(audio_array.shape) == 1 else audio_array.shape[1]
        samples_per_chunk = self.get_samples_per_chunk(sample_rate=sample_rate)
        total_seq = math.ceil(audio_array.shape[0] / samples_per_chunk)
        for seq in range(total_seq):
            chunk = audio_array[samples_per_chunk * seq : samples_per_chunk * (seq + 1)]
            chunk_metadata = MessageMetadata(
                seq=seq + 1,
                total_seq=total_seq,
                sample_rate=sample_rate,
                channels=num_channels,
                dtype=str(audio_array.dtype),
            )
            packet = self.message_packer.pack(metadata=chunk_metadata, data=chunk)
            await websocket.send_bytes(packet)

    async def recv_audio(self, websocket: WebSocket) -> Tuple[np.ndarray, int]:
        list_chunk: List[Optional[np.ndarray]] = None
        sample_rate = None
        while 1:
            packet = await asyncio.wait_for(websocket.receive_bytes(), timeout=40)
            self.logger.info("Received packet")
            metadata, chunk = self.message_packer.unpack(packet=packet)
            self.logger.info(f"Client's Metadata: {metadata}\n")
            if list_chunk is None:
                list_chunk = [None] * metadata["total_seq"]

            if metadata["channels"] > 1:
                chunk = chunk.reshape(-1, metadata["channels"])
                # chunk = chunk.mean(axis=1)  # don't think the mono conversion is working

            chunk_sample_rate = metadata["sample_rate"]
            if sample_rate is None:  # first chunk's sample_rate will be the foundation for the rest of chunks
                sample_rate = chunk_sample_rate
            elif chunk_sample_rate != sample_rate:
                chunk = librosa.resample(chunk, orig_sr=chunk_sample_rate, target_sr=sample_rate, res_type="soxr_qq")

            list_chunk[metadata["seq"] - 1] = chunk
            if metadata["seq"] == metadata["total_seq"]:
                break

        total_missing_chunks = len(
            [1 for i in range(len(list_chunk)) if list_chunk[i] is None]
        )
        if total_missing_chunks:
            self.logger.warning(f"Total missing chunk: {total_missing_chunks}")
        audio_array = np.concatenate(
            [_c for _c in list_chunk if isinstance(_c, np.ndarray)]
        )
        return audio_array, sample_rate

    def get_samples_per_chunk(self, sample_rate: int) -> int:
        return sample_rate * self.chunk_duration_ms // 1000


def pawpal_router(
    pawpal: PawPal,
    stt_coll: SpeechToTextCollection,
    tts_coll: TextToSpeechCollection,
    logger: logging.Logger,
):
    router = APIRouter(prefix="/api/v1/pawpal", tags=["pawpal"])
    pawpal_workflow = pawpal.build_workflow()
    ws_manager = ConnectionManager(logger=logger)

    @router.get("/conversation/{device_id}")
    async def get_conversations(device_id: str) -> List[ConversationOutput]:
        docs = await pawpal.get_agent_results(device_id=device_id)
        docs = [ConversationDoc.model_validate(_doc) for _doc in docs]
        docs = sorted(docs, key=lambda x: x.created_datetime, reverse=True)
        return docs

    @router.get("/conversation/{device_id}/live")
    async def get_live_conversations(device_id: str) -> List[ConversationOutput]:
        docs = await pawpal.get_agent_results(device_id=device_id)
        docs = [ConversationDoc.model_validate(_doc) for _doc in docs]
        docs = sorted(
            [_doc for _doc in docs if _doc.ongoing], key=lambda x: x.created_datetime
        )
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
    async def conversation(
        websocket: WebSocket,
        device_id: str,
        stream_audio: Literal["websocket", "http", "device"] = "websocket",
        target_sample_rate: Optional[int] = None,
        debug_mode: bool = False,
    ):
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
                    if convo_doc.ongoing  # filter the only ongoing
                ]
                curr_convo_doc: Optional[ConversationDoc] = None
                for convo_doc in active_convo_docs:  # always take the first created
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
                    "selected_features": secure_shuffle(
                        curr_convo_doc.selected_features
                    ),
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
                                node
                                not in TopicFlowNodeType.__args__  # to handle if exit subflow, can trigger keep_running false instead waiting for check_session
                                and isinstance(state, dict)
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

                                    logger.info(f"Agentic sent Action: {_action}")
                                    _action, _addons = f"{_action.strip('+')}+".split(
                                        "+", 1
                                    )
                                    if _action == "speaker":
                                        if _addons == "audio":
                                            _audio_array, _sample_rate = sf.read(
                                                interrupt_schema["message"],
                                                dtype="float32",
                                            )
                                            _audio_buffer = BytesIO()
                                            sf.write(
                                                _audio_buffer,
                                                data=_audio_array,
                                                samplerate=_sample_rate,
                                                format="WAV",
                                            )
                                            tts_audio_data = _audio_buffer.getvalue()
                                        else:
                                            tts_audio_data = (
                                                await tts_coll.synthesize_async(
                                                    interrupt_schema["message"],
                                                )
                                            )

                                        logger.info("Sending audio to device")
                                        if stream_audio == "http":
                                            """
                                            we send_text "speaker;filename", then we save the audio into static folder.
                                            then client will need to access the static folder with the provided filename
                                            """
                                            logger.info(
                                                f"Saving audio to '{STATIC_AUDIO_PATH}' as file"
                                            )
                                            audio_array, sample_rate = sf.read(
                                                BytesIO(tts_audio_data), dtype="float32"
                                            )
                                            if target_sample_rate and sample_rate != target_sample_rate:
                                                audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=target_sample_rate, res_type="soxr_qq")
                                                sample_rate = target_sample_rate

                                            audio_filename = datetime.now(
                                                timezone.utc
                                            ).strftime("%Y%m%d_%H%M%S%f.wav")
                                            sf.write(
                                                STATIC_AUDIO_PATH / audio_filename,
                                                audio_array,
                                                samplerate=sample_rate,
                                            )
                                            logger.info(
                                                f"Saved the audio file '{audio_filename}' into '{STATIC_AUDIO_PATH}'"
                                            )
                                            await ws_manager.send_text(
                                                websocket=websocket,
                                                message=f"{_action};{audio_filename}",
                                            )
                                            logger.info(
                                                "Sent the audio filename to client."
                                            )
                                        elif stream_audio == "device":
                                            """
                                            we don't need to send any text to client, since this will play to server device
                                            or save as filename
                                            """
                                            logger.info("Playing audio through device")
                                            audio_array, sample_rate = sf.read(
                                                BytesIO(tts_audio_data), dtype="int16"
                                            )
                                            try:
                                                import sounddevice as sd

                                                sd.play(
                                                    data=audio_array,
                                                    samplerate=sample_rate,
                                                )
                                                sd.wait()
                                            except OSError:
                                                audio_filename = datetime.now(
                                                    timezone.utc
                                                ).strftime(
                                                    "conversation-%Y%m%d_%H%M%S%f.wav"
                                                )
                                                logger.info(
                                                    f"failed to play due to unsupported OS, will into file '{audio_filename}' in {STATIC_AUDIO_PATH}"
                                                )
                                                sf.write(
                                                    STATIC_AUDIO_PATH / audio_filename,
                                                    audio_array,
                                                    samplerate=sample_rate,
                                                )
                                        else:
                                            """
                                            default websocket send_text for telling it will be speaker, then stream with chunks
                                            """
                                            await ws_manager.send_text(
                                                websocket=websocket, message=_action
                                            )
                                            logger.info(
                                                "Streaming audio through websocket to client."
                                            )
                                            await ws_manager.send_audio(
                                                websocket=websocket,
                                                audio_data=tts_audio_data,
                                                target_sample_rate=target_sample_rate
                                            )
                                            logger.info(
                                                "Audio has been sent to client, server proceed to continue agentic chat"
                                            )

                                        workflow_input = Command(resume="")
                                    elif _action == "microphone":
                                        """
                                        server will confirm to client we will need microphone, then client will stream us with chunking
                                        """
                                        await ws_manager.send_text(
                                            websocket=websocket, message=_action
                                        )
                                        logger.info(
                                            "Request audio recorded from microphone"
                                        )
                                        audio_array, sample_rate = (
                                            await ws_manager.recv_audio(
                                                websocket=websocket
                                            )
                                        )

                                        if debug_mode:
                                            try:
                                                import sounddevice as sd
                                                sd.play(data=audio_array, samplerate=sample_rate)
                                                sd.wait()
                                            except OSError:
                                                audio_filename = datetime.now(timezone.utc).strftime("test-debug_mode_on-%Y%m%d_%H%M%S%f.wav")
                                                _fp = f"tests/{audio_filename}"
                                                logger.info(
                                                    f"failed to play due to unsupported OS, will just write to '{_fp}'"
                                                )
                                                sf.write(_fp, data=audio_array, samplerate=sample_rate)

                                        buffer = (
                                            BytesIO()
                                        )  # convert into bytes for processing to stt_coll
                                        sf.write(
                                            buffer,
                                            audio_array,
                                            sample_rate,
                                            format="WAV",
                                        )
                                        logger.info(
                                            "Audio has been received, parsing to STT model"
                                        )
                                        user_answer = (
                                            await stt_coll.transcribe_raw_async(
                                                buffer.getvalue()
                                            )
                                        )
                                        logger.info(
                                            f'Done parsing, continue chat with new user answer "{user_answer}".'
                                        )
                                        workflow_input = Command(resume=user_answer)
                logger.info(
                    f"Device '{device_id}': Chat '{curr_convo_doc.id}' has ended"
                )
        except WebSocketDisconnect as e:
            logger.info(f"Device '{device_id}' has disconnected, due to {e}")
            ws_manager.disconnect(websocket=websocket)

    @router.websocket("/conversation-test")
    async def conversation_test(websocket: WebSocket, cue_action: bool = False):
        await websocket.accept()
        logger.info("Someone has connected to conversation test websocket")

        logger.info("Sending Audio to client using chunking")
        if cue_action:
            await websocket.send_text("speaker;")
        with open("tests/test.wav", "rb") as f:
            await websocket.send_bytes(f.read())

        logger.info("Trying to receive chunked audio from client")
        if cue_action:
            await websocket.send_text("microphone;")
        audio_bytes = await websocket.receive_bytes()

        logger.info("Received the audio successfully, trying to play")
        audio_array, sample_rate = sf.read(BytesIO(audio_bytes), dtype="int16")
        try:
            import sounddevice as sd

            sd.play(data=audio_array, samplerate=sample_rate)
            sd.wait()
        except OSError:
            _fp = "tests/conversation-test-result.wav"
            logger.info(
                f"failed to play due to unsupported OS, will just write to '{_fp}'"
            )
            sf.write(_fp, data=audio_array, samplerate=sample_rate)

        logger.info("Testing successfully been executed")

    @router.websocket("/conversation-chunking-test")
    async def conversation_chunking_test(websocket: WebSocket, cue_action: bool = False, target_sample_rate: Optional[int] = None):
        await ws_manager.connect(websocket=websocket)
        logger.info("Someone has connected to conversation chunking test websocket")

        logger.info("Sending Audio to client using chunking")
        if cue_action:
            await websocket.send_text("speaker;")
        with open("tests/test.wav", "rb") as f:
            await ws_manager.send_audio(
                websocket=websocket,
                audio_data=f.read(),
                target_sample_rate=target_sample_rate
            )

        logger.info("Trying to receive chunked audio from client")
        if cue_action:
            await websocket.send_text("microphone;")
        audio_array, sample_rate = await ws_manager.recv_audio(websocket=websocket)

        logger.info("Received the audio successfully, trying to play")
        try:
            import sounddevice as sd

            sd.play(data=audio_array, samplerate=sample_rate)
            sd.wait()
        except OSError:
            _fp = "tests/conversation-chunking-test-result.wav"
            logger.info(
                f"failed to play due to unsupported OS, will just write to '{_fp}'"
            )
            sf.write(_fp, data=audio_array, samplerate=sample_rate)

        logger.info("Testing successfully been executed")

    @router.websocket("/conversation-chunking-http-test")
    async def conversation_chunking_http_test(websocket: WebSocket, target_sample_rate: Optional[int] = None):
        await ws_manager.connect(websocket=websocket)
        logger.info(
            "Someone has connected to conversation chunking http test websocket"
        )

        # speaker
        logger.info(
            "Sending Audio to client text for accessing the audio static through http"
        )
        with open("tests/test.wav", "rb") as f:
            test_audio_data = f.read()

        logger.info(f"Saving audio to '{STATIC_AUDIO_PATH}' as file")
        audio_array, sample_rate = sf.read(BytesIO(test_audio_data), dtype="float32")
        if target_sample_rate and sample_rate != target_sample_rate:
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=target_sample_rate, res_type="soxr_qq")
            sample_rate = target_sample_rate

        audio_filename = datetime.now(timezone.utc).strftime("test-%Y%m%d_%H%M%S%f.wav")
        sf.write(
            STATIC_AUDIO_PATH / audio_filename, audio_array, samplerate=sample_rate
        )
        logger.info(
            f"Saved the audio file '{audio_filename}' into '{STATIC_AUDIO_PATH}'"
        )
        await ws_manager.send_text(
            websocket=websocket, message=f"speaker;{audio_filename}"
        )
        logger.info("Sent the audio filename to client.")

        # Microphone
        await ws_manager.send_text(websocket=websocket, message="microphone;")
        logger.info("Trying to receive chunked audio from client")
        audio_array, sample_rate = await ws_manager.recv_audio(websocket=websocket)

        logger.info("Received the audio successfully, trying to play")
        try:
            import sounddevice as sd

            sd.play(data=audio_array, samplerate=sample_rate)
            sd.wait()
        except OSError:
            _fp = "tests/conversation-chunking-test-result.wav"
            logger.info(
                f"failed to play due to unsupported OS, will just write to '{_fp}'"
            )
            sf.write(_fp, data=audio_array, samplerate=sample_rate)

        logger.info("Testing successfully been executed")

    @router.get("/http-wav-response-test")
    async def get_http_wav_response_test(target_sample_rate: Optional[int] = None):
        with open("tests/test1.wav", "rb") as f:
            wav_bytes = f.read()
            if target_sample_rate:
                audio_array, sample_rate = sf.read(BytesIO(wav_bytes), dtype="float32")
                if sample_rate != target_sample_rate:
                    audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=target_sample_rate, res_type="soxr_qq")
                    sample_rate = target_sample_rate

                buffer = BytesIO()
                sf.write(
                    buffer,
                    audio_array,
                    sample_rate,
                    format="WAV",
                )
                wav_bytes = buffer.getvalue()

            return Response(content=wav_bytes, media_type="audio/wav")

    @router.get("/http-wav-file-test")
    async def get_http_wav_file_test():
        return FileResponse(
            "tests/test1.wav", media_type="audio/wav", filename="example.wav"
        )

    return router
