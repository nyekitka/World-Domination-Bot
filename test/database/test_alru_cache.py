from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from database.schemas import GameDto


@pytest.mark.asyncio
async def test_get_game_cached(database_client, game_id):
    mock_session1 = AsyncMock(spec=AsyncSession)
    mock_session2 = AsyncMock(spec=AsyncSession)

    mock_session1.get.return_value = GameDto(id=game_id, num_planets=2)
    mock_session2.get.return_value = GameDto(id=game_id, num_planets=2)

    await database_client.get_game(mock_session1, game_id)
    await database_client.get_game(mock_session2, game_id)

    mock_session1.get.assert_awaited_once()
    mock_session2.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_cache_invalidate(database_client, game_id):
    mock_session1 = AsyncMock(spec=AsyncSession)
    mock_session2 = AsyncMock(spec=AsyncSession)

    mock_session1.get.return_value = GameDto(id=game_id, num_planets=2)
    mock_session2.get.return_value = GameDto(id=game_id, num_planets=2)

    await database_client.get_game(mock_session1, game_id)
    database_client.get_game.cache_invalidate(game_id)
    await database_client.get_game(mock_session2, game_id)

    mock_session1.get.assert_awaited_once()
    mock_session2.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_clear(database_client):
    mock_session = AsyncMock(spec=AsyncSession)

    mock_session.get.return_value = GameDto(
        id=1,
        num_planets=5
    )

    await database_client.get_game(mock_session, 1)
    await database_client.get_game(mock_session, 2)
    database_client.get_game.cache_clear()
    await database_client.get_game(mock_session, 1)
    await database_client.get_game(mock_session, 2)

    assert mock_session.get.call_count == 4
