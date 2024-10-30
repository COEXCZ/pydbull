import importlib.util
import types
import typing
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import annotated_types
import django.core.exceptions
import django.core.validators
import django.db.models
import django.db.models.options
import pydantic.fields
import pydantic_core
from pydantic_core import PydanticUndefined, PydanticUndefinedType

import pydbull
from pydbull import _utils as utils

__all__ = [
    "DjangoAdapter",
]

FieldT = django.db.models.Field


class DjangoAdapter[ModelT: django.db.models.Model](pydbull.BaseAdapter[ModelT]):
    @typing.override
    def get_default(self, field: FieldT) -> typing.Any:
        if field.default == django.db.models.fields.NOT_PROVIDED and self._field_is_required(field):
            return PydanticUndefined
        if type(field.default) is types.FunctionType:
            # if callable, use `get_default_factory`
            return PydanticUndefined
        return field.get_default()

    @typing.override
    def get_default_factory(self, field: FieldT) -> typing.Callable[[], typing.Any] | PydanticUndefinedType | None:
        if field.default == django.db.models.fields.NOT_PROVIDED and self._field_is_required(field):
            return PydanticUndefined
        if type(field.default) is not types.FunctionType:
            # if not callable, use `get_default`
            return PydanticUndefined
        return field.get_default

    @typing.override
    def get_max_length(self, field: FieldT) -> int | None:
        return field.max_length

    @typing.override
    def get_min_length(self, field: FieldT) -> int | None:
        validator = self._get_validator(django.core.validators.MinLengthValidator, field)
        if validator:
            return validator.limit_value

        array_fields = django.db.models.ManyToManyField
        try:
            from django.contrib.postgres.fields import ArrayField

            array_fields |= ArrayField
        except ImportError:
            pass

        if isinstance(field, array_fields) and self._field_is_required(field):
            return 1
        return None

    @typing.override
    def get_pattern(self, field: FieldT) -> str | PydanticUndefinedType | None:
        validator = self._get_validator(django.core.validators.RegexValidator, field)
        skip_validators: set[type] = {
            # Skip URLValidator because the regex is too complex for pydantic to handle.
            # The validation is therefore done only in Django (see `run_extra_field_validators`).
            django.core.validators.URLValidator,
        }
        if validator and type(validator) not in skip_validators:
            return validator.regex.pattern
        return None

    @typing.override
    def get_greater_than(self, field: FieldT) -> PydanticUndefinedType:
        # not supported by django model
        return PydanticUndefined

    @typing.override
    def get_greater_than_or_equal(self, field: FieldT) -> annotated_types.SupportsGt | PydanticUndefinedType:
        validator = self._get_validator(django.core.validators.MinValueValidator, field)
        if validator:
            return validator.limit_value
        return PydanticUndefined

    @typing.override
    def get_less_than(self, field: FieldT) -> PydanticUndefinedType:
        # not supported by django model
        return PydanticUndefined

    @typing.override
    def get_less_than_or_equal(self, field: FieldT) -> annotated_types.SupportsLt | PydanticUndefinedType:
        validator = self._get_validator(django.core.validators.MaxValueValidator, field)
        if validator:
            return validator.limit_value
        return PydanticUndefined

    @typing.override
    def get_multiple_of(
        self,
        field: FieldT,
    ) -> annotated_types.SupportsDiv | annotated_types.SupportsMod | PydanticUndefinedType:
        validator = self._get_validator(django.core.validators.StepValueValidator, field)
        if not validator:
            return PydanticUndefined
        if validator.offset not in [0, None]:
            # pydantic doesn't support offset
            return PydanticUndefined
        return validator.limit_value

    @typing.override
    def get_description(self, field: FieldT) -> str | None:
        return field.help_text

    @typing.override
    def get_decimal_max_digits(self, field: FieldT) -> int | PydanticUndefinedType:
        if isinstance(field, django.db.models.DecimalField):
            return field.max_digits if field.max_digits is not None else PydanticUndefined
        return PydanticUndefined

    @typing.override
    def get_decimal_places(self, field: FieldT) -> int | PydanticUndefinedType:
        if isinstance(field, django.db.models.DecimalField):
            return field.decimal_places if field.decimal_places is not None else PydanticUndefined
        return PydanticUndefined

    # TODO remove from here, add in vercajk as an extension
    @typing.override
    def field_pre_check(self, field: str, validator_field: pydantic.fields.FieldInfo) -> None:
        dj_model_field = self.field_getter(field)
        if dj_model_field is None:
            return
        dj_model_field_is_optional: bool = dj_model_field.null or not self._field_is_required(dj_model_field)
        # TODO check if the field is enum that the all the validator choices are in the model enum (dont need to be all)
        if not dj_model_field_is_optional and utils.pydantic_field_is_optional(validator_field):
            raise ValueError(
                f"`{self.model.__name__}.{field}` field required in the django model, but not it's validator.",
            )

    @typing.override
    def run_extra_field_validators(self, field: FieldT, value: typing.Any) -> typing.Any:
        """
        Run a django validator on a value.
        Why not just call the validator?
        Because pydantic field validators *need to return the value* and this value is then passed to the later
        validators and used as the value of the field.
        This allows pydantic validators to modify the value, but is incompatible with django validators
        which only check the value, raise an exception if it's invalid and return None.
        """
        if value is None and isinstance(field, django.db.models.CharField) and not field.null:
            # Automatically convert Null value to empty string if the field is non-nullable CharField.
            value = ""
        if value in django.core.validators.EMPTY_VALUES:
            return value

        errors: list[django.core.exceptions.ValidationError] = []
        for validator in field.validators:
            try:
                validator(value)
            except django.core.exceptions.ValidationError as django_exc:
                pyd_error_code = self._validator_to_pydantic_error_code(type(validator))
                if pyd_error_code is not None:
                    django_exc.code = pyd_error_code
                errors.append(django_exc)

        if errors:
            raise self.convert_to_pydantic_exception(django.core.exceptions.ValidationError(errors))
        return value

    @staticmethod
    @typing.override
    def run_extra_model_validators[T: "pydantic.BaseModel"](
        pyd_model: T,
        context: pydantic.ValidationInfo,
    ) -> T:
        instance: ModelT = pydbull.get_adapter(pyd_model).get_model_instance(pyd_model)
        if not instance:
            return pyd_model

        if instance.pk:
            # ensures that unique=True fields are not checked against the instance itself
            instance._state.adding = False  # noqa: SLF001

        errors: dict[typing.LiteralString, list[django.core.exceptions.ValidationError]] = {}
        try:
            instance.validate_unique()
        except django.core.exceptions.ValidationError as exc:
            errors = exc.update_error_dict(errors)
        try:
            instance.validate_constraints()
        except django.core.exceptions.ValidationError as exc:
            errors = exc.update_error_dict(errors)
        if errors:
            raise pydbull.get_adapter(pyd_model).convert_to_pydantic_exception(
                django.core.exceptions.ValidationError(errors),
            )
        return pyd_model

    @typing.override
    def field_getter(self, field: str) -> FieldT | None:
        try:
            return self.model._meta.get_field(field)  # noqa: SLF001
        except django.core.exceptions.FieldDoesNotExist:
            # Is just a validator model field, nothing to add from the django model.
            return None

    @classmethod
    @typing.override
    def convert_to_pydantic_exception(cls, exc: django.core.exceptions.ValidationError) -> pydantic.ValidationError:
        loc_to_errors: dict[str | None, list[django.core.exceptions.ValidationError]] = {}
        try:
            loc_to_errors = exc.error_dict
        except AttributeError:
            # Case when we don't know which field this belongs to.
            # "__all__" is set by Django model constraint validators, so use it here also to match the behavior.
            loc_to_errors[django.core.exceptions.NON_FIELD_ERRORS] = exc.error_list
        return pydantic.ValidationError.from_exception_data(
            "Model validation error",
            line_errors=[
                {
                    "type": pydantic_core.PydanticCustomError(
                        error.code if error.code else "value_error",
                        ". ".join(error.messages),
                        {},
                    ),
                    "loc": () if loc == django.core.exceptions.NON_FIELD_ERRORS else (loc,),  # TODO handle if nested
                    "input": error.params.get("value") if error.params else None,
                }
                for loc, errors in loc_to_errors.items()
                for error in errors
            ],
        )

    def model_field_to_annotation_type(self, field: FieldT) -> type:
        try:
            field_type = _FIELD_TO_PYD_TYPE[type(field)]
        except KeyError as e:
            # TODO - add more; search in base classes
            raise ValueError(
                f"Unsupported field type: {type(field).__name__} on field {field.model.__name__}.{field.name}",
            ) from e
        if type(field_type) is types.FunctionType:
            return field_type(field)
        return field_type

    def model_to_pydantic[T: pydantic.BaseModel](  # noqa: C901
        self,
        *,
        name: str | None = None,
        fields: typing.Collection[str] | None = None,
        exclude: typing.Collection[str] | None = None,
        field_annotations: dict[str, pydantic.fields.FieldInfo] | None = None,
        __base__: type[T] | None = None,
    ) -> type["pydantic.BaseModel"] | type[T]:
        """
        Create a pydantic model from a django model.
        :param name: Name of the pydantic model.
        :param fields: Fields from the Django model to include in the pydantic model.
        :param exclude: Fields from the Django model to exclude from the pydantic model.
        :param field_annotations: Any extra annotations for the fields in the pydantic model.
            Use as: {<field_name>: pydantic.Field(...), ...}
        """

        def check_fields_exist_on_model(fields_: typing.Collection[str]) -> None:
            model_fields: set[str] = {f.name for f in dj_model_fields}
            for f in fields_:
                if f not in model_fields:
                    raise ValueError(f"Field `{f}` not found in `{self.model.__name__}` model.")

        if name is None:
            name = f"{self.model.__name__}Validator"

        if fields is not None and exclude is not None:
            raise ValueError("Cannot specify both `fields` and `exclude`.")
        if field_annotations is None:
            field_annotations = {}
        model_meta: django.db.models.options.Options = self.model._meta  # noqa: SLF001
        dj_model_fields: list[django.db.models.Field] = model_meta.get_fields()
        check_fields_exist_on_model(field_annotations.keys())
        if fields is not None:
            check_fields_exist_on_model(fields)
            dj_model_fields = [f for f in dj_model_fields if f.name in fields]
        elif exclude is not None:
            check_fields_exist_on_model(exclude)
            dj_model_fields = [f for f in dj_model_fields if f.name not in exclude]

        name_to_field: dict[str, django.db.models.Field] = {f.name: f for f in dj_model_fields}
        field_to_type: dict[str, type] = {}
        for field_name, field in name_to_field.items():
            field_type = self.model_field_to_annotation_type(field)
            if not self._field_is_required(field):
                field_type = field_type | None
            field_to_type[field.name] = typing.Annotated[
                field_type,
                field_annotations.get(field_name, pydantic.Field()),
            ]

        pyd_model = pydantic.create_model(
            name,
            __base__=(__base__,) if __base__ else (pydantic.BaseModel,),
            **field_to_type,
        )
        return pydbull.model_validator(self.model)(pyd_model)

    @typing.override
    def get_model_instance(
        self,
        data: pydantic.BaseModel,
    ) -> ModelT:
        if django_pk := getattr(self, self.model._meta.pk.name, None):  # noqa: SLF001:
            instance: ModelT = self.model.objects.get(pk=django_pk)
        else:
            instance = self.model()

        for field_name in data.model_fields.keys():
            field_value: typing.Any = getattr(data, field_name)
            try:
                django_field: django.db.models.Field | None = instance._meta.get_field(field_name)  # noqa: SLF001
            except django.core.exceptions.FieldDoesNotExist:
                # Not a model field - nothing to do
                continue
            if django_field.many_to_many:
                # Prevents "TypeError: Direct assignment to the forward side of a many-to-many set is prohibited."
                continue

            is_fk_field = isinstance(django_field, django.db.models.ForeignKey)
            if isinstance(field_value, pydantic.BaseModel):
                field_value: pydantic.BaseModel
                if not is_fk_field:
                    # Case where a validator is used on a non-relationship field - something is wrong, for now just
                    # raise an error.
                    raise ValueError(
                        f"Field '{field_name}' is a `{type(self).__name__}` but the model"
                        f" `{self.model.__name__}.{django_field.name} is not "
                        f"a {django.db.models.ForeignKey.__name__}.",
                    )
                setattr(instance, field_name, pydbull.get_adapter(field_value).get_model_instance(field_value))
            elif is_fk_field:
                # If the field is a ForeignKey, we need to set the field to the validator instance.
                setattr(instance, f"{field_name}_id", field_value)
            else:
                setattr(instance, field_name, field_value)
        return instance

    @classmethod
    @typing.override
    def get_exception_class(cls) -> type[Exception]:
        return django.core.exceptions.ValidationError

    def _get_validator[T](
        self,
        validator_cls: type[T],
        field: FieldT,
    ) -> T | None:
        for validator in field.validators:
            if isinstance(validator, validator_cls):
                return validator
        return None

    @classmethod
    def _validator_to_pydantic_error_code(cls, validator: type) -> typing.LiteralString | None:
        """
        Map the Django error codes to pydantic ones.
        This is so that the error codes are consistent no matter whether the validation fails in Django or Pydantic.
        """
        mapping: dict[type, pydantic_core.ErrorType] = {
            django.core.validators.EmailValidator: "value_error",
            django.core.validators.MinLengthValidator: "too_short",
            django.core.validators.MaxLengthValidator: "too_long",
            django.core.validators.StepValueValidator: "multiple_of",
        }
        return mapping.get(validator)

    def _field_is_required(self, field: FieldT) -> bool:
        return not field.blank


EmailStr = pydantic.EmailStr if importlib.util.find_spec("email_validator") is not None else str


# TODO add more as needed
_FIELD_TO_PYD_TYPE: dict[type[django.db.models.Field], type | typing.Callable[[django.db.models.Field], type]] = {
    django.db.models.CharField: lambda field: _try_enum_type(field, str),
    django.db.models.TextField: str,
    django.db.models.IntegerField: lambda field: _try_enum_type(field, int),
    django.db.models.BigIntegerField: lambda field: _try_enum_type(field, int),
    django.db.models.SmallIntegerField: lambda field: _try_enum_type(field, int),
    django.db.models.PositiveSmallIntegerField: lambda field: _try_enum_type(field, int),
    django.db.models.PositiveBigIntegerField: lambda field: _try_enum_type(field, int),
    django.db.models.BigAutoField: int,
    django.db.models.ForeignKey: int,
    django.db.models.ManyToManyField: list[int],
    django.db.models.AutoField: int,
    django.db.models.FloatField: float,
    django.db.models.DecimalField: Decimal,
    django.db.models.BooleanField: bool,
    django.db.models.DateField: date,
    django.db.models.TimeField: time,
    django.db.models.DateTimeField: datetime,
    django.db.models.EmailField: EmailStr,
    django.db.models.URLField: str,
    django.db.models.UUIDField: str,
    django.db.models.GenericIPAddressField: str,
    django.db.models.FileField: str,
    django.db.models.ImageField: str,
    django.db.models.BinaryField: bytes,
    django.db.models.DurationField: timedelta,
    django.db.models.SlugField: str,
}


def _try_enum_type[T: type](field: django.db.models.Field, default: T) -> T | type[django.db.models.Choices]:
    try:
        choices_enum = field.__choices_enum__
    except AttributeError:
        return default

    if not issubclass(choices_enum, django.db.models.Choices):
        raise TypeError(f"Field `{field.name}` has invalid choices enum: {choices_enum}")
    return choices_enum
