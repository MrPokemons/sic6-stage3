import os
import logging
from logging.config import dictConfig

import uvicorn
from fastapi import FastAPI
from langchain_ollama import ChatOllama

from config.settings import Settings

from src.services.pawpal import PawPal
from src.services.stt import SpeechToText
from src.services.tts import TextToSpeech
from src.services.nosql import MongoDBEngine

from src.controllers.pawpal import pawpal_router


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
mongodb_engine = MongoDBEngine(
    uri=CONFIG.MONGODB.CONN_URI, db_name=CONFIG.MONGODB.DB_NAME
)
pawpal = PawPal(mongodb_engine=mongodb_engine, collection_name="pawpal")
stt = SpeechToText()
model = ChatOllama(model=CONFIG.MODEL.NAME, num_ctx=2048 * 3, keep_alive=False)
tts = TextToSpeech()


# App Router
app = FastAPI()

app.include_router(
    pawpal_router(
        pawpal=pawpal,
        model=model,
        stt=stt,
        tts=tts,
        logger=app_logger,
    )
)


if __name__ == "__main__":
    uvicorn.run(app=app, host=CONFIG.APP.HOST, port=CONFIG.APP.PORT)
