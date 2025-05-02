from typing import TypeVar, TypeAlias, Union, Sequence, List


T = TypeVar("T")
OneOrMany: TypeAlias = Union[T, List[T]]

def one_or_many(value: T) -> List[T]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return list(value)
    return [value]
