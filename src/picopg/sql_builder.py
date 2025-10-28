"""Provides a stateless SQL query builder for the micro-pg ORM.

This module contains the `SQLBuilder` class, which uses static methods to
construct raw SQL queries for `BaseModel` instances.
"""

from __future__ import annotations

from typing import Any, Type
from psycopg.sql import SQL, Composed, Identifier

from .models import BaseModel


class SQLBuilder:
    """Builds raw SQL queries for `BaseModel` instances.

    This class uses static methods to remain stateless and ensure that query
    generation is idempotent and free from side effects.
    """

    @staticmethod
    def build_insert(model: BaseModel) -> tuple[Composed, list[Any]]:
        """Builds an INSERT query from a model instance.

        Args:
            model: The model instance to insert.

        Returns:
            A tuple containing the SQL query and a list of parameters.
        """
        model_class = type(model)
        data = model.model_dump()
        if data.get(model_class.__primary_key__) is None:
            data.pop(model_class.__primary_key__, None)

        columns = [Identifier(col) for col in data.keys()]
        placeholders = [SQL("%s")] * len(data)
        
        query = Composed([
            SQL("INSERT INTO"),
            model_class.__full_table_name__,
            SQL("("),
            Composed(columns).join(SQL(", ")),
            SQL(") VALUES ("),
            Composed(placeholders).join(SQL(", ")),
            SQL(") RETURNING *")
        ])
        return query, list(data.values())

    @staticmethod
    def build_select(
        model_class: Type[BaseModel],
        where: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> tuple[Composed, list[Any]]:
        """Builds a SELECT query.

        Args:
            model_class: The model class to query.
            where: An optional dictionary of conditions for the WHERE clause.
            limit: An optional limit for the number of records to return.

        Returns:
            A tuple containing the SQL query and a list of parameters.
        """
        query_parts = [SQL("SELECT * FROM"), model_class.__full_table_name__]
        params = []
        if where:
            conditions = Composed([
                Composed([Identifier(key), SQL("= %s")])
                for key in where.keys()
            ]).join(SQL(" AND "))
            query_parts.extend([SQL("WHERE"), conditions])
            params.extend(where.values())
        if limit:
            query_parts.extend([SQL("LIMIT %s")])
            params.append(limit)
        
        query = Composed(query_parts)
        return query, params

    @staticmethod
    def build_update(model: BaseModel) -> tuple[Composed, list[Any]]:
        """Builds an UPDATE query from a model instance.

        Args:
            model: The model instance to update.

        Returns:
            A tuple containing the SQL query and a list of parameters.
        """
        model_class = type(model)
        data = model.model_dump()
        pk_value = data.pop(model_class.__primary_key__)
        
        set_parts = Composed([
            Composed([Identifier(key), SQL("= %s")])
            for key in data.keys()
        ]).join(SQL(", "))
        
        query = Composed([
            SQL("UPDATE"),
            model_class.__full_table_name__,
            SQL("SET"),
            set_parts,
            SQL("WHERE"),
            Identifier(model_class.__primary_key__),
            SQL("= %s RETURNING *")
        ])
        params = list(data.values()) + [pk_value]
        return query, params

    @staticmethod
    def build_delete(model: BaseModel) -> tuple[Composed, list[Any]]:
        """Builds a DELETE query.

        Args:
            model: The model instance to delete.

        Returns:
            A tuple containing the SQL query and a list of parameters.
        """
        model_class = type(model)
        pk_value = getattr(model, model_class.__primary_key__)
        
        query = Composed([
            SQL("DELETE FROM"),
            model_class.__full_table_name__,
            SQL("WHERE"),
            Identifier(model_class.__primary_key__),
            SQL("= %s")
        ])
        return query, [pk_value]

    @staticmethod
    def build_count(
        model_class: Type[BaseModel], where: dict[str, Any] | None = None
    ) -> tuple[Composed, list[Any]]:
        """Builds a COUNT query.

        Args:
            model_class: The model class to query.
            where: An optional dictionary of conditions for the WHERE clause.

        Returns:
            A tuple containing the SQL query and a list of parameters.
        """
        query_parts = [SQL("SELECT COUNT(*) as total FROM"), model_class.__full_table_name__]
        params = []
        if where:
            conditions = Composed([
                Composed([Identifier(key), SQL("= %s")])
                for key in where.keys()
            ]).join(SQL(" AND "))
            query_parts.extend([SQL("WHERE"), conditions])
            params.extend(where.values())
        
        query = Composed(query_parts)
        return query, params

    @staticmethod
    def build_paginate(
        model_class: Type[BaseModel],
        page: int,
        page_size: int,
        where: dict[str, Any] | None = None,
    ) -> tuple[Composed, list[Any]]:
        """Builds a paginated SELECT query.

        Args:
            model_class: The model class to query.
            page: The page number to retrieve.
            page_size: The number of records per page.
            where: An optional dictionary of conditions for the WHERE clause.

        Returns:
            A tuple containing the SQL query and a list of parameters.
        """
        query, params = SQLBuilder.build_select(model_class, where)
        offset = (page - 1) * page_size
        
        query = Composed([
            query,
            SQL("LIMIT %s OFFSET %s")
        ])
        params.extend([page_size, offset])
        return query, params
