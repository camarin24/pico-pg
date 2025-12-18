"""Defines the base model for the PicoPG ORM.

This module contains the `BaseModel` class, which serves as the foundation for
all database models in the PicoPG library. It provides automatic table name
inference, primary key detection, and schema support.
"""

from __future__ import annotations

import re
from typing import ClassVar

from psycopg.sql import SQL, Composed, Identifier
from pydantic import BaseModel as PydanticBaseModel


class BaseModel(PydanticBaseModel):
    """Base class for database models.

    Provides dynamic computation of table names and primary keys, and supports
    the creation of abstract base models for shared configurations.

    Class Attributes:
        __table_name__ (str): Optional. The name of the database table. If not
            provided, it's inferred from the class name (e.g., `MyUser` -> `my_user`).
        __primary_key__ (str): Optional. The name of the primary key field.
            Defaults to `id` if a field with that name exists.
        __schema__ (str | None): Optional. The database schema for the table.
        __abstract__ (bool): Optional. If `True`, the model is treated as an
            abstract base class and is not mapped to a database table.
    """

    __tablename__: ClassVar[str]
    __primary_key__: ClassVar[str]
    __schema__: ClassVar[str | None] = None

    @classmethod
    def get_table_name(cls) -> str:
        """Computes the table name for the model.

        Uses the `__table_name__` attribute if defined, otherwise infers it
        from the class name.

        Returns:
            The database table name.
        """
        if "__tablename__" in cls.__dict__:
            return cls.__dict__["__tablename__"]
        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()

    @classmethod
    def get_full_table_name(cls) -> Composed:
        """Computes the fully qualified and quoted table name.

        Includes the schema if `__schema__` is defined.

        Returns:
            A `psycopg.sql.Composed` object representing the full table name.
        """
        table_name = cls.get_table_name()
        schema = getattr(cls, "__schema__", None)
        if schema:
            return Composed([Identifier(schema), SQL("."), Identifier(table_name)])
        return Composed([Identifier(table_name)])

    @classmethod
    def get_primary_key(cls) -> str:
        """Computes the primary key for the model.

        Uses the `__primary_key__` attribute if defined, otherwise defaults to `id`.
        Raises a `TypeError` for non-abstract models that lack a primary key.

        Returns:
            The primary key field name.
        """
        if "__primary_key__" in cls.__dict__:
            return cls.__dict__["__primary_key__"]
        if "id" in cls.model_fields:
            return "id"
        if not getattr(cls, "__abstract__", False):
            raise TypeError(f"{cls.__name__} does not have a primary key.")
        raise TypeError("No primary key defined.")
