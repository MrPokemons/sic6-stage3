import math
import logging
import librosa
import numpy as np
import soundfile as sf
from io import BytesIO
from pathlib import Path
from typing import Any, Annotated, List, Optional, Dict, Union, Tuple, Literal, TypeAlias
from bson.objectid import ObjectId

from fastapi import status as http_status
from fastapi.exceptions import HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel, PositiveInt
from fastapi_mqtt import FastMQTT
from gmqtt import Client as MQTTClient

from langgraph.types import Command, Interrupt
from langgraph.graph import END
from langgraph.graph.state import CompiledStateGraph

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

TOPIC_SPEAKER = "pawpal/{device_id}/speaker"
TOPIC_COMMAND = "pawpal/{device_id}/command"
TOPIC_RECORDING = "pawpal/{device_id}/recording"

FORCE_LOCAL = True

DEVICE_ID: TypeAlias = Annotated[str, "Iot Device ID"]


class StartConversationInput(BaseModel):
    device_id: DEVICE_ID
    user: UserData
    feature_params: TopicParams
    selected_features: List[TopicFlowType]
    total_sessions: PositiveInt


class ConversationOutput(ConversationDoc): ...


COMMAND_TYPE: TypeAlias = Literal["record"]


class PawPalMQTTManager:
    def __init__(
        self,
        fast_mqtt: FastMQTT,
        pawpal: PawPal,
        pawpal_workflow: CompiledStateGraph,
        stt_coll: SpeechToTextCollection,
        tts_coll: TextToSpeechCollection,
        logger: logging.Logger,
        chunk_duration_ms: int = 20,
        message_packer: Optional[MessagePacker] = None,
    ):
        if message_packer is None:
            message_packer = MessagePacker(separator=b"---ENDJSON---")

        self.client = fast_mqtt
        self.pawpal = pawpal
        self.pawpal_workflow = pawpal_workflow
        self.stt_coll = stt_coll
        self.tts_coll = tts_coll
        self.logger = logger
        self.chunk_duration_ms = chunk_duration_ms
        self.message_packer = message_packer

        self.recording_packet_stream: Dict[DEVICE_ID, List[Tuple[MessageMetadata, np.ndarray]]] = {}

    def publish_command(self, device_id: DEVICE_ID, command: COMMAND_TYPE):
        self.client.publish(
            message_or_topic=TOPIC_COMMAND.format(device_id=device_id),
            payload=command,
            qos=2,
        )

    async def subscribe_recording_on_message(self, topic: str, payload: bytes):
        device_id: DEVICE_ID = topic.split("/", 2)[1]
        if device_id not in self.recording_packet_stream:
            self.recording_packet_stream[device_id] = []

        _metadata, _chunk = self.message_packer.unpack(packet=payload)

        self.recording_packet_stream[device_id].append((_metadata, _chunk))

        if _metadata["seq"] != _metadata["total_seq"]:
            return  # audio streaming in progress

        # audio streaming completed, assembling in progress
        sample_rate: Optional[int] = None
        list_chunk: List[np.ndarray] = []
        for curr_metadata, curr_chunk in sorted(self.recording_packet_stream[device_id], key=lambda x: x[0]["seq"]):
            if curr_metadata["channels"] > 1:
                curr_chunk = curr_chunk.reshape(-1, curr_metadata["channels"])
                # chunk = chunk.mean(axis=1)  # don't think the mono conversion is working

            curr_chunk_sample_rate = curr_metadata["sample_rate"]
            if sample_rate is None:  # first chunk's sample_rate will be the foundation for the rest of chunks
                sample_rate = curr_chunk_sample_rate
            elif curr_chunk_sample_rate != sample_rate:
                curr_chunk = librosa.resample(curr_chunk, orig_sr=curr_chunk_sample_rate, target_sr=sample_rate, res_type="soxr_qq")

            list_chunk.append(curr_chunk)

        audio_array = np.concatenate(
            [_c for _c in list_chunk if isinstance(_c, np.ndarray)]
        )

        # TODO: need to resume the workflow
        buffer = BytesIO()

        sf.write(
            buffer,
            audio_array,
            sample_rate,
            format="WAV",
        )
        self.logger.info(
            "Audio has been received, parsing to STT model"
        )

        user_answer = await self.stt_coll.transcribe_raw_async(
            buffer.getvalue(),
            force_local=FORCE_LOCAL,
        )
        self.logger.info(
            f'Done parsing, continue chat with new user answer "{user_answer}".'
        )
        workflow_input = Command(resume=user_answer)

        docs = await self.pawpal.get_agent_results(device_id=device_id)
        active_convo_docs: List[ConversationDoc] = [
            convo_doc
            for convo_doc in sorted(
                [ConversationDoc.model_validate(doc) for doc in docs],
                key=lambda convo_doc: convo_doc.created_datetime,
            )
            if convo_doc.ongoing  # filter the only ongoing
        ]
        if not active_convo_docs:
            return # should we return err?

        curr_convo = active_convo_docs[0]

        workflow_config = ConfigSchema(
            configurable=ConfigurableSchema(
                thread_id=curr_convo.id,
                device_id=curr_convo.device_id,
                user=curr_convo.user,
                feature_params=curr_convo.feature_params,
            )
        )
        keep_running = True
        while keep_running:
            async for _subgraph, event in self.pawpal_workflow.astream(
                input=workflow_input,
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
                                self.logger.warning(
                                    "Unknown interrupt action '{_action}'"
                                )
                                continue

                            self.logger.info(f"Agentic sent Action: {_action}")
                            _action, _addons = f"{_action.strip('+')}+".split(
                                "+", 1
                            )
                            _addons = _addons.strip("+")
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
                                        await self.tts_coll.synthesize_async(
                                            interrupt_schema["message"],
                                            force_local=FORCE_LOCAL,
                                        )
                                    )

                                self.logger.info("Sending audio to device")
                                self.publish_speaker(
                                    device_id=curr_convo.device_id,
                                    audio_data=tts_audio_data,
                                    target_sample_rate=curr_convo.target_sample_rate,
                                )
                                self.logger.info(
                                    "Audio has been sent to client, server proceed to continue agentic chat"
                                )

                                workflow_input = Command(resume="")
                            elif _action == "microphone":
                                """
                                server will confirm to client we will need microphone, then client will stream us with chunking
                                """
                                self.publish_command(
                                    device_id=curr_convo.device_id,
                                    command="record",
                                )
                                self.logger.info(
                                    "Request audio recorded from microphone"
                                )
                                keep_running = False

        # cleaning up
        self.recording_packet_stream.pop(device_id)

    def publish_speaker(self, device_id: DEVICE_ID, audio_data: bytes, *, target_sample_rate: Optional[int] = None):
        audio_array, sample_rate = sf.read(BytesIO(audio_data), dtype="float32")
        if target_sample_rate and sample_rate != target_sample_rate:
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=target_sample_rate, res_type="soxr_qq")
            sample_rate = target_sample_rate

        num_channels = 1 if len(audio_array.shape) == 1 else audio_array.shape[1]
        samples_per_chunk = self._get_samples_per_chunk(sample_rate=sample_rate)
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
            self.client.publish(
                message_or_topic=TOPIC_SPEAKER.format(device_id=device_id),
                payload=packet,
                qos=2 if seq + 1 == total_seq else 0,
            )

    def _get_samples_per_chunk(self, sample_rate: int) -> int:
        return sample_rate * self.chunk_duration_ms // 1000


def pawpal_router(
    pawpal: PawPal,
    fast_mqtt: FastMQTT,
    stt_coll: SpeechToTextCollection,
    tts_coll: TextToSpeechCollection,
    logger: logging.Logger,
):
    router = APIRouter(prefix="/api/v2/pawpal", tags=["pawpal-v2"])
    pawpal_workflow = pawpal.build_workflow()

    mqtt_manager = PawPalMQTTManager(
        fast_mqtt=fast_mqtt,
        pawpal=pawpal,
        pawpal_workflow=pawpal_workflow,
        stt_coll=stt_coll,
        tts_coll=tts_coll,
        logger=logger,
    )

    # due to "The QoS Negotiation Rule", mostly qos=0 until the last one will be qos=2 by the publisher as well
    @fast_mqtt.subscribe(TOPIC_RECORDING.format(device_id="+"), qos=2)
    async def pawpal_recording_data(client: MQTTClient, topic: str, payload: bytes, qos: int, properties: Any):
        logger.info(f"PawPal Server Subscribe Recording: {repr(topic)}, {repr(payload)}, {repr(qos)}, {repr(properties)}")

    @fast_mqtt.on_message()
    async def message(client: MQTTClient, topic: str, payload: bytes, qos: int, properties: Any):
        logger.info(f"Received message: {repr(topic)}, {repr(qos)}, {repr(properties)}")
        if (
            (_t := (topic.rsplit("/", 1) or [""])[-1])
            and (_t == "recording")
        ):
            await mqtt_manager.subscribe_recording_on_message(topic=topic, payload=payload)

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
        target_sample_rate: Optional[int] = None,
    ) -> ConversationOutput:
        docs = await pawpal.get_agent_results(device_id=conversation_input.device_id)
        active_convo_docs: List[ConversationDoc] = [
            convo_doc
            for convo_doc in sorted(
                [ConversationDoc.model_validate(doc) for doc in docs],
                key=lambda convo_doc: convo_doc.created_datetime,
            )
            if convo_doc.ongoing  # filter the only ongoing
        ]
        if active_convo_docs:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="There is active conversation going, please complete it first..."
            )

        new_chat_id = str(ObjectId())
        new_conversation_doc = ConversationDoc(
            id=new_chat_id,
            device_id=conversation_input.device_id,
            user=conversation_input.user,
            feature_params=conversation_input.feature_params,
            selected_features=conversation_input.selected_features,
            total_sessions=conversation_input.total_sessions,
            target_sample_rate=target_sample_rate,
        )
        await pawpal.create_agent_conversation(conv_doc=new_conversation_doc)
        logger.info(
            f"Device '{conversation_input.device_id}': Initiating new chat with id '{new_chat_id}'"
        )

        # TODO: Start workflow
        workflow_config = ConfigSchema(
            configurable=ConfigurableSchema(
                thread_id=new_conversation_doc.id,
                device_id=new_conversation_doc.device_id,
                user=new_conversation_doc.user,
                feature_params=new_conversation_doc.feature_params,
            )
        )
        workflow_input = {
            "total_sessions": new_conversation_doc.total_sessions,
            "selected_features": secure_shuffle(
                new_conversation_doc.selected_features
            ),
        }
        keep_running = True
        while keep_running:
            async for _subgraph, event in pawpal_workflow.astream(
                input=workflow_input,
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
                            _addons = _addons.strip("+")
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
                                            force_local=FORCE_LOCAL,
                                        )
                                    )

                                logger.info("Sending audio to device")
                                mqtt_manager.publish_speaker(
                                    device_id=new_conversation_doc.device_id,
                                    audio_data=tts_audio_data,
                                    target_sample_rate=target_sample_rate,
                                )
                                logger.info(
                                    "Audio has been sent to client, server proceed to continue agentic chat"
                                )

                                workflow_input = Command(resume="")
                            elif _action == "microphone":
                                """
                                server will confirm to client we will need microphone, then client will stream us with chunking
                                """
                                mqtt_manager.publish_command(
                                    device_id=new_conversation_doc.device_id,
                                    command="record",
                                )
                                logger.info(
                                    "Request audio recorded from microphone"
                                )
                                keep_running = False

        return new_conversation_doc

    @router.delete("/conversation/{device_id}", status_code=http_status.HTTP_204_NO_CONTENT)
    async def delete_ongoing_conversation(device_id: str):
        docs = await pawpal.get_agent_results(device_id=device_id)
        for _doc in docs:
            _convo_doc = ConversationDoc.model_validate(_doc)
            if _convo_doc.ongoing:
                await pawpal.delete_agent_conversation(convo_doc_id=_convo_doc.id)

    return router
