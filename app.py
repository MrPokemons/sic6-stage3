import os

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from langchain_ollama import ChatOllama

from config.settings import SETTINGS

from src.services.pawpal import PawPal
from src.services.stt import (
    WhisperSpeechToText,
    DeepgramSpeechToText,
    SpeechToTextCollection,
)
from src.services.tts import (
    FacebookMMSTextToSpeech,
    ElevenlabsTextToSpeech,
    TextToSpeechCollection,
)
from src.services.nosql import MongoDBEngine

from src.controllers.health import health_router
from src.controllers import pawpal as pawpal_controller
from src.middleware import log_middleware

if SETTINGS.ENABLE_MQTT:
    from src.services.mqtt import fast_mqtt
    from src.controllers import pawpal_v2 as pawpal_v2_controller


# Logging
SETTINGS.configure_logging()
app_logger = logging.getLogger(__name__)

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    if SETTINGS.ENABLE_MQTT:
        await fast_mqtt.mqtt_startup()
    yield
    if SETTINGS.ENABLE_MQTT:
        await fast_mqtt.mqtt_shutdown()


# Initialize Services
mongodb_engine = MongoDBEngine(
    uri=SETTINGS.MONGODB.CONN_URI, db_name=SETTINGS.MONGODB.DB_NAME
)

# Speech to Text
whisper_stt = WhisperSpeechToText()
deepgram_stt = DeepgramSpeechToText(api_keys=SETTINGS.DEEPGRAM.API_KEYS)
stt_coll = SpeechToTextCollection(
    whisper=whisper_stt, deepgram=deepgram_stt, logger=app_logger
)

# LLM
model = ChatOllama(
    model=SETTINGS.MODEL.NAME,
    base_url=SETTINGS.MODEL.URL,
    num_ctx=2048 * 3,
    keep_alive=False,
)

# Text to Speech
facebook_mms_tts = FacebookMMSTextToSpeech()
elevenlabs_tts = ElevenlabsTextToSpeech(api_keys=SETTINGS.ELEVENLABS.API_KEYS)
tts_coll = TextToSpeechCollection(
    facebook_mms=facebook_mms_tts, elevenlabs=elevenlabs_tts, logger=app_logger
)

# Agentic
pawpal = PawPal()
pawpal.set_agentic_cls(model=model, mongodb_engine=mongodb_engine)


# App Router
app = FastAPI(lifespan=_lifespan)
app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(
    health_router(
        model=model,
        stt_coll=stt_coll,
        tts_coll=tts_coll,
    )
)

app.include_router(
    pawpal_controller.pawpal_router(
        pawpal=pawpal,
        stt_coll=stt_coll,
        tts_coll=tts_coll,
        logger=app_logger,
    )
)

if SETTINGS.ENABLE_MQTT:
    app.include_router(
        pawpal_v2_controller.pawpal_router(
            pawpal=pawpal,
            stt_coll=stt_coll,
            tts_coll=tts_coll,
            fast_mqtt=fast_mqtt,
            logger=app_logger,
        )
    )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=11080,
        log_config=None,
        ws_ping_interval=60,
        ws_ping_timeout=900,
    )
