import pytest

from database.schemas import AdminDto, GameDto, GameStatus

@pytest.mark.asyncio
async def test_start_round(
    message, user_client,
    messages_client, game_client,
    actions_client, info_client,
    mock_session, mocker,
    user_id, other_user_id, game_id
):
    mocker.patch.object(user_client, 'get_user', return_value=AdminDto(tg_id=user_id, game_id=game_id))
    mocker.patch.object(
        game_client, 'get_all_active_admins',
        return_value=[
            AdminDto(tg_id=user_id, game_id=game_id),
            AdminDto(tg_id=other_user_id, game_id=game_id),
        ]
    )
    mocker.patch.object(
        game_client, 'get_game',
        return_value=GameDto(id=game_id, status=GameStatus.ROUND, round=1, num_planets=3)
    )
    