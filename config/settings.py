import os
from typing import Literal

import logging
from logging.config import dictConfig

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv

load_dotenv()


ENV_FILE = os.getenv("ENV_FILE")
if ENV_FILE is None:
    raise ValueError("You must set ENV_FILE in the environment")


class Settings(BaseSettings):
    class _App(BaseModel):
        CONTAINER_NAME: str

    class _MongoDB(BaseModel):
        CONN_URI: str
        DB_NAME: str

    class _Model(BaseModel):
        NAME: str
        URL: str

    ENV_TYPE: Literal["local", "development", "production"]
    APP: _App
    MONGODB: _MongoDB
    MODEL: _Model

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_nested_delimiter="__")

    def configure_logging(self):
        os.makedirs("logs", exist_ok=True)
        dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "()": "uvicorn.logging.DefaultFormatter",
                        "fmt": (
                            f"[{self.ENV_TYPE}:{self.APP.CONTAINER_NAME}] "
                            "%(asctime)s [%(process)d] [%(levelname)s] "
                            "%(name)s - %(module)s: %(message)s"
                        ),
                        "datefmt": "%Y-%m-%d %H:%M:%S",
                    },
                },
                "handlers": {
                    "console": {
                        "formatter": "default",
                        "class": "logging.StreamHandler",
                        "level": "INFO",
                    },
                    "file": {
                        "formatter": "default",
                        "class": "logging.FileHandler",
                        "filename": "logs/pawpal.log",
                    },
                },
                "loggers": {
                    "uvicorn": {
                        "handlers": ["console", "file"],
                        "level": "INFO",
                        "propagate": False,
                    },
                    "uvicorn.error": {"level": "INFO"},
                    "uvicorn.access": {
                        "handlers": ["console", "file"],
                        "level": "INFO",
                        "propagate": False,
                    },
                },
                "root": {"level": "DEBUG", "handlers": ["console", "file"]},
            }
        )

        disabled_loggers = (
            "httpx",
            "httpcore.http11",
            "httpcore.connection",
            "pdfminer",
            "pymongo.topology",
            "urllib3.connectionpool",
        )
        for logger_name in logging.root.manager.loggerDict:
            logger = logging.getLogger(logger_name)
            if any(logger_name.startswith(disabled) for disabled in disabled_loggers):
                logger.setLevel(logging.ERROR)
