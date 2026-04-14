# Changelog

## 0.1.12

### Fixed

- **Critical**: `SQLBuilder` methods (`build_select`, `build_update`,
  `build_delete`, `build_count`, `build_paginate`, `build_paginate_from_sql`)
  assembled their final query with `Composed(query_parts)`, which does not
  insert separators between fragments. When a `%s` placeholder was immediately
  followed by a SQL keyword, PostgreSQL's lexer rejected it as a single
  malformed parameter token (e.g. `$1LIMIT`, `$3WHERE`, `$1ORDER`), raising
  `psycopg.errors.SyntaxError`.

  Concrete shapes that were broken on 0.1.9–0.1.11:
  - `select_one` / `select_all` with any `where` filter (rendered as `... = $1LIMIT $2`).
  - `select_all` with `where` + `order_by`.
  - `update` on any model (always broken: `... = $3WHERE ...`).
  - `paginate` with any `where` filter.

  `insert` and `delete` happened to work only because their placeholders sat at
  the tail of the query.

  Assembly is now done with `SQL(" ").join(...)`, which is the structural fix:
  separators are the responsibility of the assembler, not of each individual
  fragment. `build_insert` retains manual assembly because its grammar has
  tokens (parentheses, commas) that should hug their neighbors.

### Deprecated / Yanked

- **0.1.9, 0.1.10, 0.1.11** are affected by the bug above and should be
  considered broken. Downstream users on those versions should upgrade to
  0.1.12.

### Tests

- Added `tests/test_sql_builder.py` with execution-based regression tests
  covering each broken shape (WHERE + LIMIT, WHERE + ORDER BY, UPDATE, paginate
  with WHERE, etc.). Tests run against the live test database, so any
  reintroduction of the bug surfaces as a real parser error.

#### How to run

Start a Postgres instance (e.g. via Docker):

```bash
docker run -d --name pg-test -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:17
```

Run the regression tests:

```bash
TEST_DB_DSN="postgresql://postgres:test@localhost:5433/postgres" uv run --extra dev pytest tests/test_sql_builder.py -v
```

Cleanup:

```bash
docker rm -f pg-test
```
