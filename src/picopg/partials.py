"""Provides a function to dynamically create partial Pydantic models.

This module contains the `Partial` function, which is used to create a new
`BaseModel` subclass where all fields are marked as optional. This is useful
for creating "query by example" filters.
"""

from __future__ import annotations

from typing import Type, TypeVar

from pydantic import create_model

from .models import BaseModel

T = TypeVar("T", bound=BaseModel)


def Partial(model_class: Type[T]) -> Type[T]:
    """Dynamically creates a new Pydantic model with all fields optional.

    This function is used to support "query by example" by creating a partial
    version of a `BaseModel` subclass.

    Args:
        model_class: The `BaseModel` subclass to make partial.

    Returns:
        A new `BaseModel` subclass where all fields are optional.
    """
    fields = {
        name: (field.annotation or None, None)
        for name, field in model_class.model_fields.items()
    }
    return create_model(
        f"Partial{model_class.__name__}",
        **fields,
        __base__=model_class,
    )
