from typing import Annotated, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, PositiveInt
from langchain_core.messages import BaseMessage
from ..services.pawpal.schemas import UserData, FeatureParams
from ..services.pawpal.subflows import FlowFeatureType
from ..services.pawpal.schemas import FeatureResultsType


class SessionResult(BaseModel):
    type: FlowFeatureType
    messages: List[BaseMessage]
    result: FeatureResultsType

class ConversationDoc(BaseModel):
    id: Annotated[str, "chat_id"]
    device_id: Annotated[str, "iot_device_id"]
    user: UserData
    feature_params: FeatureParams
    selected_features: List[FlowFeatureType]
    total_sessions: PositiveInt
    sessions: List[SessionResult]
    created_datetime: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
