"""
Tests for the CRUD operations.
"""

import pytest
import pytest_asyncio

from picopg import (
    BaseModel,
    ConnectionManager,
    Partial,
    delete,
    execute_raw,
    insert,
    paginate,
    select_all,
    select_one,
    select_raw,
    update,
)


class User(BaseModel):
    __primary_key__ = "id"
    id: int | None = None
    name: str
    email: str


@pytest_asyncio.fixture(autouse=True)
async def create_test_table():
    """
    Creates the test table before each test and drops it after.
    """
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS "user" (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL
                )
                """
            )
            await cur.execute('TRUNCATE TABLE "user" RESTART IDENTITY')
    yield
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DROP TABLE IF EXISTS "user"')


@pytest.mark.asyncio
async def test_insert():
    user = User(name="Test User", email="test@example.com")
    inserted_user = await insert(user)
    assert inserted_user.id is not None
    assert inserted_user.name == user.name
    assert inserted_user.email == user.email


@pytest.mark.asyncio
async def test_select_one():
    user = User(name="Test User", email="test@example.com")
    inserted_user = await insert(user)
    selected_user = await select_one(User, id=inserted_user.id)
    assert selected_user is not None
    assert selected_user.id == inserted_user.id
    assert selected_user.name == inserted_user.name


@pytest.mark.asyncio
async def test_select_all():
    await insert(User(name="User 1", email="user1@example.com"))
    await insert(User(name="User 2", email="user2@example.com"))
    users = await select_all(User)
    assert len(users) == 2


@pytest.mark.asyncio
async def test_select_with_partial_and_kwargs():
    # Setup: Insert two users, one active, one inactive
    await insert(User(name="Active User", email="active@example.com"))
    await insert(User(name="Inactive User", email="inactive@example.com"))

    # Test 1: Select one using Partial model
    PartialUser = Partial(User)
    filter_model = PartialUser(name="Active User")
    user_by_partial = await select_one(User, where=filter_model)
    assert user_by_partial is not None
    assert user_by_partial.email == "active@example.com"

    # Test 2: Select all using keyword arguments
    all_users = await select_all(User, name="Inactive User")
    assert len(all_users) == 1
    assert all_users[0].email == "inactive@example.com"

    # Test 3: Select one with no match
    no_user = await select_one(User, name="Non Existent")
    assert no_user is None


@pytest.mark.asyncio
async def test_select_with_list_filter():
    # Setup: Insert multiple users
    user1 = await insert(User(name="User 1", email="user1@example.com"))
    await insert(User(name="User 2", email="user2@example.com"))
    user3 = await insert(User(name="User 3", email="user3@example.com"))

    # Test filtering by a list of IDs
    user_ids = [user1.id, user3.id]
    selected_users = await select_all(User, id=user_ids)

    assert len(selected_users) == 2
    selected_ids = {user.id for user in selected_users}
    assert selected_ids == set(user_ids)


@pytest.mark.asyncio
async def test_update():
    user = User(name="Test User", email="test@example.com")
    inserted_user = await insert(user)
    inserted_user.name = "Updated User"
    updated_user = await update(inserted_user)
    assert updated_user.name == "Updated User"


@pytest.mark.asyncio
async def test_delete():
    user = User(name="Test User", email="test@example.com")
    inserted_user = await insert(user)
    result = await delete(inserted_user)
    assert result is True
    selected_user = await select_one(User, id=inserted_user.id)
    assert selected_user is None


@pytest.mark.asyncio
async def test_paginate():
    for i in range(20):
        await insert(User(name=f"User {i}", email=f"user{i}@example.com"))
    # Test default sort (by primary key 'id')
    users, total = await paginate(User, page=2, page_size=5)
    assert len(users) == 5
    assert total == 20
    # Since IDs are 1-20, page 2 should start with ID 6 (User 5)
    assert users[0].name == "User 5"

    # Test explicit sort by name (alphabetical)
    users_sorted, total_sorted = await paginate(
        User, page=1, page_size=5, order_by="name"
    )
    assert len(users_sorted) == 5
    assert total_sorted == 20
    # User 0, User 1, User 10, User 11, User 12 (alphabetical sort)
    assert users_sorted[0].name == "User 0"
    assert users_sorted[4].name == "User 12"


class Profile(BaseModel):
    __table_name__ = "profiles"
    __primary_key__ = "user_id"
    user_id: int | None = None
    username: str
    bio: str | None = None


@pytest_asyncio.fixture
async def create_profile_table():
    """
    Creates the test table for profiles.
    """
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS "profiles" (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    bio TEXT
                )
                """
            )
            await cur.execute('TRUNCATE TABLE "profiles" RESTART IDENTITY')
    yield
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DROP TABLE IF EXISTS "profiles"')


@pytest.mark.asyncio
async def test_insert_with_custom_pk(create_profile_table):
    profile = Profile(username="testuser")
    inserted_profile = await insert(profile)
    assert inserted_profile.user_id is not None
    assert inserted_profile.username == "testuser"


@pytest.mark.asyncio
async def test_insert_with_null_value(create_profile_table):
    profile = Profile(username="testuser", bio=None)
    inserted_profile = await insert(profile)
    assert inserted_profile.user_id is not None
    retrieved_profile = await select_one(Profile, user_id=inserted_profile.user_id)
    assert retrieved_profile is not None
    assert retrieved_profile.bio is None


@pytest.mark.asyncio
async def test_update_with_null_value(create_profile_table):
    profile = Profile(username="testuser", bio="A bio")
    inserted_profile = await insert(profile)
    inserted_profile.bio = None
    updated_profile = await update(inserted_profile)
    assert updated_profile.bio is None


class Product(BaseModel):
    __schema__ = "core"
    __table_name__ = "raw_materials"
    __primary_key__ = "material_id"
    material_id: int | None = None
    name: str
    quantity: int


@pytest_asyncio.fixture
async def create_schema_and_product_table():
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("CREATE SCHEMA IF NOT EXISTS core")
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS core.raw_materials (
                    material_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    quantity INTEGER NOT NULL
                )
                """
            )
            await cur.execute("TRUNCATE TABLE core.raw_materials RESTART IDENTITY")
    yield
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DROP TABLE IF EXISTS core.raw_materials")
            await cur.execute("DROP SCHEMA IF EXISTS core")


@pytest.mark.asyncio
async def test_schema_table_operations(create_schema_and_product_table):
    # Test insert
    product = Product(name="Iron Ore", quantity=1000)
    inserted_product = await insert(product)
    assert inserted_product.material_id is not None
    assert inserted_product.name == "Iron Ore"

    # Test select_one
    selected = await select_one(Product, material_id=inserted_product.material_id)
    assert selected is not None
    assert selected.name == "Iron Ore"

    # Test update
    selected.quantity = 950
    updated = await update(selected)
    assert updated.quantity == 950

    # Test delete
    deleted = await delete(updated)
    assert deleted is True

    # Verify deletion
    final_check = await select_one(Product, material_id=inserted_product.material_id)
    assert final_check is None


@pytest.mark.asyncio
async def test_kwargs_and_where_conflict():
    with pytest.raises(ValueError):
        await select_one(User, where=User(id=1), id=1)


@pytest.mark.asyncio
async def test_invalid_kwarg():
    with pytest.raises(AttributeError):
        await select_one(User, non_existent_field=1)


@pytest.mark.asyncio
async def test_select_all_no_match():
    users = await select_all(User, name="Non Existent User")
    assert users == []


@pytest.mark.asyncio
async def test_paginate_out_of_bounds():
    await insert(User(name="User 1", email="user1@example.com"))
    users, total = await paginate(User, page=2, page_size=1)
    assert users == []
    assert total == 1


@pytest.mark.asyncio
async def test_update_non_existent():
    user = User(id=999, name="Test User", email="test@example.com")
    with pytest.raises(RuntimeError):
        await update(user)


@pytest.mark.asyncio
async def test_delete_non_existent():
    user = User(id=999, name="Test User", email="test@example.com")
    result = await delete(user)
    assert result is False


@pytest.mark.asyncio
async def test_select_raw():
    # Setup: Insert users
    user1 = await insert(User(name="Raw User 1", email="raw1@example.com"))
    await insert(User(name="Raw User 2", email="raw2@example.com"))

    # Test 1: Raw select with model validation
    query = 'SELECT * FROM "user" WHERE name = %s'
    results_as_models = await select_raw(query, ["Raw User 1"], model_class=User)
    assert len(results_as_models) == 1
    assert isinstance(results_as_models[0], User)
    assert results_as_models[0].id == user1.id

    # Test 2: Raw select returning dicts
    query_all = 'SELECT id, name FROM "user" ORDER BY id'
    results_as_dicts = await select_raw(query_all)
    assert len(results_as_dicts) == 2
    assert isinstance(results_as_dicts[0], dict)
    assert "email" not in results_as_dicts[0]
    assert results_as_dicts[0]["name"] == "Raw User 1"


@pytest.mark.asyncio
async def test_execute_raw():
    # Setup: Insert a user
    await insert(User(name="Exec User", email="exec@example.com"))

    # Test 1: Raw update
    update_query = 'UPDATE "user" SET name = %s WHERE email = %s'
    affected_rows = await execute_raw(
        update_query, ["Updated Name", "exec@example.com"]
    )
    assert affected_rows == 1
    updated_user = await select_one(User, email="exec@example.com")
    assert updated_user is not None
    assert updated_user.name == "Updated Name"

    # Test 2: Raw delete
    delete_query = 'DELETE FROM "user" WHERE email = %s'
    affected_rows = await execute_raw(delete_query, ["exec@example.com"])
    assert affected_rows == 1
    deleted_user = await select_one(User, email="exec@example.com")
    assert deleted_user is None


@pytest.mark.asyncio
async def test_abstract_model_inheritance():
    """
    Tests that a model can inherit from an abstract base model
    without causing errors.
    """

    class AbstractBase(BaseModel):
        __abstract__ = True
        # This class has no primary key, which would normally cause an error.

    class ConcreteModel(AbstractBase):
        __table_name__ = "concrete"
        id: int | None = None
        name: str

    # Setup table for the concrete model
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS "concrete" (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL
                )
                """
            )
            await cur.execute('TRUNCATE TABLE "concrete" RESTART IDENTITY')

    # Test that CRUD operations work on the concrete model
    instance = ConcreteModel(name="test")
    inserted = await insert(instance)
    assert inserted.id is not None

    retrieved = await select_one(ConcreteModel, id=inserted.id)
    assert retrieved is not None
    assert retrieved.name == "test"

    # Teardown table
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DROP TABLE "concrete"')


@pytest.mark.asyncio
async def test_abstract_model_inheritance():
    """
    Tests that a model can inherit from an abstract base model
    without causing errors.
    """

    class AbstractBase(BaseModel):
        __abstract__ = True
        # This class has no primary key, which would normally cause an error.

    class ConcreteModel(AbstractBase):
        __table_name__ = "concrete"
        id: int | None = None
        name: str

    # Setup table for the concrete model
    pool = ConnectionManager.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS "concrete" (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL
                )
                """
            )
            await cur.execute('TRUNCATE TABLE "concrete" RESTART IDENTITY')

    # Test that CRUD operations work on the concrete model
    instance = ConcreteModel(name="test")
    inserted = await insert(instance)
    assert inserted.id is not None

    retrieved = await select_one(ConcreteModel, id=inserted.id)
    assert retrieved is not None
    assert retrieved.name == "test"

    # Teardown table
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DROP TABLE "concrete"')
