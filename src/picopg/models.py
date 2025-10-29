"""Defines the base model for the PicoPG ORM.

This module contains the `BaseModel` class, which serves as the foundation for
all database models in the PicoPG library. It provides automatic table name
inference, primary key detection, and schema support.
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

from psycopg.sql import SQL, Composed, Identifier
from pydantic import BaseModel as PydanticBaseModel
from psycopg.sql import SQL, Identifier, Composed


class BaseModel(PydanticBaseModel):
    """Base class for database models."""

    __table_name__: ClassVar[str]
    __primary_key__: ClassVar[str]
    __schema__: ClassVar[str | None] = None

    @classmethod
    def get_table_name(cls) -> str:
        if "__table_name__" in cls.__dict__:
            return cls.__dict__["__table_name__"]
        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()

    @classmethod
    def get_full_table_name(cls) -> Composed:
        table_name = cls.get_table_name()
        schema = getattr(cls, "__schema__", None)
        if schema:
            return Composed([Identifier(schema), SQL("."), Identifier(table_name)])
        return Composed([Identifier(table_name)])

    @classmethod
    def get_primary_key(cls) -> str:
        if "__primary_key__" in cls.__dict__:
            return cls.__dict__["__primary_key__"]
        if "id" in cls.model_fields:
            return "id"
        if not getattr(cls, "__abstract__", False):
            raise TypeError(f"{cls.__name__} does not have a primary key.")
        return ""


