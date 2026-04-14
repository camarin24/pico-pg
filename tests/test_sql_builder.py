"""Regression tests for picopg.sql_builder.

These cover the query shapes broken in 0.1.9–0.1.11, where builders assembled
fragments with ``Composed(query_parts)`` — which does not insert separators —
causing keywords to concatenate directly onto ``%s`` placeholders and raise
``psycopg.errors.SyntaxError`` (e.g. ``$1LIMIT``, ``$3WHERE``, ``$1ORDER``).

Each test executes the query against the live test database so a regression
would surface as a real parser error, not just a string mismatch.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from picopg import BaseModel, ConnectionManager, insert
from picopg.sql_builder import SQLBuilder


class SBUser(BaseModel):
    __table_name__ = "sb_user"
    __primary_key__ = "id"
    id: int | None = None
    name: str
    email: str


@pytest_asyncio.fixture(autouse=True)
async def create_sb_user_table():
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS "sb_user" (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL
                )
                """
            )
            await cur.execute('TRUNCATE TABLE "sb_user" RESTART IDENTITY')
    yield
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DROP TABLE IF EXISTS "sb_user"')


async def _execute(query, params):
    """Execute a (query, params) pair on the test pool, returning fetchall."""
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            # Only fetch if the statement produced a resultset
            if cur.description is not None:
                return await cur.fetchall()
            return None


# --- SELECT -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_select_where_only():
    query, params = SQLBuilder.build_select(SBUser, where={"name": "x"})
    await _execute(query, params)


@pytest.mark.asyncio
async def test_build_select_where_plus_limit():
    # Regression: previously rendered "... = $1LIMIT $2" → syntax error.
    query, params = SQLBuilder.build_select(SBUser, where={"name": "x"}, limit=5)
    await _execute(query, params)


@pytest.mark.asyncio
async def test_build_select_where_plus_order_by():
    # Regression: previously rendered "... = $1ORDER BY ..." → syntax error.
    query, params = SQLBuilder.build_select(SBUser, where={"name": "x"}, order_by="id")
    await _execute(query, params)


@pytest.mark.asyncio
async def test_build_select_limit_only():
    query, params = SQLBuilder.build_select(SBUser, limit=5)
    await _execute(query, params)


@pytest.mark.asyncio
async def test_build_select_order_by_only():
    query, params = SQLBuilder.build_select(SBUser, order_by="id")
    await _execute(query, params)


@pytest.mark.asyncio
async def test_build_select_where_plus_limit_plus_order_by():
    query, params = SQLBuilder.build_select(
        SBUser, where={"name": "x"}, order_by="id", limit=5
    )
    await _execute(query, params)


@pytest.mark.asyncio
async def test_build_select_where_list_filter_plus_limit():
    # Covers the ANY(%s) branch followed by LIMIT.
    query, params = SQLBuilder.build_select(SBUser, where={"id": [1, 2, 3]}, limit=5)
    await _execute(query, params)


# --- UPDATE -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_update_executes():
    # Regression: previously rendered "... = $3WHERE ..." → always broken.
    inserted = await insert(SBUser(name="a", email="b"))
    inserted.name = "a2"
    query, params = SQLBuilder.build_update(inserted)
    await _execute(query, params)


# --- DELETE -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_delete_executes():
    # Previously accidentally worked (%s at tail); pin it down.
    inserted = await insert(SBUser(name="a", email="b"))
    query, params = SQLBuilder.build_delete(inserted)
    await _execute(query, params)


# --- INSERT -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_insert_executes():
    # Previously accidentally worked; guard against future regressions from
    # the manual-assembly path in build_insert.
    query, params = SQLBuilder.build_insert(SBUser(name="a", email="b"))
    await _execute(query, params)


# --- COUNT ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_count_where():
    query, params = SQLBuilder.build_count(SBUser, where={"name": "x"})
    await _execute(query, params)


@pytest.mark.asyncio
async def test_build_count_no_where():
    query, params = SQLBuilder.build_count(SBUser)
    await _execute(query, params)


# --- PAGINATE ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_paginate_no_where():
    query, params = SQLBuilder.build_paginate(SBUser, page=1, page_size=10)
    await _execute(query, params)


@pytest.mark.asyncio
async def test_build_paginate_with_where():
    # Regression: previously rendered "... = $1ORDER BY ..." → syntax error.
    query, params = SQLBuilder.build_paginate(
        SBUser, page=1, page_size=10, where={"name": "x"}
    )
    await _execute(query, params)


@pytest.mark.asyncio
async def test_build_paginate_with_where_and_order_by():
    query, params = SQLBuilder.build_paginate(
        SBUser, page=1, page_size=10, where={"name": "x"}, order_by="name"
    )
    await _execute(query, params)
