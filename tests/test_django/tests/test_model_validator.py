import typing

import django.core.exceptions
import pydantic
import pydantic_core
import pytest
from django.core.validators import MinLengthValidator
from django.db import models

import pydbull


def test_model_validator_attributes_set() -> None:
    class DjangoModelModelValidator(models.Model):
        field_1 = models.IntegerField()

    @pydbull.model_validator(DjangoModelModelValidator)
    class PydbullDjangoModel(pydantic.BaseModel):
        field_1: str

    assert issubclass(PydbullDjangoModel, pydantic.BaseModel)
    assert PydbullDjangoModel.__pydbull_model__ == DjangoModelModelValidator
    assert type(PydbullDjangoModel.__pydbull_adapter__) is pydbull.DjangoAdapter
    assert PydbullDjangoModel.__pydbull_adapter__.model is DjangoModelModelValidator
    assert PydbullDjangoModel.__name__ == "PydbullDjangoModel"
    assert hasattr(PydbullDjangoModel, "pydbull_field_1_field_extra_validators")
    assert hasattr(PydbullDjangoModel, "pydbull_model_extra_validators")


def test_model_validator_inherits_validators_from_the_model() -> None:
    class DjangoModelModelValidator(models.Model):
        field_1 = models.CharField(max_length=100, verbose_name="field 1")

    @pydbull.model_validator(DjangoModelModelValidator)
    class PydbullDjangoModel(pydantic.BaseModel):
        field_1: str

    pyd_adapter = pydbull.PydanticAdapter(PydbullDjangoModel)
    assert pyd_adapter.get_max_length(PydbullDjangoModel.model_fields["field_1"]) == 100


def test_model_validator_inherited_validators_from_model_can_be_overridden() -> None:
    class DjangoModelModelValidator(models.Model):
        field_1 = models.CharField(
            max_length=100,
            validators=[
                MinLengthValidator(5),
            ],
            verbose_name="field 1",
        )

    @pydbull.model_validator(DjangoModelModelValidator)
    class PydbullDjangoModel(pydantic.BaseModel):
        field_1: typing.Annotated[str, pydantic.Field(max_length=50)]

    pyd_adapter = pydbull.PydanticAdapter(PydbullDjangoModel)
    assert pyd_adapter.get_max_length(PydbullDjangoModel.model_fields["field_1"]) == 50
    assert pyd_adapter.get_min_length(PydbullDjangoModel.model_fields["field_1"]) == 5


def test_model_to_pydantic() -> None:
    class DjangoModelModelValidator(models.Model):
        field_1 = models.CharField(max_length=100, verbose_name="field 1")

    pyd_model = pydbull.model_to_pydantic(DjangoModelModelValidator)

    pyd_model = pyd_model(field_1="test")
    assert pyd_model.field_1 == "test"
    assert pyd_model.model_dump() == {
        "field_1": "test",
        "id": None
    }


def test_get_pydbull_model() -> None:
    class DjangoModelModelValidator(models.Model):
        field_1 = models.IntegerField()

    @pydbull.model_validator(DjangoModelModelValidator)
    class PydbullDjangoModel(pydantic.BaseModel):
        field_1: str

    assert pydbull.get_model(PydbullDjangoModel) is DjangoModelModelValidator


def test_get_pydbull_adapter() -> None:
    class DjangoModelModelValidator(models.Model):
        field_1 = models.IntegerField()

    @pydbull.model_validator(DjangoModelModelValidator)
    class PydbullDjangoModel(pydantic.BaseModel):
        field_1: str

    assert type(pydbull.get_adapter(PydbullDjangoModel)) is pydbull.django.DjangoAdapter
    assert pydbull.get_adapter(PydbullDjangoModel).model is DjangoModelModelValidator


def test_custom_validators_on_django_model() -> None:
    def name_not_pepa(value: str) -> None:
        if value.lower() == "pepa":
            raise django.core.exceptions.ValidationError(
                code="dont_try_to_impersonate_pepa",
                message="There is only one Pepa and you are not him.",
                params={},
            )
        return

    class User(models.Model):
        name = models.CharField(
            max_length=100,
            validators=[MinLengthValidator(2), name_not_pepa],
        )

    @pydbull.model_validator(User)
    class UserModel(pydantic.BaseModel):
        name: str

    with pytest.raises(pydantic.ValidationError) as exc:
        UserModel(name="pepa")
    assert len(exc.value.errors()) == 1
    error = exc.value.errors()[0]
    assert error["loc"] == ("name",)
    assert error["msg"] == "There is only one Pepa and you are not him."
    assert error["type"] == "dont_try_to_impersonate_pepa"
    assert error["ctx"] == {}

    with pytest.raises(pydantic.ValidationError) as exc:
        UserModel(name="p")
    assert len(exc.value.errors()) == 1
    error = exc.value.errors()[0]
    assert error["loc"] == ("name",)
    assert error["msg"] == "String should have at least 2 characters"
    assert error["type"] == "string_too_short"
    assert error["ctx"] == {
        "min_length": 2
    }


def test_custom_validators_on_pydantic_model() -> None:
    class User(models.Model):
        name = models.CharField(
            max_length=100,
            validators=[MinLengthValidator(2)],
        )

    @pydbull.model_validator(User)
    class UserModel(pydantic.BaseModel):
        name: str

        @pydantic.field_validator("name")
        @classmethod
        def name_not_pepa(cls, value: str) -> str:
            if value.lower() == "pepa":
                raise pydantic.ValidationError.from_exception_data(
                    "UserModel validation error",
                    line_errors=[
                        {
                            "type": pydantic_core.PydanticCustomError(
                                "dont_try_to_impersonate_pepa",
                                "You can't impersonate Pepa",
                                {},
                            ),
                            "input": value,
                        },
                        {
                            "type": pydantic_core.PydanticCustomError(
                                "dont_try_to_impersonate_pepa_2",
                                "You really shouldn't",
                                {},
                            ),
                            "input": value,
                        },
                    ],
                )
            return value


    with pytest.raises(pydantic.ValidationError) as exc:
        UserModel(name="pepa")
    assert exc.value.errors() == [
        {
            'ctx': {},
            'input': 'pepa',
            'loc': ('name',),
            'msg': "You can't impersonate Pepa",
            'type': 'dont_try_to_impersonate_pepa'
        }, {
            'ctx': {},
            'input': 'pepa',
            'loc': ('name',),
            'msg': "You really shouldn't",
            'type': 'dont_try_to_impersonate_pepa_2'
        }
    ]

    with pytest.raises(pydantic.ValidationError) as exc:
        UserModel(name="p")
    assert len(exc.value.errors()) == 1
    error = exc.value.errors()[0]
    assert error["loc"] == ("name",)
    assert error["msg"] == "String should have at least 2 characters"
    assert error["type"] == "string_too_short"
    assert error["ctx"] == {
        "min_length": 2
    }


def test_custom_methods_on_pydantic_model() -> None:
    class User(models.Model):
        name = models.CharField(max_length=100)

    @pydbull.model_validator(User)
    class UserModel(pydantic.BaseModel):
        name: str

        def some_method(self) -> int:
            return 42

    user = UserModel(name="test")
    assert user.some_method() == 42


def test_custom_property_on_pydantic_model() -> None:
    class User(models.Model):
        name = models.CharField(max_length=100)

    @pydbull.model_validator(User)
    class UserModel(pydantic.BaseModel):
        name: str

        @property
        def some_property(self) -> int:
            return 42

    user = UserModel(name="test")
    assert user.some_property == 42



def test_custom_computed_property_on_pydantic_model() -> None:
    class Rectangle(models.Model):
        width = models.IntegerField()
        length = models.IntegerField()

    @pydbull.model_validator(Rectangle)
    class RectangleModel(pydantic.BaseModel):
        width: int
        length: int

        @pydantic.computed_field
        @property
        def area(self) -> int:
            return self.width * self.length

    rectangle = RectangleModel(width=10, length=5)
    assert rectangle.area == 50

