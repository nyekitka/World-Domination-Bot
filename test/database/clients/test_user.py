import pytest
from pytest_lazy_fixtures import lf

from database.models import Admin, Game, Planet, Player
from database.schemas import GameStatus
from game.schemas import FailureReason


@pytest.mark.parametrize(
    ["tg_id", "is_admin"],
    [
        (lf("admin_id"), True),
        (lf("non_existing_user_id"), True),
        (lf("player_id"), False),
        (lf("non_existing_user_id"), False),
    ],
)
@pytest.mark.asyncio
async def test_make_new_user_if_not_exists(session, tg_id, is_admin, user_client):
    await user_client.make_new_user_if_not_exists(session, tg_id, is_admin)

    if is_admin:
        admin = await session.get(Admin, tg_id)
        assert admin
    else:
        player = await session.get(Player, tg_id)
        assert player


@pytest.mark.parametrize("is_admin", (True, False))
@pytest.mark.asyncio
async def test_make_new_user(session, is_admin, non_existing_user_id, user_client):
    await user_client.make_new_user(session, non_existing_user_id, is_admin)

    if is_admin:
        admin = await session.get(Admin, non_existing_user_id)
        assert admin
    else:
        player = await session.get(Player, non_existing_user_id)
        assert player


@pytest.mark.parametrize(
    ["tg_id", "result"],
    [
        (lf("admin_id"), lf("admin_id")),
        (lf("player_id"), lf("player_id")),
        (lf("non_existing_user_id"), None),
    ],
)
@pytest.mark.asyncio
async def test_get_user(user_client, session, tg_id, result):
    res = await user_client.get_user(session, tg_id)

    if res:
        assert res.tg_id == result
    else:
        assert res == result


@pytest.mark.parametrize(
    ["user_id", "user_game_id", "game_status", "result"],
    [
        (lf("admin_id"), None, GameStatus.WAITING, FailureReason.SUCCESS),
        (lf("admin_id"), None, GameStatus.ENDED, FailureReason.SUCCESS),
        (lf("player_id"), None, GameStatus.WAITING, FailureReason.SUCCESS),
        (lf("player_id"), None, GameStatus.ENDED, FailureReason.GAME_ENDED),
        (
            lf("player_id"),
            lf("game_id"),
            GameStatus.ROUND,
            FailureReason.ALREADY_IN_GAME,
        ),
        (
            lf("admin_id"),
            lf("game_id"),
            GameStatus.ROUND,
            FailureReason.ALREADY_IN_GAME,
        ),
    ],
)
@pytest.mark.asyncio
async def test_join_user(
    session, user_id, user_game_id,
    game_status, result, game_id, user_client
):
    user = await session.get(Player, user_id)
    if user:
        user.game_id = user_game_id
    user = await session.get(Admin, user_id)
    if user:
        user.game_id = user_game_id

    game = await session.get(Game, game_id)
    game.status = game_status
    await session.commit()

    res = await user_client.join_user(session, user_id, game_id)
    assert res == result

    if res != FailureReason.GAME_ENDED:
        user = await session.get(Player, user_id)
        if user:
            assert user.game_id == game_id
        user = await session.get(Admin, user_id)
        if user:
            assert user.game_id == game_id


@pytest.fixture()
def new_player_id():
    return 6


@pytest.mark.asyncio
async def test_join_player_when_lobby_is_full(
    user_client, session, new_player_id,
    game_id, player_ids, planet_ids
):
    for player_id, planet_id in zip(player_ids, planet_ids):
        planet = await session.get(Planet, planet_id)
        planet.owner_id = player_id
        await session.commit()

    new_player = Player(tg_id=new_player_id)
    session.add(new_player)
    await session.commit()

    res = await user_client.join_user(session, new_player_id, game_id)
    assert res == FailureReason.GAME_IS_FULL


@pytest.mark.asyncio
async def test_kick_user(user_client, session, player_id, game_id, admin_id):
    player = await session.get(Player, player_id)
    admin = await session.get(Admin, admin_id)

    player.game_id = game_id
    admin.game_id = game_id
    await session.commit()

    res = await user_client.kick_user(session, player_id)
    assert res == FailureReason.SUCCESS

    res = await user_client.kick_user(session, admin_id)
    assert res == FailureReason.SUCCESS

    player = await session.get(Player, player_id)
    admin = await session.get(Admin, admin_id)

    assert player.game_id is None
    assert admin.game_id is None


@pytest.mark.asyncio
async def test_kick_user_when_not_in_lobby(
    user_client, session, player_id, admin_id
):
    res = await user_client.kick_user(session, player_id)
    assert res == FailureReason.NOT_IN_GAME

    res = await user_client.kick_user(session, admin_id)
    assert res == FailureReason.NOT_IN_GAME


@pytest.mark.asyncio
async def test_promote_to_admin_not_in_game(
    user_client, session, player_id
):
    res = await user_client.promote_to_admin(session, player_id)
    assert res == FailureReason.SUCCESS

    admin = await session.get(Admin, player_id)
    assert admin.tg_id == player_id


@pytest.mark.parametrize(
    ('game_status', 'expected_result'),
    [
        (GameStatus.WAITING, FailureReason.SUCCESS),
        (GameStatus.ROUND, FailureReason.WAIT_TILL_GAME_ENDS),
        (GameStatus.MEETING, FailureReason.WAIT_TILL_GAME_ENDS),
    ]
)
@pytest.mark.asyncio
async def test_promote_to_admin_in_game(
    user_client, session, player_id, game_status,
    expected_result, game_id
):
    game = await session.get(Game, game_id)
    game.status = game_status
    player = await session.get(Player, player_id)
    player.game_id = game_id
    await session.commit()
    
    result = await user_client.promote_to_admin(session, player_id)
    assert result == expected_result
    await session.commit()

    player = await session.get(Player, player_id)
    admin = await session.get(Admin, player_id)
    if expected_result == FailureReason.SUCCESS:
        assert admin.tg_id == player_id and player is None
    else:
        assert player.tg_id == player_id and admin is None


@pytest.mark.asyncio
async def test_fire_admin(user_client, session, admin_id):
    res = await user_client.fire_admin(session, admin_id)
    assert res == FailureReason.SUCCESS
    await session.commit()

    admin = await session.get(Admin, admin_id)
    assert admin is None
    player = await session.get(Player, admin_id)
    assert player.tg_id == admin_id


@pytest.mark.asyncio
async def test_is_user_admin(user_client, session, admin_id, player_id):
    res = await user_client.is_user_admin(session, admin_id)
    assert res is True

    res = await user_client.is_user_admin(session, player_id)
    assert res is False
