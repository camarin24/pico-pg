"""Provides asynchronous CRUD operations for the micro-pg ORM.

This module contains the core functions for interacting with the database,
including insert, select, update, delete, and paginate.
"""

from __future__ import annotations

from typing import Any, LiteralString, Type, TypeVar

from psycopg.rows import dict_row
from psycopg.sql import SQL

from .connections import ConnectionManager
from .models import BaseModel
from .sql_builder import SQLBuilder

T = TypeVar("T", bound=BaseModel)


async def insert(model: T) -> T:
    """Inserts a model instance into the database.

    Args:
        model: The model instance to insert.

    Returns:
        The inserted model instance, updated with any database-generated values.

    Raises:
        RuntimeError: If the insert operation fails.
    """
    pool = ConnectionManager.get_pool()
    model_class = type(model)
    query, params = SQLBuilder.build_insert(model)
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, params)
            result = await cur.fetchone()
            if result:
                return model_class.model_validate(result)
    raise RuntimeError("Insert operation failed.")


async def select_one(
    model_class: Type[T], where: T | None = None, **kwargs: Any
) -> T | None:
    """Selects a single record from the database.

    Args:
        model_class: The model class to query.
        where: An optional partial model instance for filtering.
        **kwargs: Keyword arguments for filtering.

    Returns:
        A model instance if a record is found, otherwise `None`.

    Raises:
        ValueError: If both `where` and `kwargs` are provided.
        AttributeError: If a keyword argument is not a valid field.
    """
    if where and kwargs:
        raise ValueError("Cannot use both 'where' and keyword arguments.")

    pool = ConnectionManager.get_pool()
    where_dict = None
    if where:
        where_dict = where.model_dump(exclude_unset=True)
    elif kwargs:
        for key in kwargs:
            if key not in model_class.model_fields:
                raise AttributeError(
                    f"'{key}' is not a valid field for {model_class.__name__}"
                )
        where_dict = kwargs

    query, params = SQLBuilder.build_select(model_class, where_dict, limit=1)
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, params)
            result = await cur.fetchone()
            if result:
                return model_class.model_validate(result)
            return None


async def select_all(
    model_class: Type[T],
    where: T | None = None,
    limit: int | None = None,
    order_by: str | list[str] | None = None,
    **kwargs: Any,
) -> list[T]:
    """Selects multiple records from the database.

    Args:
        model_class: The model class to query.
        where: An optional partial model instance for filtering.
        **kwargs: Keyword arguments for filtering.

    Returns:
        A list of model instances.

    Raises:
        ValueError: If both `where` and `kwargs` are provided.
        AttributeError: If a keyword argument is not a valid field.
    """
    if where and kwargs:
        raise ValueError("Cannot use both 'where' and keyword arguments.")

    pool = ConnectionManager.get_pool()
    where_dict = None
    if where:
        where_dict = where.model_dump(exclude_unset=True)
    elif kwargs:
        for key in kwargs:
            if key not in model_class.model_fields:
                raise AttributeError(
                    f"'{key}' is not a valid field for {model_class.__name__}"
                )
        where_dict = kwargs

    if order_by is None:
        order_by = model_class.get_primary_key()

    query, params = SQLBuilder.build_select(model_class, where_dict, limit, order_by)
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, params)
            results = await cur.fetchall()
            return [model_class.model_validate(row) for row in results]


async def update(model: T) -> T:
    """Updates a model instance in the database.

    Args:
        model: The model instance to update.

    Returns:
        The updated model instance.

    Raises:
        RuntimeError: If the update operation fails.
    """
    pool = ConnectionManager.get_pool()
    model_class = type(model)
    query, params = SQLBuilder.build_update(model)
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, params)
            result = await cur.fetchone()
            if result:
                return model_class.model_validate(result)
    raise RuntimeError("Update operation failed.")


async def delete(model: T) -> bool:
    """Deletes a model instance from the database.

    Args:
        model: The model instance to delete.

    Returns:
        `True` if the deletion was successful, otherwise `False`.
    """
    pool = ConnectionManager.get_pool()
    query, params = SQLBuilder.build_delete(model)
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            return cur.rowcount > 0


async def paginate(
    model_class: Type[T],
    page: int,
    page_size: int,
    where: T | None = None,
    order_by: str | list[str] | None = None,
    **kwargs: Any,
) -> tuple[list[T], int]:
    """Fetches a paginated list of models.

    Args:
        model_class: The model class to query.
        page: The page number to retrieve.
        page_size: The number of records per page.
        where: An optional partial model instance for filtering.
        order_by: An optional field name or list of field names for the ORDER BY clause.
        **kwargs: Keyword arguments for filtering.

    Returns:
        A tuple containing the list of models for the current page and the
        total number of records.

    Raises:
        ValueError: If both `where` and `kwargs` are provided.
        AttributeError: If a keyword argument is not a valid field.
    """
    if where and kwargs:
        raise ValueError("Cannot use both 'where' and keyword arguments.")

    pool = ConnectionManager.get_pool()
    where_dict = None
    if where:
        where_dict = where.model_dump(exclude_unset=True)
    elif kwargs:
        for key in kwargs:
            if key not in model_class.model_fields:
                raise AttributeError(
                    f"'{key}' is not a valid field for {model_class.__name__}"
                )
        where_dict = kwargs

    # Default to sorting by primary key for stable pagination
    if order_by is None:
        order_by = model_class.get_primary_key()

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # Get total count
            count_query, count_params = SQLBuilder.build_count(model_class, where_dict)
            await cur.execute(count_query, count_params)
            count_result = await cur.fetchone()
            total_count = count_result["total"] if count_result else 0

            # Get paginated results
            query, params = SQLBuilder.build_paginate(
                model_class, page, page_size, where_dict, order_by
            )
            await cur.execute(query, params)
            results = await cur.fetchall()
            models = [model_class.model_validate(row) for row in results]
            return models, total_count


async def paginate_raw(
    model_class: Type[T],
    count_query: LiteralString,
    query: LiteralString,
    page: int,
    page_size: int,
    params: list[Any] | None = None,
) -> tuple[list[T], int]:
    """Fetches a paginated list of models from a raw SQL query.

    Args:
        model_class: The model class to query.
        count_query: The raw SQL query to count the total number of records.
        The query should be a valid SQL query that returns a single column named "total" containing the total number of records.
        query: The raw SQL query to fetch the records.
        page: The page number to retrieve.
        page_size: The number of records per page.
        params: An optional list of parameters to pass to the query.

    Returns:
        A tuple containing the list of models for the current page and the
        total number of records.
    """
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(count_query, params)
            count_result = await cur.fetchone()
            total_count = count_result["total"] if count_result else 0

            paginated_query, paginated_params = SQLBuilder.build_paginate_from_sql(
                SQL(query), page, page_size, params
            )
            await cur.execute(paginated_query, paginated_params)
            results = await cur.fetchall()
            models = [model_class.model_validate(row) for row in results]
            return models, total_count


async def select_raw(
    query: LiteralString,
    params: list[Any] | None = None,
    model_class: Type[T] | None = None,
) -> list[T] | list[dict[str, Any]]:
    """Executes a raw SELECT query.

    Args:
        query: The raw SQL query string.
        params: An optional list of parameters to pass to the query.
        model_class: An optional `BaseModel` subclass to validate the results.

    Returns:
        A list of model instances if `model_class` is provided, otherwise a
        list of dictionaries.
    """
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, params)
            results = await cur.fetchall()
            if model_class:
                return [model_class.model_validate(row) for row in results]
            return results


async def execute_raw(query: LiteralString, params: list[Any] | None = None) -> int:
    """Executes a raw query (INSERT, UPDATE, DELETE).

    Args:
        query: The raw SQL query string.
        params: An optional list of parameters to pass to the query.

    Returns:
        The number of affected rows.
    """
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            return cur.rowcount
