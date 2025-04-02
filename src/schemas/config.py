from pydantic import BaseModel
from .model import ModelProviders, ModelProviderSettings


class Config(BaseModel):
    class _App(BaseModel):
        host: str = "0.0.0.0"
        port: int = 5000

    class _Model(BaseModel):
        provider: ModelProviders
        settings: ModelProviderSettings

    app: _App
    model: _Model