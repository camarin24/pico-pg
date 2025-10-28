"""Defines the base model for the PicoPG ORM.

This module contains the `BaseModel` class, which serves as the foundation for
all database models in the PicoPG library. It provides automatic table name
inference, primary key detection, and schema support.
"""
from __future__ import annotations

import re
from typing import Any, ClassVar

from pydantic import BaseModel as PydanticBaseModel
from psycopg.sql import SQL, Identifier, Composed


class BaseModel(PydanticBaseModel):
    """Base class for database models.

    This class provides the core functionality for defining table models,
    including automatic table name inference and primary key detection.

    Attributes:
        __table_name__: The unquoted base name of the database table.
        __full_table_name__: The fully qualified, quoted name of the database table as a Composed object.
        __primary_key__: The name of the primary key field.
        __schema__: An optional database schema for the table.
    """

    __table_name__: ClassVar[str]
    __full_table_name__: ClassVar[Composed]
    __primary_key__: ClassVar[str]
    __schema__: ClassVar[str | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Initializes the subclass, inferring table name and primary key.
        """
        super().__init_subclass__(**kwargs)

        # Determine the base table name
        if hasattr(cls, "__table_name__"):
            base_table_name = cls.__table_name__
        else:
            base_table_name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        
        cls.__table_name__ = base_table_name

        # Construct full, quoted table name with schema if provided
        schema = getattr(cls, "__schema__", None)
        if schema:
            cls.__full_table_name__ = Composed([Identifier(schema), SQL("."), Identifier(base_table_name)])
        else:
            cls.__full_table_name__ = Composed([Identifier(base_table_name)])

        # Configure primary key
        if not hasattr(cls, "__primary_key__"):
            if "id" in cls.model_fields:
                cls.__primary_key__ = "id"
            else:
                raise TypeError(f"{cls.__name__} does not have a primary key.")
