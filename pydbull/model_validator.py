import typing

import pydantic
import pydantic.fields
import pydantic_core

import pydbull

__all__ = [
    "model_validator",
    "model_to_pydantic",
    "get_model",
    "get_adapter",
]


def model_validator( # noqa: ANN201
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
        pydantic_adapter = pydbull.PydanticAdapter(input_validator)
        pydantic_fields: dict[str, tuple[type, pydantic.Field]] = {}
        pydantic_method_validators: dict[str, typing.Callable] = {}  # method_name: method
        for field_name, pyd_field_info in input_validator.model_fields.items():
            adapter.field_pre_check(field_name, pyd_field_info)
            model_field = adapter.field_getter(field_name)
            if model_field is None:
                # The Field is not present in the model, just in the pydantic validator - nothing to add from the model.
                continue

            adapters: list[pydbull.BaseAdapter] = [pydantic_adapter, adapter]
            # Reconstruct the field with values enriched by the model adapter.
            default = _get_field_value(field_name, adapters, adapter.get_default)
            if default is pydantic_core.PydanticUndefined:
                default_factory = _get_field_value(field_name, adapters, adapter.get_default_factory)
            else:
                default_factory = pydantic_core.PydanticUndefined
            pydantic_fields[field_name] = (
                pyd_field_info.annotation,
                pydantic.Field(
                    # Fields enriched by the model ################
                    default=default,
                    default_factory=default_factory,
                    max_length=_get_field_value(field_name, adapters, adapter.get_max_length),
                    min_length=_get_field_value(field_name, adapters, adapter.get_min_length),
                    pattern=_get_field_value(field_name, adapters, adapter.get_pattern),
                    gt=_get_field_value(field_name, adapters, adapter.get_greater_than),
                    ge=_get_field_value(field_name, adapters, adapter.get_greater_than_or_equal),
                    lt=_get_field_value(field_name, adapters, adapter.get_less_than),
                    le=_get_field_value(field_name, adapters, adapter.get_less_than_or_equal),
                    max_digits=_get_field_value(field_name, adapters, adapter.get_decimal_max_digits),
                    decimal_places=_get_field_value(field_name, adapters, adapter.get_decimal_places),
                    multiple_of=_get_field_value(field_name, adapters, adapter.get_multiple_of),
                    description=_get_field_value(field_name, adapters, adapter.get_description),
                    # Only pydantic fields ##############################
                    alias=pyd_field_info.alias,
                    alias_priority=pyd_field_info.alias_priority,
                    validation_alias=pyd_field_info.validation_alias,
                    serialization_alias=pyd_field_info.serialization_alias,
                    title=pyd_field_info.title,
                    field_title_generator=pyd_field_info.field_title_generator,
                    examples=pyd_field_info.examples,
                    exclude=pyd_field_info.exclude,
                    discriminator=pyd_field_info.discriminator,
                    deprecated=pyd_field_info.deprecated,
                    json_schema_extra=pyd_field_info.json_schema_extra,
                    frozen=pyd_field_info.frozen,
                    validate_default=pyd_field_info.validate_default,
                    repr=pyd_field_info.repr,
                    init=pyd_field_info.init,
                    init_var=pyd_field_info.init_var,
                    kw_only=pyd_field_info.kw_only,
                    strict=pydantic_adapter.get_strict(pyd_field_info),
                    coerce_numbers_to_str=pydantic_adapter.get_coerce_numbers_to_str(pyd_field_info),
                    allow_inf_nan=pydantic_adapter.get_allow_inf_nan(pyd_field_info),
                    union_mode=pydantic_adapter.get_union_mode(pyd_field_info),
                    fail_fast=pydantic_adapter.get_fail_fast(pyd_field_info),
                ),
            )
            # The same as putting @pydantic.field_validator(field_name) decorator on a method
            # which contains the validator logic.
            pydantic_method_validators[f"pydbull_{field_name}_field_extra_validators"] = (
                pydantic.field_validator(field_name)(
                    lambda value, field=model_field: adapter.run_extra_field_validators(field=field, value=value),
                )
            )

        # The same as putting @pydantic.model_validator decorator on a method which contains the validator logic.
        pydantic_method_validators["pydbull_model_extra_validators"] = (
            typing.cast(
                callable,
                pydantic.model_validator(mode="after")(
                    adapter.run_extra_model_validators,
                ),
            )
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
        model: typing.Any, # noqa: ANN401
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


def _select_adapter(model: typing.Any) -> type["pydbull.BaseAdapter"]: # noqa: ANN401
    # TODO make it easy to override default adapter from settings
    try:
        import django.db.models
        if issubclass(model, django.db.models.Model):
            return pydbull.DjangoAdapter
    except ImportError:
        # Django not installed
        pass
    raise NotImplementedError(f"Adapter for {model} not implemented")


def _get_field_value(
        field: str,
        adapters: list["pydbull.BaseAdapter"],
        method: typing.Callable[[object], typing.Any],
) -> typing.Any:  # noqa: ANN401
    """
    Iterate over the adapters and return a first defined value.
    """
    for adapter in adapters:
        ad_field = adapter.field_getter(field)
        if ad_field is None:
            continue
        val = getattr(adapter, method.__name__)(ad_field)
        if val is not pydantic_core.PydanticUndefined:
            return val
    return pydantic_core.PydanticUndefined
