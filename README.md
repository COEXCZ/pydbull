# Pydbull
Pydbull is a library for building Pydantic models from other data models (such as Django models).
It is designed to inherit the original model's validation rules.

_The name pydbull is a portmanteau of _pydantic_ and _builder_, and a play on the word pitbull as a 
guard-dog for your data._


## Installation

```bash
pip install pydbull
```

# Usage & examples

## Functions and methods
### `@model_validator` decorator
The `@model_validator` decorator is used to inherit validation rules from any supported data model (e.g., Django model).
For example:
```python
import pydbull
import pydantic
from django.db import models


class User(models.Model):
    name = models.CharField(max_length=5)
    age = models.IntegerField()


@pydbull.model_validator(User)
class UserModel(pydantic.BaseModel):
    name: str


# The following will raise a ValidationError
UserModel(name="ABCDEF")
```

This will make the `UserModel` model inherit the validation rules from the `User` model, meaning that
the `UserModel.name` field will have a maximum length of 5 characters.


The pydantic model can be extended with additional fields, methods or validators just like any other pydantic model.
```python
import pydbull
import pydantic
from django.db import models


class User(models.Model):
    name = models.CharField(max_length=100)


@pydbull.model_validator(User)
class UserModel(pydantic.BaseModel):
    name: str
    age: int

    @pydantic.field_validator("age")
    def validate_age(cls, v: int) -> int:
        if v < 18:
            raise ValueError("Age must be over 18.")
        return v


# The following will raise a ValidationError
UserModel(name="John", age=17)
```

If the Django model has some additional constraints, the pydantic model will inherit and validate them as well.

```python
import pydbull
import pydantic
from django.db import models
from django.core.validators import MinValueValidator


class User(models.Model):
    age = models.IntegerField(validators=[MinValueValidator(5)])


@pydbull.model_validator(User)
class UserModel(pydantic.BaseModel):
    age: int


# The following will raise a ValidationError
UserModel(age=4)
```



### `model_to_pydantic` function
The `model_to_pydantic` function is used to build a Pydantic model from a supported data model (e.g., Django model). 
For example:
```python
import pydbull
import pydantic
from django.db import models
from django.core.validators import MinValueValidator


class DjangoModel(models.Model):
    field_1 = models.CharField(max_length=5, help_text="Some help text (will be inherited by Pydantic model)")
    field_2 = models.IntegerField(validators=[MinValueValidator(5)])


PydanticModelCls = pydbull.model_to_pydantic(DjangoModel)

pyd_model = PydanticModelCls(field_1="test", field_2=5)
assert pyd_model.model_dump() == {
    "field_1": "test",
    "field_2": 5,
    "id": None
}


# The following will raise a ValidationError
PydanticModelCls(field_1="test", field_2=4)


# You can use `fields` parameter to specify which fields to include in the Pydantic model.
pydbull.model_to_pydantic(DjangoModel, fields=["field_1"])
# You can also use `exclude` parameter to specify which fields to exclude from the Pydantic model.
pydbull.model_to_pydantic(DjangoModel, exclude=["id"])
# You can use `field_annotations` parameter to specify additional field annotations for the Pydantic model.
pydbull.model_to_pydantic(DjangoModel, field_annotations={"field_1": pydantic.Field(max_length=2, description="Some description")})
```

## Integrations
Currently, Pydbull supports the following data models:
- Django models

To see how to extend Pydbull to support other data models, see the [Extending Pydbull](#extending-pydbull) section.


## Extending Pydbull
Pydbull can be extended to support other data models by implementing `Adapter` class for the data model type.
The `Adapter` class should inherit from ABC class `pydbull.BaseAdapter` and implement it's abstract methods.
For example, see the implementation of `DjangoAdapter` class in `pydbull.django` module.


## Contributing
Pull requests for any improvements are welcome.

[Poetry](https://github.com/sdispater/poetry) is used to manage dependencies.
To get started follow these steps:

```shell
git clone https://github.com/coexcz/pydbull
cd pydbull
poetry install
poetry run pytest
```

### Pre commit

We have a configuration for
[pre-commit](https://github.com/pre-commit/pre-commit), to add the hook run the
following command:

```shell
pre-commit install
```
