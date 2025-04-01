import uvicorn
from fastapi import FastAPI

from langchain_ollama import ChatOllama

from src.services.agent import PawPal
from src.controllers.conversation import pawpal_conversation_router


pawpal = PawPal()
pawpal_workflow = pawpal.build_workflow()
model = ChatOllama(model="qwen2.5:3b", num_ctx=2048 * 3, keep_alive=False)


app = FastAPI()
app.include_router(
    pawpal_conversation_router(pawpal_workflow=pawpal_workflow, model=model)
)


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=6789)
