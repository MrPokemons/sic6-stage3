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

from ..services.stt import SpeechToText
from ..services.tts import TextToSpeech
from ..services.pawpal import PawPal
from ..services.pawpal.schemas.user import UserData
from ..services.pawpal.schemas.topic import TopicParams
from ..services.pawpal.schemas.topic_flow import TopicFlowType
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
    model: BaseChatModel,
    stt: SpeechToText,
    tts: TextToSpeech,
    logger: logging.Logger,
):
    router = APIRouter(prefix="/api/v1/pawpal", tags=["pawpal"])
    pawpal_workflow = pawpal.build_workflow()

    # TODO:
    @router.get("/conversation/{device_id}")
    async def get_conversation(device_id: str) -> ConversationOutput:
        pawpal.get_agent_results(device_id=device_id)
        # take docs from "pawpal" collections.

        # curr_config = Agent.create_config(chat_id=chat_id)
        # state_snapshot = pawpal_workflow.get_state(config=curr_config)
        # if not state_snapshot.values:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND, detail="invalid chat_id"
        #     )
        # convo: Conversation = Conversation.model_validate(state_snapshot.values)
        # return convo
        return

    # TODO:
    @router.post("/conversation/start")
    async def start_conversation(
        conversation_input: StartConversationInput,
    ) -> ConversationOutput:
        """
        start convo triggered by FE, i need to create global state which filters by device_id
        which in websocket will constantly waiting for that device_id to appear,
        meanwhile having the chat status is still ongoing. If multiple just take the first.

        websocket will receive the registration of the device_id from IoT, then
        will try to check the mongodb collection "pawpal" whether there're active chat status.
        check every 5-10seconds then convo start,
        server will start the invocation and iot will wait instructions based on the interruptions
        from the server.
        """
        new_chat_id = str(uuid.uuid1())
        # new_config = Agent.create_config(chat_id=new_chat_id)
        # resp_state = await pawpal_workflow.ainvoke(
        #     {**conversation_input.model_dump(), "model": model, "chat_id": new_chat_id},
        #     config=new_config,
        # )
        # convo: Conversation = Conversation.model_validate(resp_state)
        # return convo
        return

    @router.websocket("/conversation/{device_id}")
    async def conversation(websocket: WebSocket, device_id: str):
        # curr_config = Agent.create_config(chat_id=chat_id)
        # state_snapshot = pawpal_workflow.get_state(config=curr_config)
        # if not state_snapshot.values:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND, detail="invalid chat_id"
        #     )

        # await websocket.accept()
        # while state_snapshot.next:
        #     try:
        #         audio_data = await websocket.receive_bytes()
        #         user_answer = stt.transcribe(audio_data)
        #         resp_state = await Agent.resume_workflow(
        #             workflow=pawpal_workflow, value=user_answer, config=curr_config
        #         )
        #         convo: Conversation = Conversation.model_validate(resp_state)
        #         last_question = convo.last_answered_question
        #         if last_question is None:
        #             raise HTTPException(
        #                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #                 detail="invalid flow logic, please review",
        #             )
        #         last_answer = last_question.answers[-1]
        #         model_response = last_answer.feedback
        #         logger.info(f"Websocket - Model Response: {model_response}")

        #         tts_audio = tts.synthesize(model_response)
        #         await websocket.send_bytes(tts_audio)

        #     except Exception as e:
        #         await websocket.close(code=1011, reason=str(e))
        #         logger.error(f"Conversation Error\n{traceback.format_exc()}")
        # else:
        #     raise HTTPException(
        #         status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="conversation ended"
        #     )
        return

    return router
