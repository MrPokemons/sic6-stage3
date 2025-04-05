import logging

import uvicorn
from fastapi import FastAPI

from langchain_ollama import ChatOllama

from src.schemas.config import Config
from src.services.agent import PawPal
from src.services.stt import SpeechToText
from src.services.tts import TextToSpeech
from src.controllers.conversation import pawpal_conversation_router
from config.settings import load_config


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[
        logging.FileHandler("logs/pawpal.log"),
        logging.StreamHandler(),
    ],
)

app_logger = logging.Logger(__name__)

CONFIG = Config.model_validate(load_config())

pawpal = PawPal()
pawpal_workflow = pawpal.build_workflow()

stt = SpeechToText()
model = ChatOllama(model="qwen2.5:3b", num_ctx=2048 * 3, keep_alive=False)
tts = TextToSpeech()


app = FastAPI()
app.include_router(
    pawpal_conversation_router(
        pawpal_workflow=pawpal_workflow, model=model, stt=stt, tts=tts, logger=app_logger
    )
)


if __name__ == "__main__":
    uvicorn.run(app=app, host=CONFIG.app.host, port=CONFIG.app.port)
