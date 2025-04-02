import uvicorn
from fastapi import FastAPI

from langchain_ollama import ChatOllama

from src.schemas.config import Config
from src.services.agent import PawPal
from src.services.stt import SpeechToText
from src.services.tts import TextToSpeech
from src.controllers.conversation import pawpal_conversation_router
from config.settings import load_config


CONFIG = Config.model_validate(load_config())

pawpal = PawPal()
pawpal_workflow = pawpal.build_workflow()

stt = SpeechToText()
model = ChatOllama(model="qwen2.5:3b", num_ctx=2048 * 3, keep_alive=False)
tts = TextToSpeech()


app = FastAPI()
app.include_router(
    pawpal_conversation_router(pawpal_workflow=pawpal_workflow, model=model)
)


if __name__ == "__main__":
    uvicorn.run(app=app, host=CONFIG.app.host, port=CONFIG.app.port)
