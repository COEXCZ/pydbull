import pydantic
import pytest

import pydbull
import django.db.models


def test_get_django_instance() -> None:
    class DjangoModel(django.db.models.Model):
        name = django.db.models.CharField(max_length=100)

    @pydbull.model_validator(DjangoModel)
    class TestModel(pydantic.BaseModel):
        name: str

    pyd_model = TestModel(name="test")
    dj_instance = pydbull.get_adapter(pyd_model).get_model_instance(pyd_model)
    assert type(dj_instance) is DjangoModel
    assert dj_instance.name == "test"


def test_get_django_instance_with_extra_field() -> None:
    class DjangoModel(django.db.models.Model):
        name = django.db.models.CharField(max_length=100)

    @pydbull.model_validator(DjangoModel)
    class TestModel(pydantic.BaseModel):
        name: str
        some_extra_field: str

    pyd_model = TestModel(name="test", some_extra_field="extra")
    dj_instance = pydbull.get_adapter(pyd_model).get_model_instance(pyd_model)
    assert type(dj_instance) is DjangoModel
    assert dj_instance.name == "test"
    with pytest.raises(AttributeError):
        dj_instance.some_extra_field


def test_get_django_instance_with_nested_object() -> None:
    class NestedDjangoModel(django.db.models.Model):
        name = django.db.models.CharField(max_length=100)

    class DjangoModel(django.db.models.Model):
        nested = django.db.models.ForeignKey(NestedDjangoModel, on_delete=django.db.models.CASCADE)

    @pydbull.model_validator(NestedDjangoModel)
    class NestedModel(pydantic.BaseModel):
        name: str

    @pydbull.model_validator(DjangoModel)
    class TestModel(pydantic.BaseModel):
        nested: NestedModel

    pyd_model = TestModel(nested=NestedModel(name="test"))
    dj_instance = pydbull.get_adapter(pyd_model).get_model_instance(pyd_model)
    assert type(dj_instance) is DjangoModel
    assert type(dj_instance.nested) is NestedDjangoModel
    assert dj_instance.nested.name == "test"


def test_get_django_instance_skips_m2m() -> None:
    """
    M2M fields should be skipped when setting the Django instance, as they are not directly settable.
    """
    class NestedDjangoModel(django.db.models.Model):
        name = django.db.models.CharField(max_length=100)

    class DjangoModel(django.db.models.Model):
        nested_list = django.db.models.ManyToManyField(NestedDjangoModel)

    @pydbull.model_validator(NestedDjangoModel)
    class NestedModel(pydantic.BaseModel):
        name: str

    @pydbull.model_validator(DjangoModel)
    class TestModel(pydantic.BaseModel):
        nested_list: list[NestedModel]

    pyd_model = TestModel(nested_list=[NestedModel(name="test")])
    dj_instance = pydbull.get_adapter(pyd_model).get_model_instance(pyd_model)  # If the M2M field was set, this would raise an error.
    assert type(dj_instance) is DjangoModel
