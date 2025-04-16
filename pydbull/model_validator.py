import typing

import pydantic
import pydantic.fields

import pydbull

__all__ = [
    "model_validator",
    "model_to_pydantic",
    "get_model",
    "get_adapter",
]


def model_validator(  # noqa: ANN201
    model: type,
    adapter_cls: type["pydbull.BaseAdapter"] | None = None,
):
    """
    Decorator to create a pydantic and

    :param model:
    :param adapter_cls:
    :return:
    """
    if adapter_cls is None:
        adapter_cls = _select_adapter(model)

    def wrapper[T: pydantic.BaseModel](input_validator: type[T]) -> type[T]:
        adapter = adapter_cls(model)
        pydantic_fields: dict[str, tuple[type, pydantic.Field]] = {}
        pydantic_method_validators: dict[str, typing.Callable] = {}  # method_name: method
        for field_name, pyd_field_info in input_validator.model_fields.items():
            adapter.field_pre_check(field_name, pyd_field_info)
            model_field = adapter.field_getter(field_name)
            if model_field is None:
                # The Field is not present in the model, just in the pydantic validator - nothing to add from the model.
                continue

            # Field enriched with additional information from the model.
            enriched_field: pydantic.fields.FieldInfo = pydantic.Field(
                default=adapter.get_default(model_field),
                default_factory=adapter.get_default_factory(model_field),
                max_length=adapter.get_max_length(model_field),
                min_length=adapter.get_min_length(model_field),
                pattern=adapter.get_pattern(model_field),
                gt=adapter.get_greater_than(model_field),
                ge=adapter.get_greater_than_or_equal(model_field),
                lt=adapter.get_less_than(model_field),
                le=adapter.get_less_than_or_equal(model_field),
                max_digits=adapter.get_decimal_max_digits(model_field),
                decimal_places=adapter.get_decimal_places(model_field),
                multiple_of=adapter.get_multiple_of(model_field),
                description=adapter.get_description(model_field),
            )
            pydantic_fields[field_name] = (
                pyd_field_info.annotation,
                pydantic.fields.FieldInfo.merge_field_infos(enriched_field, pyd_field_info),
            )
            # The same as putting @pydantic.field_validator(field_name) decorator on a method
            # which contains the validator logic.
            pydantic_method_validators[f"pydbull_{field_name}_field_extra_validators"] = pydantic.field_validator(
                field_name,
            )(
                lambda value, field=model_field: adapter.run_extra_field_validators(field=field, value=value),
            )

        # The same as putting @pydantic.model_validator decorator on a method which contains the validator logic.
        pydantic_method_validators["pydbull_model_extra_validators"] = typing.cast(
            callable,
            pydantic.model_validator(mode="after")(
                adapter.run_extra_model_validators,
            ),
        )

        # Need to re-create the pydantic model, because there is no other way (AFAIK) how to add validators to an
        # existing model.
        # Because we're setting the original validator as base, we inherit its methods.
        pyd_model: type[pydantic.BaseModel] = pydantic.create_model(
            input_validator.__name__.removesuffix("Validator"),
            __base__=(input_validator,),
            __validators__=pydantic_method_validators,
            **pydantic_fields,
        )
        pyd_model.__pydbull_model__ = model
        pyd_model.__pydbull_adapter__ = adapter
        return pyd_model

    return wrapper


def model_to_pydantic[T: pydantic.BaseModel](
    model: typing.Any,  # noqa: ANN401
    name: str | None = None,
    fields: typing.Collection[str] | None = None,
    exclude: typing.Collection[str] | None = None,
    field_annotations: dict[str, pydantic.fields.FieldInfo] | None = None,
    __base__: type[T] | None = None,
) -> type[pydantic.BaseModel] | type[T]:
    """
    Convenience function to create a pydantic model from a model (e.g., Django model).
    :param model: Model to create a pydantic model from.
    :param name: Name of the pydantic model.
    :param fields: Fields from model to include in the pydantic model.
    :param exclude: Fields from the model to exclude from the pydantic model.
    :param field_annotations: Any extra annotations for the fields in the pydantic model.
        Use as: {<field_name>: pydantic.Field(...), ...}
    :param __base__: Base of the pydantic model.
    """
    adapter_cls = _select_adapter(model)
    adapter = adapter_cls(model)
    return adapter.model_to_pydantic(
        name=name,
        fields=fields,
        exclude=exclude,
        field_annotations=field_annotations,
        __base__=__base__,
    )


def get_model(model: type[pydantic.BaseModel] | pydantic.BaseModel, /) -> type:
    """
    Get the validated class for a model.
    """
    try:
        return model.__pydbull_model__  # Set in `@model_validator` decorator
    except AttributeError as e:
        raise TypeError(
            f"No pydbull model found. Did you forget to use the @{model_validator.__name__} decorator?",
        ) from e


def get_adapter(model: type[pydantic.BaseModel] | pydantic.BaseModel, /) -> "pydbull.BaseAdapter":
    """
    Get the adapter for a model.
    """
    try:
        return model.__pydbull_adapter__  # Set in `@model_validator` decorator
    except AttributeError as e:
        raise TypeError(
            f"No pydbull adapter found. Did you forget to use the @{model_validator.__name__} decorator?",
        ) from e


def _select_adapter(model: typing.Any) -> type["pydbull.BaseAdapter"]:  # noqa: ANN401
    # TODO make it easy to override default adapter from settings
    try:
        import django.db.models

        if issubclass(model, django.db.models.Model):
            return pydbull.DjangoAdapter
    except ImportError:
        # Django not installed
        pass
    raise NotImplementedError(f"Adapter for {model} not implemented")
