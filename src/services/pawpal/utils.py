import os
from pydantic import BaseModel, Field
from langchain.schema import BaseMessage, AIMessage, HumanMessage, SystemMessage

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt_md(filename: str) -> str:
    with open(os.path.join(PROMPT_DIR, filename), "r", encoding="utf8") as f:
        return f.read()


class PromptLoader(BaseModel):
    class TalkToMe(BaseModel):
        opening: str = Field(
            default_factory=lambda: load_prompt_md("talk_to_me/opening.md")
        )

    # Core Flow
    baseline: str = Field(default_factory=lambda: load_prompt_md("baseline.md"))
    welcome_template: str = Field(default_factory=lambda: load_prompt_md("welcome.md"))
    language_template: str = Field(
        default_factory=lambda: load_prompt_md("language.md")
    )

    talk_to_me: TalkToMe = Field(default_factory=TalkToMe)


prompt_loader = PromptLoader()


def convert_base_to_specific(message: BaseMessage):
    if message.type == "human":
        return HumanMessage(
            content=message.content,
            additional_kwargs=message.additional_kwargs,
            response_metadata=message.response_metadata,
        )
    elif message.type == "ai":
        return AIMessage(
            content=message.content,
            additional_kwargs=message.additional_kwargs,
            response_metadata=message.response_metadata,
        )
    elif message.type == "system":
        return SystemMessage(
            content=message.content,
            additional_kwargs=message.additional_kwargs,
            response_metadata=message.response_metadata,
        )
    else:
        raise ValueError(f"Unknown message type: {message.type}")
