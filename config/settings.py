import os
from typing import Literal
from pydantic import BaseModel, Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv

load_dotenv()


ENV_FILE = os.getenv("ENV_FILE")
if ENV_FILE is None:
    raise ValueError("You must set ENV_FILE in the environment")


class Settings(BaseSettings):
    class _App(BaseModel):
        HOST: str
        PORT: int
        ENV_NAME: str
        CONTAINER_NAME: str

    class _MongoDB(BaseModel):
        CONN_URI: str
        DB_NAME: str

    class _Model(BaseModel):
        NAME: str = Field(validation_alias=AliasChoices("MODEL", "NAME", "MODEL_NAME"))
        URL: str = Field(validation_alias=AliasChoices("URL", "BASE_URL"))

    ENV_TYPE: Literal["local", "development", "production"]
    APP: _App
    MONGODB: _MongoDB
    MODEL: _Model

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_nested_delimiter="__")
