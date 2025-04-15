from typing import Annotated, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, PositiveInt
from langchain_core.messages import BaseMessage

from .topic import TopicResultsType, TopicParams
from .topic_flow import TopicFlowType
from .user import UserData


class SessionResult(BaseModel):
    type: TopicFlowType
    messages: List[BaseMessage]
    result: Optional[TopicResultsType] = None


class ConversationDoc(BaseModel):
    id: Annotated[str, "chat_id"]
    device_id: Annotated[str, "iot_device_id"]
    user: UserData
    feature_params: TopicParams
    selected_features: List[TopicFlowType]
    total_sessions: PositiveInt
    just_created: bool = True
    sessions: List[SessionResult] = []
    created_datetime: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def ongoing(self):
        return self.total_sessions > len(self.sessions)
