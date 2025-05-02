import os
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from langchain_ollama import ChatOllama

from config.settings import Settings

from src.services.pawpal import PawPal
from src.services.stt import WhisperSpeechToText, DeepgramSpeechToText, SpeechToTextCollection
from src.services.tts import FacebookMMSTextToSpeech, ElevenlabsTextToSpeech, TextToSpeechCollection
from src.services.nosql import MongoDBEngine

from src.controllers.pawpal import pawpal_router
from src.middleware import log_middleware


# Load Up Global ENV Configuration
CONFIG = Settings()

# Logging
CONFIG.configure_logging()
app_logger = logging.getLogger(__name__)

# Initialize Services
mongodb_engine = MongoDBEngine(
    uri=CONFIG.MONGODB.CONN_URI, db_name=CONFIG.MONGODB.DB_NAME
)

# Speech to Text
whisper_stt = WhisperSpeechToText()
deepgram_stt = DeepgramSpeechToText(api_keys=CONFIG.DEEPGRAM.API_KEYS)
stt_coll = SpeechToTextCollection(
    whisper=whisper_stt,
    deepgram=deepgram_stt,
    logger=app_logger
)

# LLM
model = ChatOllama(
    model=CONFIG.MODEL.NAME,
    base_url=CONFIG.MODEL.URL,
    num_ctx=2048 * 3,
    keep_alive=False,
)

# Text to Speech
facebook_mms_tts = FacebookMMSTextToSpeech()
elevenlabs_tts = ElevenlabsTextToSpeech(
    api_keys=CONFIG.ELEVENLABS.API_KEYS
)
tts_coll = TextToSpeechCollection(
    facebook_mms=facebook_mms_tts,
    elevenlabs=elevenlabs_tts,
    logger=app_logger
)

# Agentic
pawpal = PawPal()
pawpal.set_agentic_cls(model=model, mongodb_engine=mongodb_engine)


# App Router
app = FastAPI()
app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(
    pawpal_router(
        pawpal=pawpal,
        stt_coll=stt_coll,
        tts_coll=tts_coll,
        logger=app_logger,
    )
)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=11080, log_config=None, ws_ping_interval=60, ws_ping_timeout=900)
