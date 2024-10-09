import pydantic
from pydantic_core import PydanticUndefined

import pydbull

PYD_ADAPTER = pydbull.PydanticAdapter(pydantic.BaseModel)


def test_get_default() -> None:
    assert PYD_ADAPTER.get_default(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_default(pydantic.Field(default="default")) == "default"


def test_get_default_factory() -> None:
    assert PYD_ADAPTER.get_default_factory(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_default_factory(pydantic.Field(default_factory=lambda: "default"))() == "default"


def test_get_max_length() -> None:
    assert PYD_ADAPTER.get_max_length(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_max_length(pydantic.Field(max_length=1)) == 1


def test_get_min_length() -> None:
    assert PYD_ADAPTER.get_min_length(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_min_length(pydantic.Field(min_length=1)) == 1


def test_get_pattern() -> None:
    assert PYD_ADAPTER.get_pattern(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_pattern(pydantic.Field(pattern="pattern")) == "pattern"


def test_get_greater_than() -> None:
    assert PYD_ADAPTER.get_greater_than(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_greater_than(pydantic.Field(gt=1)) == 1


def test_get_greater_than_or_equal() -> None:
    assert PYD_ADAPTER.get_greater_than_or_equal(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_greater_than_or_equal(pydantic.Field(ge=1)) == 1


def test_get_less_than() -> None:
    assert PYD_ADAPTER.get_less_than(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_less_than(pydantic.Field(lt=1)) == 1


def test_get_less_than_or_equal() -> None:
    assert PYD_ADAPTER.get_less_than_or_equal(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_less_than_or_equal(pydantic.Field(le=1)) == 1


def test_get_multiple_of() -> None:
    assert PYD_ADAPTER.get_multiple_of(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_multiple_of(pydantic.Field(multiple_of=2)) == 2


def test_get_description() -> None:
    assert PYD_ADAPTER.get_description(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_description(pydantic.Field(description="description")) == "description"


def test_get_decimal_max_digits() -> None:
    assert PYD_ADAPTER.get_decimal_max_digits(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_decimal_max_digits(pydantic.Field(max_digits=1)) == 1


def test_get_decimal_places() -> None:
    assert PYD_ADAPTER.get_decimal_places(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_decimal_places(pydantic.Field(decimal_places=1)) == 1


def test_get_strict() -> None:
    assert PYD_ADAPTER.get_strict(pydantic.Field()) is False
    assert PYD_ADAPTER.get_strict(pydantic.Field(strict=False)) is False
    assert PYD_ADAPTER.get_strict(pydantic.Field(strict=True)) is True


def test_get_coerce_numbers_to_str() -> None:
    assert PYD_ADAPTER.get_coerce_numbers_to_str(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_coerce_numbers_to_str(pydantic.Field(coerce_numbers_to_str=False)) is False
    assert PYD_ADAPTER.get_coerce_numbers_to_str(pydantic.Field(coerce_numbers_to_str=True)) is True


def test_get_allow_inf_nan() -> None:
    assert PYD_ADAPTER.get_allow_inf_nan(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_allow_inf_nan(pydantic.Field(allow_inf_nan=False)) is False
    assert PYD_ADAPTER.get_allow_inf_nan(pydantic.Field(allow_inf_nan=True)) is True


def test_get_union_mode() -> None:
    assert PYD_ADAPTER.get_union_mode(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_union_mode(pydantic.Field(union_mode="smart")) == "smart"
    assert PYD_ADAPTER.get_union_mode(pydantic.Field(union_mode="left_to_right")) == "left_to_right"


def test_get_fail_fast() -> None:
    assert PYD_ADAPTER.get_fail_fast(pydantic.Field()) == PydanticUndefined
    assert PYD_ADAPTER.get_fail_fast(pydantic.Field(fail_fast=False)) is False
    assert PYD_ADAPTER.get_fail_fast(pydantic.Field(fail_fast=True)) is True
