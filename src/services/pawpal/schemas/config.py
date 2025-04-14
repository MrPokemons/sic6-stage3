from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.runnables.config import RunnableConfig
from .topic import TopicParams
from .user import UserData


class ConfigurableSchema(TypedDict):
    thread_id: Annotated[str, "chat_id"]
    device_id: Annotated[str, "iot_device_id"]
    user: UserData
    feature_params: TopicParams


class ConfigSchema(RunnableConfig):
    configurable: ConfigurableSchema
