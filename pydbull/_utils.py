import types
import typing
import pydantic.fields

__all__ = [
    "pydantic_field_is_optional",
]


def pydantic_field_is_optional(field: pydantic.fields.FieldInfo) -> bool:
    """
    Returns True for field typed as `typing.Optional[int]`, `int | None`, `typing.Union[int, None]`.
    """
    t = field.annotation
    return typing.get_origin(t) in (types.UnionType, typing.Union) and type(None) in typing.get_args(t)
