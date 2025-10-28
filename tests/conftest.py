"""
This module contains shared fixtures for pytest.
"""

import asyncio
import os

import pytest
import pytest_asyncio
from picopg import ConnectionManager

# Use a separate database for testing
TEST_DB_DSN = os.environ.get("TEST_DB_DSN")
if not TEST_DB_DSN:
    raise RuntimeError("TEST_DB_DSN environment variable is not set.")


@pytest.fixture(scope="session")
def event_loop():
    """
    Creates an asyncio event loop for the test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """
    Initializes the database connection pool before tests run.
    """
    await ConnectionManager.initialize(TEST_DB_DSN)
    yield
    await ConnectionManager.close()
