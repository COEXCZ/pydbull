import abc
import typing

import annotated_types
import pydantic.fields
from pydantic_core import PydanticUndefinedType

__all__ = [
    "BaseAdapter",
]


class BaseAdapter[ModelT: object](abc.ABC):
    """
    Adapter for extracting validation information from a model (for example, Django model) and its fields.
    """

    def __init__(self, model: type[ModelT]) -> None:
        self.model: type[ModelT] = model

    def field_pre_check(self, field: str, validator_field: pydantic.fields.FieldInfo) -> None:  # noqa: ARG002
        """
        Hook to perform any necessary checks on the field before extracting validation information.
        """
        return

    def run_extra_field_validators(self, field: object, value: typing.Any) -> typing.Any:  # noqa: ARG002 ANN401
        """
        Run any extra validators on the field and return the processed field value.
        :raise pydantic.ValidationError: If the field value is invalid.
        """
        return value

    @staticmethod
    def run_extra_model_validators[T: pydantic.BaseModel](
        pyd_model: T,
        context: pydantic.ValidationInfo,  # noqa: ARG004
    ) -> T:
        """
        Run any extra validators on the model and return the processed model.
        (e.g., function decorated by @pydantic.model_validator(mode="after"))
        :raise pydantic.ValidationError: If the model is invalid.
        """
        return pyd_model

    @abc.abstractmethod
    def get_max_length(self, field: object) -> int | PydanticUndefinedType | None:
        """
        Get the maximum length of the field.
        """

    @abc.abstractmethod
    def get_min_length(self, field: object) -> int | PydanticUndefinedType | None:
        """
        Get the minimum length of the field.
        """

    @abc.abstractmethod
    def get_pattern(self, field: object) -> str | PydanticUndefinedType | None:
        """
        Get the regex pattern of the field.
        """

    @abc.abstractmethod
    def get_greater_than(self, field: object) -> annotated_types.SupportsGt | PydanticUndefinedType | None:
        """
        Get the greater than value of the field.
        """

    @abc.abstractmethod
    def get_greater_than_or_equal(self, field: object) -> annotated_types.SupportsGe | PydanticUndefinedType | None:
        """
        Get the greater than or equal value of the field.
        """

    @abc.abstractmethod
    def get_less_than(self, field: object) -> annotated_types.SupportsLt | PydanticUndefinedType | None:
        """
        Get the less than value of the field.
        """

    @abc.abstractmethod
    def get_less_than_or_equal(self, field: object) -> annotated_types.SupportsLe | PydanticUndefinedType | None:
        """
        Get the less than or equal value of the field.
        """

    @abc.abstractmethod
    def get_multiple_of(
        self,
        field: object,
    ) -> annotated_types.SupportsDiv | annotated_types.SupportsMod | PydanticUndefinedType | None:
        """
        Get the multiple of value of the field value (for example, 2 for even numbers).
        """

    @abc.abstractmethod
    def get_description(self, field: object) -> str | PydanticUndefinedType | None:
        """
        Get the description of the field.
        """

    @abc.abstractmethod
    def get_default(self, field: object) -> typing.Any:  # noqa: ANN401
        """
        Get the default value of the field.
        """

    @abc.abstractmethod
    def get_default_factory(self, field: object) -> typing.Callable[[], typing.Any] | PydanticUndefinedType | None:
        """
        Get the default factory of the field.
        """

    @abc.abstractmethod
    def get_decimal_max_digits(self, field: object) -> int | PydanticUndefinedType | None:
        """
        Get the maximum number of digits in the decimal field.
        """

    @abc.abstractmethod
    def get_decimal_places(self, field: object) -> int | PydanticUndefinedType | None:
        """
        Get the maximum number of decimal places in the decimal field.
        """

    @abc.abstractmethod
    def field_getter(self, field: str) -> typing.Any:  # noqa: ANN401
        """
        Function to retrieve the model field from the model.
        """

    @classmethod
    @abc.abstractmethod
    def convert_to_pydantic_exception(cls, exc: Exception) -> pydantic.ValidationError:
        """
        Convert the model exception to a Pydantic validation error.
        """

    @classmethod
    @abc.abstractmethod
    def get_exception_class(cls) -> type[Exception]:
        """
        Get the exception class of the model.
        """

    @typing.overload
    def model_to_pydantic[T: pydantic.BaseModel](
        self,
        *,
        name: str | None = None,
        fields: typing.Literal[None] = None,
        exclude: typing.Collection[str] | None = None,
        field_annotations: dict[str, pydantic.fields.FieldInfo] | None = None,
        __base__: type[T] | None = None,
    ) -> type["pydantic.BaseModel"] | type[T]:
        pass

    @typing.overload
    def model_to_pydantic[T: pydantic.BaseModel](
        self,
        *,
        name: str | None = None,
        fields: typing.Collection[str] | None = None,
        exclude: typing.Literal[None] = None,
        field_annotations: dict[str, pydantic.fields.FieldInfo] | None = None,
        __base__: type[T] | None = None,
    ) -> type["pydantic.BaseModel"] | type[T]:
        pass

    @abc.abstractmethod
    def model_to_pydantic[T: pydantic.BaseModel](
        self,
        *,
        name: str | None = None,
        fields: typing.Collection[str] | None = None,
        exclude: typing.Collection[str] | None = None,
        field_annotations: dict[str, pydantic.fields.FieldInfo] | None = None,
        __base__: type[T] | None = None,
    ) -> type["pydantic.BaseModel"] | type[T]:
        """
        Create a pydantic model from self.model.
        :param name: Name of the pydantic model.
        :param fields: Fields from self.model to include in the pydantic model.
        :param exclude: Fields from the self.model to exclude from the pydantic model.
        :param field_annotations: Any extra annotations for the fields in the pydantic model.
            Use as: {<field_name>: pydantic.Field(...), ...}
        :param __base__: Base of the pydantic model.
        """

    @abc.abstractmethod
    def get_model_instance(
        self,
        data: "pydantic.BaseModel",
    ) -> ModelT:
        """
        Get the instance of the model.
        To be overridden by the subclasses.
        """
