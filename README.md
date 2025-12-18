# PicoPG: A Lightweight Pydantic-Powered Micro ORM for PostgreSQL

PicoPG is a minimal, asynchronous micro-ORM designed for PostgreSQL. It leverages the power of [Pydantic](https://pydantic-docs.helpmanual.io/) for schema definition and data validation, and uses the modern `psycopg` library for efficient, non-blocking database interaction.

It is designed for developers who prefer explicit SQL generation and a simple, function-based API over complex, stateful ORM patterns.

## Features

- **Pydantic Integration:** Define database schemas using Pydantic `BaseModel` for automatic data validation and type hinting.
- **Asynchronous:** Built on `psycopg` for high-performance, non-blocking I/O.
- **Simple CRUD API:** Direct, function-based access for `insert`, `select_one`, `select_all`, `update`, `delete`, and `paginate`.
- **Query by Example:** Use partial models for flexible filtering in select and paginate operations.
- **Stateless SQL Builder:** Explicit and safe SQL generation using parameterized queries.
- **Connection Pooling:** Centralized management of the `psycopg_pool.AsyncConnectionPool`.

## Installation

PicoPG requires Python 3.10+ and is built on `psycopg` and `pydantic`.

```bash
pip install picopg
```

## 1. Defining Models

Database tables are represented by classes inheriting from `picopg.BaseModel`.

- **Table Name Inference:** Class names are automatically converted to snake_case table names (e.g., `MyUser` -> `"my_user"`).
- **Primary Key:** Defaults to a field named `id`. You can override this with the `__primary_key__` class variable.
- **Schema Support:** Use the `__schema__` class variable to specify a PostgreSQL schema.

```python
from picopg import BaseModel
from datetime import datetime

class User(BaseModel):
    # Optional: Override inferred table name
    __tablename__ = '"users_table"'
    # Optional: Specify a schema
    __schema__ = "app_data"
    # Optional: Override primary key (defaults to 'id')
    __primary_key__ = "user_id"

    user_id: int | None = None # Primary key field
    username: str
    email: str
    is_active: bool = True
    created_at: datetime = datetime.now()
```

## 2. Connection Management

PicoPG uses a static `ConnectionManager` to handle the asynchronous connection pool. This must be initialized once at application startup.

```python
from picopg import ConnectionManager

# 1. Initialize the pool (e.g., at application startup)
async def startup():
    DSN = "postgresql://user:password@host:port/dbname"
    await ConnectionManager.initialize(
        dsn=DSN,
        min_size=5,
        max_size=10,
        # ... other psycopg_pool arguments
    )

# 2. Close the pool (e.g., at application shutdown)
async def shutdown():
    await ConnectionManager.close()
```

## 3. CRUD Operations

PicoPG provides simple, asynchronous functions for all standard database operations.

### Insert

The `insert` function takes a model instance and returns the model updated with any database-generated values (e.g., auto-incremented IDs, default timestamps).

```python
from picopg import insert
# ... User model defined above

new_user = User(username="alice", email="alice@example.com")
inserted_user = await insert(new_user)

print(inserted_user.user_id) # e.g., 1
print(inserted_user.created_at) # e.g., 2023-10-27 10:00:00
```

### Select One

The `select_one` function retrieves a single record. Filtering can be done using keyword arguments or a `Partial` model instance.

```python
from picopg import select_one, Partial

# 1. Select by keyword argument
user_by_id = await select_one(User, user_id=1)
user_by_email = await select_one(User, email="alice@example.com")

# 2. Select using a Partial model (Query by Example)
UserPartial = Partial(User)
filter_model = UserPartial(username="alice", is_active=True)
user_by_partial = await select_one(User, where=filter_model)

if user_by_id:
    print(f"Found user: {user_by_id.username}")
```

### Select All

The `select_all` function retrieves a list of records, supporting the same filtering methods as `select_one`.

```python
from picopg import select_all

# Select all active users
active_users = await select_all(User, is_active=True)

# Select all users with a specific username prefix (using Partial for filtering)
# Note: PicoPG's built-in filtering is for equality (=) only.
# For complex queries (LIKE, >, etc.), you must use raw SQL via select_raw
```

### Update

The `update` function requires a model instance that includes the primary key value. It updates the record and returns the updated model from the database.

```python
from picopg import update

# Assume 'user_to_update' is a model instance retrieved from the database
user_to_update.email = "alice.new@example.com"
updated_user = await update(user_to_update)

print(updated_user.email) # alice.new@example.com
```

### Delete

The `delete` function takes a model instance (only the primary key is required) and removes the corresponding record.

```python
from picopg import delete

# Delete the user
success = await delete(updated_user)
print(f"Deletion successful: {success}") # True or False
```

### Paginate

The `paginate` function is used for fetching a subset of records along with the total count, which is essential for building UIs.

```python
from picopg import paginate

# Fetch the second page of 10 records, filtered by active status
page_number = 2
page_size = 10
users_page, total_count = await paginate(
    model_class=User,
    page=page_number,
    page_size=page_size,
    is_active=True
)

print(f"Total active users: {total_count}")
print(f"Users on page {page_number}: {len(users_page)}")
```

## 4. Advanced Components

### `Partial` Models

The `Partial` utility function dynamically creates a Pydantic model where every field is optional. This is the recommended way to pass filter criteria to `select_one`, `select_all`, and `paginate` when you want to use a model-like structure for filtering.

```python
from picopg import Partial

class Post(BaseModel):
    id: int | None = None
    title: str
    content: str
    author_id: int

# Create a partial model type
PartialPost = Partial(Post)

# Use it to define a filter
filter_by_author = PartialPost(author_id=5)

# This filter can now be passed to select functions
# posts = await select_all(Post, where=filter_by_author)
```

### `SQLBuilder`

The `SQLBuilder` class is exposed for advanced use cases where you need to inspect or modify the generated SQL. It is a stateless utility for generating parameterized queries.

```python
from picopg import SQLBuilder

# Example: Build an INSERT query manually
new_post = Post(title="Hello", content="World", author_id=1)
query, params = SQLBuilder.build_insert(new_post)

print(query)
# INSERT INTO "post" (title, content, author_id) VALUES (%s, %s, %s) RETURNING *

print(params)
# ['Hello', 'World', 1]
```
