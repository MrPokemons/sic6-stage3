import uuid

from fastapi import status
from fastapi.routing import APIRouter
from fastapi.websockets import WebSocket
from fastapi.exceptions import HTTPException

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from ..utils.typex import ExcludedField
from ..services.agent import Agent
from ..schemas.conversation import Conversation, ConversationSettings
from ..services.stt import SpeechToText
from ..services.tts import TextToSpeech


class StartConversationInput(ConversationSettings):
    model: ExcludedField


class ConversationOutput(Conversation):
    messages: ExcludedField


def pawpal_conversation_router(
    pawpal_workflow: CompiledStateGraph,
    model: BaseChatModel,
    stt: SpeechToText,
    tts: TextToSpeech,
):
    router = APIRouter(prefix="/api/v1/pawpal", tags=["pawpal"])

    @router.get("/conversation/{chat_id}")
    async def get_conversation(chat_id: str) -> ConversationOutput:
        curr_config = Agent.create_config(chat_id=chat_id)
        state_snapshot = pawpal_workflow.get_state(config=curr_config)
        if not state_snapshot.values:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="invalid chat_id"
            )
        convo: Conversation = Conversation.model_validate(state_snapshot.values)
        return convo

    @router.post("/conversation/start")
    async def start_conversation(
        conversation_input: StartConversationInput,
    ) -> ConversationOutput:
        new_chat_id = str(uuid.uuid1())
        new_config = Agent.create_config(chat_id=new_chat_id)
        resp_state = await pawpal_workflow.ainvoke(
            {**conversation_input.model_dump(), "model": model, "chat_id": new_chat_id},
            config=new_config,
        )
        convo: Conversation = Conversation.model_validate(resp_state)
        return convo

    @router.websocket("/conversation/{chat_id}")
    async def conversation(websocket: WebSocket, chat_id: str):
        curr_config = Agent.create_config(chat_id=chat_id)
        state_snapshot = pawpal_workflow.get_state(config=curr_config)
        if not state_snapshot.values:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="invalid chat_id"
            )

        await websocket.accept()
        while state_snapshot.next:
            try:
                # 1. Receive audio
                audio_data = await websocket.receive_bytes()

                # 2. STT
                user_answer = stt.transcribe(audio_data)

                # 3. LLM
                resp_state = await Agent.resume_workflow(
                    workflow=pawpal_workflow, value=user_answer, config=curr_config
                )
                convo: Conversation = Conversation.model_validate(resp_state)
                last_question = convo.last_answered_question
                if last_question is None:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="invalid flow logic, please review",
                    )
                last_answer = last_question.answers[-1]
                model_response = last_answer.feedback

                # 4. TTS
                tts_audio = tts.synthesize(model_response)

                # 5. Send audio response
                await websocket.send_bytes(tts_audio)

            except Exception as e:
                await websocket.close(code=1011, reason=str(e))
                break
        else:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="conversation ended"
            )

    return router
