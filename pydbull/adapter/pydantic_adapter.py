import typing

import annotated_types
import pydantic.fields
from pydantic_core import PydanticUndefined, PydanticUndefinedType

from pydbull.adapter import BaseAdapter

__all__ = [
    "PydanticAdapter",
]


FieldT = pydantic.fields.FieldInfo


class PydanticAdapter[ModelT: pydantic.BaseModel](BaseAdapter[ModelT]):
    ValidationError = pydantic.ValidationError

    @typing.override
    def get_default(self, field: FieldT) -> typing.Any:
        return field.default

    @typing.override
    def get_default_factory(self, field: FieldT) -> typing.Callable[[], typing.Any] | PydanticUndefinedType | None:
        if field.default_factory is None:
            return PydanticUndefined
        return field.default_factory

    @typing.override
    def get_max_length(self, field: FieldT) -> int | PydanticUndefinedType:
        validator = self._get_validator(annotated_types.MaxLen, field)
        return validator.max_length if validator else PydanticUndefined

    @typing.override
    def get_min_length(self, field: FieldT) -> int | PydanticUndefinedType:
        validator = self._get_validator(annotated_types.MinLen, field)
        return validator.min_length if validator else PydanticUndefined

    @typing.override
    def get_pattern(self, field: FieldT) -> str | PydanticUndefinedType | None:
        for meta in field.metadata:
            if hasattr(meta, "pattern"):
                return meta.pattern
        return PydanticUndefined

    @typing.override
    def get_greater_than(self, field: FieldT) -> annotated_types.SupportsGt | PydanticUndefinedType:
        validator = self._get_validator(annotated_types.Gt, field)
        return validator.gt if validator else PydanticUndefined

    @typing.override
    def get_greater_than_or_equal(
        self,
        field: FieldT,
    ) -> annotated_types.SupportsGe | PydanticUndefinedType:
        validator = self._get_validator(annotated_types.Ge, field)
        return validator.ge if validator else PydanticUndefined

    @typing.override
    def get_less_than(self, field: FieldT) -> annotated_types.SupportsLt | PydanticUndefinedType:
        validator = self._get_validator(annotated_types.Lt, field)
        return validator.lt if validator else PydanticUndefined

    @typing.override
    def get_less_than_or_equal(self, field: FieldT) -> annotated_types.SupportsLe | PydanticUndefinedType:
        validator = self._get_validator(annotated_types.Le, field)
        return validator.le if validator else PydanticUndefined

    @typing.override
    def get_multiple_of(
        self,
        field: FieldT,
    ) -> annotated_types.SupportsDiv | annotated_types.SupportsMod | PydanticUndefinedType:
        validator = self._get_validator(annotated_types.MultipleOf, field)
        return validator.multiple_of if validator else PydanticUndefined

    @typing.override
    def get_description(self, field: FieldT) -> str | PydanticUndefinedType:
        return field.description if field.description is not None else PydanticUndefined

    @typing.override
    def get_decimal_max_digits(self, field: FieldT) -> int | PydanticUndefinedType:
        for meta in field.metadata:
            if hasattr(meta, "max_digits"):
                return meta.max_digits
        return PydanticUndefined

    @typing.override
    def get_decimal_places(self, field: FieldT) -> int | PydanticUndefinedType:
        for meta in field.metadata:
            if hasattr(meta, "decimal_places"):
                return meta.decimal_places
        return PydanticUndefined

    def get_strict(self, field: FieldT) -> bool:
        validator = self._get_validator(pydantic.Strict, field)
        return validator.strict if validator else False

    def get_coerce_numbers_to_str(self, field: FieldT) -> bool | PydanticUndefinedType:
        for meta in field.metadata:
            if hasattr(meta, "coerce_numbers_to_str"):
                return meta.coerce_numbers_to_str
        return PydanticUndefined

    def get_allow_inf_nan(self, field: FieldT) -> bool | PydanticUndefinedType:
        for meta in field.metadata:
            if hasattr(meta, "allow_inf_nan"):
                return meta.allow_inf_nan
        return PydanticUndefined

    def get_union_mode(self, field: FieldT) -> typing.Literal["smart", "left_to_right"] | PydanticUndefinedType:
        for meta in field.metadata:
            if hasattr(meta, "union_mode"):
                return meta.union_mode
        return PydanticUndefined

    def get_fail_fast(self, field: FieldT) -> bool | PydanticUndefinedType:
        validator = self._get_validator(pydantic.FailFast, field)
        return validator.fail_fast if validator else PydanticUndefined

    @typing.override
    def field_getter(self, field: str) -> FieldT | None:
        try:
            return self.model.model_fields[field]
        except KeyError:
            return None

    @classmethod
    @typing.override
    def convert_to_pydantic_exception(cls, exc: pydantic.ValidationError) -> pydantic.ValidationError:
        return exc

    @classmethod
    @typing.override
    def get_exception_class(cls) -> type[Exception]:
        return cls.ValidationError

    @typing.override
    def model_to_pydantic(
        self,
        *,
        name: str | None = None,
        fields: typing.Collection[str] | None = None,
        exclude: typing.Collection[str] | None = None,
        field_annotations: dict[str, pydantic.fields.FieldInfo] | None = None,
        __base__: type[pydantic.BaseModel] | None = None,
    ) -> type["pydantic.BaseModel"]:
        return self.model

    @typing.override
    def get_model_instance(
        self,
        data: "pydantic.BaseModel",
    ) -> ModelT:
        return data

    def _get_validator[T: annotated_types.BaseMetadata](
        self,
        validator_cls: type[T],
        field: FieldT,
    ) -> T | None:
        for meta in field.metadata:
            if isinstance(meta, validator_cls):
                return meta
        return None
