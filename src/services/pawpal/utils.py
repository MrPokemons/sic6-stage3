import os
from pydantic import BaseModel, Field


PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt_md(filename: str) -> str:
    with open(os.path.join(PROMPT_DIR, filename), "r", encoding="utf8") as f:
        return f.read()


class PromptLoader(BaseModel):
    # Core Flow
    baseline: str = Field(default_factory=lambda: load_prompt_md("baseline.md"))
    welcome_template: str = Field(default_factory=lambda: load_prompt_md("welcome.md"))
    language_template: str = Field(
        default_factory=lambda: load_prompt_md("language.md")
    )


prompt_loader = PromptLoader()
