from typing import TypeAlias, Literal, Union, Dict
from pydantic import BaseModel, Field, AliasChoices


OllamaModels: TypeAlias = Literal["qwen2.5:3b"]
class OllamaSettings(BaseModel):
    name: OllamaModels = Field(validation_alias=AliasChoices("name", "model", "model_name"))


ModelProviders: TypeAlias = Literal[
    "ollama"
]  # list of providers

ModelProviderSettings: TypeAlias = Union[
    OllamaSettings
]  # provider settings

ModelsProvided: TypeAlias = Union[
    OllamaModels
]  # list of models from every existing providers

ModelValidations: Dict[ModelProviders, ModelsProvided] = {
    "ollama": OllamaModels
}