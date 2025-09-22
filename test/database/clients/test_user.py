import pytest
from pytest_lazy_fixtures import lf

from database.models import Admin, Game, Planet, Player
from database.schemas import FailureReason, GameStatus


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
async def test_make_new_user_if_not_exists(tg_id, is_admin, mock_user_client):
    await mock_user_client.make_new_user_if_not_exists(tg_id, is_admin)

    async with mock_user_client.session() as s:
        if is_admin:
            admin = await s.get(Admin, tg_id)
            assert admin
        else:
            player = await s.get(Player, tg_id)
            assert player


@pytest.mark.parametrize("is_admin", (True, False))
@pytest.mark.asyncio
async def test_make_new_user(is_admin, non_existing_user_id, mock_user_client):
    await mock_user_client.make_new_user(non_existing_user_id, is_admin)

    async with mock_user_client.session() as s:
        if is_admin:
            admin = await s.get(Admin, non_existing_user_id)
            assert admin
        else:
            player = await s.get(Player, non_existing_user_id)
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
async def test_get_user(mock_user_client, tg_id, result):
    res = await mock_user_client.get_user(tg_id)

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
    user_id, user_game_id, game_status, result, game_id, mock_user_client
):
    async with mock_user_client.session() as s:
        user = await s.get(Player, user_id)
        if user:
            user.game_id = user_game_id
        user = await s.get(Admin, user_id)
        if user:
            user.game_id = user_game_id

        game = await s.get(Game, game_id)
        game.status = game_status
        await s.commit()

    res = await mock_user_client.join_user(user_id, game_id)
    assert res == result

    if res != FailureReason.GAME_ENDED:
        async with mock_user_client.session() as s:
            user = await s.get(Player, user_id)
            if user:
                assert user.game_id == game_id
            user = await s.get(Admin, user_id)
            if user:
                assert user.game_id == game_id


@pytest.fixture()
def new_player_id():
    return 6


@pytest.mark.asyncio
async def test_join_player_when_lobby_is_full(
    mock_user_client, new_player_id, game_id, player_ids, planet_ids
):
    async with mock_user_client.session() as s:
        for player_id, planet_id in zip(player_ids, planet_ids):
            planet = await s.get(Planet, planet_id)
            planet.owner_id = player_id
            await s.commit()

        new_player = Player(tg_id=new_player_id)
        s.add(new_player)
        await s.commit()

    res = await mock_user_client.join_user(new_player_id, game_id)
    assert res == FailureReason.GAME_IS_FULL


@pytest.mark.asyncio
async def test_kick_user(mock_user_client, player_id, game_id, admin_id):
    async with mock_user_client.session() as s:
        player = await s.get(Player, player_id)
        admin = await s.get(Admin, admin_id)

        player.game_id = game_id
        admin.game_id = game_id
        await s.commit()

    res = await mock_user_client.kick_user(player_id)
    assert res == FailureReason.SUCCESS

    res = await mock_user_client.kick_user(admin_id)
    assert res == FailureReason.SUCCESS

    async with mock_user_client.session() as s:
        player = await s.get(Player, player_id)
        admin = await s.get(Admin, admin_id)

        assert player.game_id is None
        assert admin.game_id is None


@pytest.mark.asyncio
async def test_kick_user_when_not_in_lobby(mock_user_client, player_id, admin_id):
    res = await mock_user_client.kick_user(player_id)
    assert res == FailureReason.NOT_IN_GAME

    res = await mock_user_client.kick_user(admin_id)
    assert res == FailureReason.NOT_IN_GAME
