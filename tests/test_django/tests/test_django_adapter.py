import pydantic
import pytest
import pytest_mock
import pydbull

from django.core.validators import (
    MaxValueValidator, MinLengthValidator, RegexValidator, MinValueValidator,
    StepValueValidator, URLValidator,
)
from django.core.exceptions import ValidationError as DjValidationError
from django.db.models import (
    CharField, Model as DjangoModel, IntegerField, TextField, EmailField, DecimalField,
    ForeignKey, CASCADE, ManyToManyField, UniqueConstraint, CheckConstraint, Q,
)
from django.utils.translation import gettext_lazy as _
from pydantic_core import PydanticUndefined

INT_MAX: int = 9223372036854775807
INT_MIN: int = -9223372036854775808


def test_get_default() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_default(CharField(max_length=10)) == PydanticUndefined
    assert adapter.get_default(CharField(max_length=10, blank=True)) == ""
    assert adapter.get_default(IntegerField()) == PydanticUndefined
    assert adapter.get_default(IntegerField(null=True)) == PydanticUndefined
    assert adapter.get_default(IntegerField(null=True, blank=True)) is None
    assert adapter.get_default(IntegerField(default=42)) == 42
    # If Django default is callable, uses "default_factory" in pydantic model
    assert adapter.get_default(IntegerField(default=lambda: 42)) == PydanticUndefined


def test_get_default_factory() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_default_factory(CharField(max_length=10)) == PydanticUndefined
    assert adapter.get_default_factory(CharField(max_length=10, default=lambda: "TEST"))() == "TEST"
    assert adapter.get_default_factory(IntegerField(default=42)) == PydanticUndefined
    assert adapter.get_default_factory(IntegerField(default=lambda: 42))() == 42


def test_get_max_length() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_max_length(CharField(max_length=10)) == 10
    assert adapter.get_max_length(TextField(max_length=20)) == 20
    assert adapter.get_max_length(EmailField(max_length=30)) == 30


def test_get_min_length() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_min_length(CharField(validators=[MinLengthValidator(5)])) == 5
    assert adapter.get_min_length(TextField(validators=[MinLengthValidator(10)])) == 10
    assert adapter.get_min_length(EmailField(validators=[MinLengthValidator(25)])) == 25


def test_get_pattern() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_pattern(CharField(validators=[RegexValidator(r"^[A-Z].*$")])) == "^[A-Z].*$"
    assert adapter.get_pattern(TextField(validators=[RegexValidator(r"^[A-Z].*$")])) == "^[A-Z].*$"
    assert adapter.get_pattern(EmailField(validators=[RegexValidator(r"^[A-Z].*$")])) == "^[A-Z].*$"


def test_get_pattern_skips_url_validator() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    # Skip URLValidator because the regex is too complex for pydantic to handle.
    assert adapter.get_pattern(CharField(validators=[URLValidator()])) is None


def test_get_greater_than() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    # Django only has "greater than or equal", not "greater than"
    assert adapter.get_greater_than(IntegerField(validators=[MinValueValidator(5)])) == PydanticUndefined
    assert adapter.get_greater_than(DecimalField(validators=[MinValueValidator(5)])) == PydanticUndefined


def test_get_greater_than_or_equal() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_greater_than_or_equal(IntegerField()) == INT_MIN
    assert adapter.get_greater_than_or_equal(DecimalField()) == PydanticUndefined
    assert adapter.get_greater_than_or_equal(IntegerField(validators=[MinValueValidator(5)])) == 5
    assert adapter.get_greater_than_or_equal(DecimalField(validators=[MinValueValidator(7)])) == 7


def test_get_less_than() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    # Django only has "less than or equal", not "less than"
    assert adapter.get_less_than(IntegerField(validators=[MaxValueValidator(5)])) == PydanticUndefined
    assert adapter.get_less_than(DecimalField(validators=[MaxValueValidator(5)])) == PydanticUndefined


def test_get_less_than_or_equal() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_less_than_or_equal(IntegerField(validators=[MaxValueValidator(5)])) == 5
    assert adapter.get_less_than_or_equal(DecimalField(validators=[MaxValueValidator(7)])) == 7


def test_get_multiple_of() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_multiple_of(IntegerField(validators=[StepValueValidator(5)])) == 5
    assert adapter.get_multiple_of(DecimalField(validators=[StepValueValidator(7)])) == 7
    # Pydantic "multiple of" validator does not work with offset as Django does - skipped if Django has it.
    assert adapter.get_multiple_of(IntegerField(validators=[StepValueValidator(5, offset=3)])) == PydanticUndefined
    assert adapter.get_multiple_of(DecimalField(validators=[StepValueValidator(7, offset=1)])) == PydanticUndefined


def test_get_description() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_description(IntegerField(help_text="Some description.")) == "Some description."
    assert adapter.get_description(IntegerField(help_text=_("Some description."))) == "Some description."


def test_get_decimal_max_digits() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_decimal_max_digits(DecimalField(max_digits=5)) == 5
    assert adapter.get_decimal_max_digits(DecimalField(max_digits=None)) == PydanticUndefined


def test_get_decimal_places() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    assert adapter.get_decimal_places(DecimalField(decimal_places=5)) == 5
    assert adapter.get_decimal_places(DecimalField(decimal_places=None)) == PydanticUndefined


def test_run_extra_field_validators() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model

    try:
        adapter.run_extra_field_validators(CharField(max_length=5), value="ABCDE")
    except Exception:
        assert False

    with pytest.raises(pydantic.ValidationError) as err:
        adapter.run_extra_field_validators(CharField(max_length=5), value="ABCDEF")
    assert len(err.value.errors()) == 1
    error_data = err.value.errors()[0]
    assert error_data["type"] == "too_long"
    assert error_data["input"] == "ABCDEF"
    assert error_data["msg"] == "Ensure this value has at most 5 characters (it has 6)."
    assert error_data["loc"] == ()
    assert error_data["ctx"] == {}


def test_run_extra_field_validators_with_custom_validator() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model

    def custom_validator(value: str) -> None:
        if value == "NOT_ALLOWED":
            raise DjValidationError(message="Value can not be NOT_ALLOWED.", params={"value": value})

    try:
        adapter.run_extra_field_validators(CharField(validators=[custom_validator]), value="OK")
    except Exception:
        assert False

    with pytest.raises(pydantic.ValidationError) as err:
        adapter.run_extra_field_validators(CharField(validators=[custom_validator]), value="NOT_ALLOWED")
    assert len(err.value.errors()) == 1
    error_data = err.value.errors()[0]
    assert error_data["type"] == "value_error"
    assert error_data["input"] == "NOT_ALLOWED"
    assert error_data["msg"] == "Value can not be NOT_ALLOWED."
    assert error_data["loc"] == ()
    assert error_data["ctx"] == {}


def test_run_extra_field_validators_with_multiple_validators() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model

    def custom_validator(value: str) -> None:
        if value == "NOT_ALLOWED":
            raise DjValidationError(message="Value can not be NOT_ALLOWED.", params={"value": value})

    try:
        adapter.run_extra_field_validators(CharField(max_length=5, validators=[custom_validator]), value="OK")
    except Exception:
        assert False

    with pytest.raises(pydantic.ValidationError) as err:
        adapter.run_extra_field_validators(CharField(max_length=5, validators=[custom_validator]), value="NOT_ALLOWED")
    assert err.value.errors() == [
        {
            'ctx': {},
            'input': 'NOT_ALLOWED',
            'loc': (),
            'msg': 'Value can not be NOT_ALLOWED.',
            'type': 'value_error',
        },
        {
            'ctx': {},
            'input': 'NOT_ALLOWED',
            'loc': (),
            'msg': 'Ensure this value has at most 5 characters (it has 11).',
            'type': 'too_long',
        },
    ]


def test_run_extra_model_validators(mocker: pytest_mock.MockFixture) -> None:
    class Model(DjangoModel):
        name = CharField(max_length=5)

        class Meta:
            constraints = [
                UniqueConstraint(fields=["name"], name="unique_name"),
                CheckConstraint(check=~Q(name="INVALID"), name="check_name"),
            ]

    adapter = pydbull.DjangoAdapter(Model)
    pyd_model = adapter.model_to_pydantic()

    uc_mock = mocker.patch.object(UniqueConstraint, "validate")
    cc_mock = mocker.patch.object(CheckConstraint, "validate")
    adapter.run_extra_model_validators(pyd_model(name="TEST"), context=None)
    cc_mock.assert_called()
    uc_mock.assert_called()


def test_run_extra_model_validators_with_errors(mocker: pytest_mock.MockFixture) -> None:
    class Model(DjangoModel):
        name = CharField(max_length=9999)

        class Meta:
            constraints = [
                UniqueConstraint(fields=["name"], name="unique_name"),
                CheckConstraint(check=~Q(name="INVALID"), name="check_name"),
            ]

    adapter = pydbull.DjangoAdapter(Model)
    pyd_model = adapter.model_to_pydantic()

    mocker.patch.object(UniqueConstraint, "validate", side_effect=DjValidationError(code="uc_test", message="UC error"))
    mocker.patch.object(CheckConstraint, "validate", side_effect=DjValidationError(code="cc_test", message="CC error"))
    with pytest.raises(pydantic.ValidationError) as err:
        adapter.run_extra_model_validators(pyd_model(name="TEST"), context=None)
    assert len(err.value.errors()) == 2
    assert err.value.errors() == [
        {
            'ctx': {},
            'input': None,
            'loc': (),
            'msg': 'UC error',
            'type': 'uc_test',
        }, {
            'ctx': {},
            'input': None,
            'loc': (),
            'msg': 'CC error',
            'type': 'cc_test',
        }
    ]


def test_convert_to_pydantic_exception() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model

    django_exc = DjValidationError(
        code="test_code",
        message="Some message",
    )
    pyd_exc = adapter.convert_to_pydantic_exception(django_exc)
    assert pyd_exc.error_count(), 1
    error_data = pyd_exc.errors()[0]
    assert error_data["type"] == "test_code"
    assert error_data["input"] is None
    assert error_data["msg"] == "Some message"
    assert error_data["loc"] == ()
    assert error_data["ctx"] == {}


def test_convert_to_pydantic_exception_django_error_dict() -> None:
    adapter = pydbull.DjangoAdapter(DjangoModel)  # any model
    error_dict = {}
    DjValidationError(
        code="field_1_test_code",
        message="Field 1 message",
    ).update_error_dict(error_dict)
    DjValidationError(
        code="field_2_test_code",
        message="Field 2 message",
    ).update_error_dict(error_dict)

    pyd_exc = adapter.convert_to_pydantic_exception(DjValidationError(error_dict))
    assert pyd_exc.error_count(), 2
    assert pyd_exc.errors() == [
        {
            'ctx': {},
            'input': None,
            'loc': (),
            'msg': 'Field 1 message',
            'type': 'field_1_test_code',
        },
        {
            'ctx': {},
            'input': None,
            'loc': (),
            'msg': 'Field 2 message',
            'type': 'field_2_test_code',
        },
    ]


def test_model_to_pydantic_char_field() -> None:
    class Model(DjangoModel):
        char_field = CharField(
            max_length=5,
            validators=[
                MinLengthValidator(2),
                RegexValidator(r"^[A-Z].*$"),
            ],
            help_text=_("Char field description")
        )
        char_field_blank = CharField(
            max_length=10,
            blank=True,
        )

    adapter = pydbull.DjangoAdapter(Model)
    pyd_model = adapter.model_to_pydantic()
    pyd_adapter = pydbull.PydanticAdapter(pyd_model)
    assert len(pyd_model.__pydantic_fields__) == 3  # including ID
    assert pyd_adapter.get_max_length(pyd_model.__pydantic_fields__["char_field"]) == 5
    assert pyd_adapter.get_min_length(pyd_model.__pydantic_fields__["char_field"]) == 2
    assert pyd_adapter.get_pattern(pyd_model.__pydantic_fields__["char_field"]) == "^[A-Z].*$"
    assert pyd_adapter.get_default(pyd_model.__pydantic_fields__["char_field"]) == PydanticUndefined
    assert pyd_adapter.get_default_factory(pyd_model.__pydantic_fields__["char_field"]) == PydanticUndefined
    assert pyd_adapter.get_description(pyd_model.__pydantic_fields__["char_field"]) == "Char field description"

    assert pyd_adapter.get_max_length(pyd_model.__pydantic_fields__["char_field_blank"]) == 10
    assert pyd_adapter.get_min_length(pyd_model.__pydantic_fields__["char_field_blank"]) == PydanticUndefined
    assert pyd_adapter.get_default(pyd_model.__pydantic_fields__["char_field_blank"]) == ""
    assert pyd_adapter.get_default_factory(pyd_model.__pydantic_fields__["char_field_blank"]) == PydanticUndefined
    assert pyd_adapter.get_description(pyd_model.__pydantic_fields__["char_field_blank"]) == ""


def test_model_to_pydantic_pk_field() -> None:
    class Model(DjangoModel):
        pass

    adapter = pydbull.DjangoAdapter(Model)
    pyd_model = adapter.model_to_pydantic()
    pyd_adapter = pydbull.PydanticAdapter(pyd_model)
    assert len(pyd_model.__pydantic_fields__) == 1
    pyd_field = pyd_model.__pydantic_fields__["id"]
    assert pyd_adapter.get_default(pyd_field) is None
    assert pyd_adapter.get_default_factory(pyd_field) == PydanticUndefined
    assert pyd_adapter.get_max_length(pyd_field) == PydanticUndefined
    assert pyd_adapter.get_min_length(pyd_field) == PydanticUndefined
    assert pyd_adapter.get_pattern(pyd_field) == PydanticUndefined
    assert pyd_adapter.get_greater_than(pyd_field) == PydanticUndefined
    assert pyd_adapter.get_greater_than_or_equal(pyd_field) == INT_MIN
    assert pyd_adapter.get_less_than(pyd_field) == PydanticUndefined
    assert pyd_adapter.get_less_than_or_equal(pyd_field) == INT_MAX
    assert pyd_adapter.get_multiple_of(pyd_field) == PydanticUndefined
    assert pyd_adapter.get_description(pyd_field) == ""
    assert pyd_adapter.get_decimal_max_digits(pyd_field) == PydanticUndefined
    assert pyd_adapter.get_decimal_places(pyd_field) == PydanticUndefined


def test_model_to_pydantic_fields_argument() -> None:
    class Model(DjangoModel):
        field_1 = IntegerField()
        field_2 = CharField()

    adapter = pydbull.DjangoAdapter(Model)
    pyd_model = adapter.model_to_pydantic(fields=["field_2"])
    assert len(pyd_model.__pydantic_fields__) == 1
    assert "field_2" in pyd_model.__pydantic_fields__


def test_model_to_pydantic_fields_argument_for_non_existing_field() -> None:
    class Model(DjangoModel):
        field_1 = IntegerField()
        field_2 = CharField()

    adapter = pydbull.DjangoAdapter(Model)
    with pytest.raises(ValueError) as err:
        adapter.model_to_pydantic(fields=["field_1", "field_other"])

    assert str(err.value) == "Field `field_other` not found in `Model` model."


def test_model_to_pydantic_exclude_argument() -> None:
    class Model(DjangoModel):
        field_1 = IntegerField()
        field_2 = CharField()

    adapter = pydbull.DjangoAdapter(Model)
    pyd_model = adapter.model_to_pydantic(exclude=["id", "field_2"])
    assert len(pyd_model.__pydantic_fields__) == 1
    assert "field_1" in pyd_model.__pydantic_fields__


def test_model_to_pydantic_exclude_argument_for_non_existing_field() -> None:
    class Model(DjangoModel):
        field_1 = IntegerField()
        field_2 = CharField()

    adapter = pydbull.DjangoAdapter(Model)
    with pytest.raises(ValueError) as err:
        adapter.model_to_pydantic(exclude=["field_other", "field_2"])

    assert str(err.value) == "Field `field_other` not found in `Model` model."


def test_model_to_pydantic_field_annotations_argument() -> None:
    class Model(DjangoModel):
        field_1 = IntegerField()
        field_2 = CharField()

    adapter = pydbull.DjangoAdapter(Model)
    pyd_model = adapter.model_to_pydantic(field_annotations={"field_1": pydantic.Field(ge=2, description="TEST")})
    pyd_adapter = pydbull.PydanticAdapter(pyd_model)
    assert pyd_adapter.get_greater_than_or_equal(pyd_model.__pydantic_fields__["field_1"]) == 2
    assert pyd_adapter.get_description(pyd_model.__pydantic_fields__["field_1"]) == "TEST"


def test_model_to_pydantic_field_annotations_argument_for_non_existing_field() -> None:
    class Model(DjangoModel):
        field_1 = IntegerField()
        field_2 = CharField()

    adapter = pydbull.DjangoAdapter(Model)
    with pytest.raises(ValueError) as err:
        adapter.model_to_pydantic(field_annotations={"field_other": pydantic.Field(ge=2)})

    assert str(err.value) == "Field `field_other` not found in `Model` model."


def test_model_to_pydantic_foreign_key() -> None:
    class ModelOne(DjangoModel):
        pass

    class ModelTwo(DjangoModel):
        fk_field = ForeignKey(ModelOne, on_delete=CASCADE)
        fk_field_not_required = ForeignKey(ModelOne, null=True, blank=True, on_delete=CASCADE)

    adapter = pydbull.DjangoAdapter(ModelTwo)
    pyd_model = adapter.model_to_pydantic()

    assert len(pyd_model.__pydantic_fields__) == 3  # with ID
    assert pyd_model.__pydantic_fields__["fk_field"].annotation is int
    assert pyd_model.__pydantic_fields__["fk_field_not_required"].annotation == int | None


def test_model_to_pydantic_m2m() -> None:
    class ModelOne(DjangoModel):
        pass

    class ModelTwo(DjangoModel):
        m2m_field = ManyToManyField(ModelOne)
        m2m_field_blank = ManyToManyField(ModelOne, blank=True)

    adapter = pydbull.DjangoAdapter(ModelTwo)
    pyd_model = adapter.model_to_pydantic()
    pyd_adapter = pydbull.PydanticAdapter(pyd_model)

    assert len(pyd_model.__pydantic_fields__) == 3  # with ID
    assert pyd_model.__pydantic_fields__["m2m_field"].annotation == list[int]
    assert pyd_model.__pydantic_fields__["m2m_field_blank"].annotation == list[int] | None
    assert pyd_adapter.get_min_length(pyd_model.__pydantic_fields__["m2m_field"]) == 1
    assert pyd_adapter.get_min_length(pyd_model.__pydantic_fields__["m2m_field_blank"]) == PydanticUndefined
