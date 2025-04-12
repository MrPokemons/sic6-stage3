import os
import logging
from logging.config import dictConfig

import uvicorn
from fastapi import FastAPI

from langchain_ollama import ChatOllama

from src.services.agent import PawPal
from src.services.stt import SpeechToText
from src.services.tts import TextToSpeech
from src.controllers.conversation import pawpal_conversation_router
from config.settings import Settings


# ENV Configuration
CONFIG = Settings()

# Logging
os.makedirs("logs", exist_ok=True)
dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": (
                    f"[{CONFIG.ENV_TYPE}:{CONFIG.APP.CONTAINER_NAME}] %(asctime)s [%(process)d] [%(levelname)s] %(name)s - %(module)s: %(message)s"
                ),
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": "INFO",
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": "logs/pawpal.log",
                "formatter": "default",
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
        },
    }
)
disabled_loggers = (
    "httpx",
    "httpcore.http11",
    "httpcore.connection",
    "pdfminer",
    "pymongo.topology",
)
for logger_name in logging.root.manager.loggerDict:
    logger = logging.getLogger(logger_name)
    if any(logger_name.startswith(disabled) for disabled in disabled_loggers):
        logger.setLevel("ERROR")

app_logger = logging.Logger(__name__)


# Initialize Services
pawpal = PawPal()
pawpal_workflow = pawpal.build_workflow()

stt = SpeechToText()
model = ChatOllama(model="qwen2.5:3b", num_ctx=2048 * 3, keep_alive=False)
tts = TextToSpeech()


# App Router
app = FastAPI()

app.include_router(
    pawpal_conversation_router(
        pawpal_workflow=pawpal_workflow,
        model=model,
        stt=stt,
        tts=tts,
        logger=app_logger,
    )
)


if __name__ == "__main__":
    uvicorn.run(app=app, host=CONFIG.app.host, port=CONFIG.app.port)
