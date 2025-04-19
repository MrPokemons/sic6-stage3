import logging
import uvicorn
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from langchain_ollama import ChatOllama

from config.settings import Settings

from src.services.pawpal import PawPal
from src.services.stt import SpeechToText
from src.services.tts import TextToSpeech
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
stt = SpeechToText()
model = ChatOllama(
    model=CONFIG.MODEL.NAME,
    base_url=CONFIG.MODEL.URL,
    num_ctx=2048 * 3,
    keep_alive=False,
)
tts = TextToSpeech()

pawpal = PawPal()
pawpal.set_agentic_cls(model=model, mongodb_engine=mongodb_engine)


# App Router
app = FastAPI()
app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)

app.include_router(
    pawpal_router(
        pawpal=pawpal,
        stt=stt,
        tts=tts,
        logger=app_logger,
    )
)


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=11080, log_config=None)
