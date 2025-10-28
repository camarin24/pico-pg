"""
Tests for the CRUD operations.
"""

import pytest

from picopg import (
    BaseModel,
    ConnectionManager,
    delete,
    insert,
    paginate,
    select_all,
    select_one,
    update,
)


class User(BaseModel):
    __primary_key__ = "id"
    id: int | None = None
    name: str
    email: str




import pytest_asyncio


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
    users, total = await paginate(User, page=2, page_size=5)
    assert len(users) == 5
    assert total == 20
    assert users[0].name == "User 5"


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
    retrieved_profile = await select_one(
        Profile, user_id=inserted_profile.user_id
    )
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
    selected = await select_one(
        Product, material_id=inserted_product.material_id
    )
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
    final_check = await select_one(
        Product, material_id=inserted_product.material_id
    )
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

