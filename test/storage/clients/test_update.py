import asyncio
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeRedis

from storage.clients.update import UpdateClient


@pytest.fixture()
def mock_update_client():
    return UpdateClient(FakeRedis())


@pytest.mark.asyncio
async def test_update_client(mock_update_client):
    mock_handler = AsyncMock()

    async def outer_handler(lag: float):
        async with mock_update_client(1, 'money', mock_handler()):
            await asyncio.sleep(lag)

    await asyncio.gather(
        outer_handler(1),
        outer_handler(0.1),
    )

    mock_handler.assert_awaited_once()
