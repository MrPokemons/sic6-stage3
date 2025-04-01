from typing import TypeAlias, Annotated, Any
from pydantic import Field, AfterValidator
from pydantic.json_schema import SkipJsonSchema


ExcludedField: TypeAlias = SkipJsonSchema[
    Annotated[
        Any, 
        Field(default=None, exclude=True),
        AfterValidator(lambda x: None)
    ]
]