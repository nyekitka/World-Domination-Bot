import asyncio

import pytest
from pytest_lazy_fixtures import lf
from sqlalchemy import select

from database.models import (
    Admin, City, Game,
    Negotiation, Order, Planet,
    Player, Sanction
)
from database.schemas import GameStatus, OrderDto, SanctionDto
from game.config import game_config
from game.schemas import FailureReason, OrderType
from game.schemas import OrderInfo


@pytest.mark.asyncio
async def test_get_games(mock_game_client, game_id):
    games = await mock_game_client.get_all_games()
    assert len(games) == 1
    assert games[0].id == game_id


@pytest.mark.parametrize(
    'num_planets',
    (-1, 2, 6)
)
@pytest.mark.asyncio
async def test_create_game(
    mock_game_client, admin_id, pack, num_planets
):
    game = await mock_game_client.create_game(admin_id, pack, num_planets)
    if num_planets == -1:
        num_planets = len(pack.planets)
    async with mock_game_client.session() as s:
        admin = await s.get(Admin, admin_id)
        assert admin.game_id == game.id
        for i, planet in enumerate(pack.planets):
            result = await s.execute(
                select(Planet).where(
                    Planet.name == planet.name, Planet.game_id == game.id
                )
            )
            orm_planet = result.scalar_one_or_none()
            if i >= num_planets:
                assert orm_planet is None
                continue
            assert orm_planet

            for city in planet.cities:
                result = await s.execute(
                    select(City).where(
                        City.name == city.name, City.planet_id == orm_planet.id
                    )
                )
                orm_city = result.scalar_one_or_none()
                assert orm_city


@pytest.mark.asyncio
async def test_end_game(mock_game_client, game_id, player_ids, admin_id):
    async with mock_game_client.session() as s:
        admin = await s.get(Admin, admin_id)
        admin.game_id = game_id
        for player_id in player_ids:
            player = await s.get(Player, player_id)
            player.game_id = game_id
        await s.commit()

    await mock_game_client.end_game(game_id)

    async with mock_game_client.session() as s:
        admin = await s.get(Admin, admin_id)
        assert admin.game_id is None
        for player_id in player_ids:
            player = await s.get(Player, player_id)
            assert player.game_id is None

        game = await s.get(Game, game_id)
        assert game.status == GameStatus.ENDED


@pytest.mark.asyncio
async def test_get_all_active_players(
    mock_game_client, player_ids, game_id
):
    async with mock_game_client.session() as s:
        for player_id in player_ids:
            player_model = await s.get(Player, player_id)
            player_model.game_id = game_id
            await s.commit()
        
    result = await mock_game_client.get_all_active_players(game_id)
    ids = {player.tg_id for player in result}
    assert ids == set(player_ids)


@pytest.mark.asyncio
async def test_get_all_active_admins(
    mock_game_client, admin_id, player_ids, game_id
):
    async with mock_game_client.session() as s:
        for player_id in player_ids:
            player_model = await s.get(Player, player_id)
            player_model.game_id = game_id
            await s.commit()
        admin = await s.get(Admin, admin_id)
        admin.game_id = game_id
        await s.commit()
        
    result = await mock_game_client.get_all_active_admins(game_id)
    assert len(result) == 1
    assert result[0].tg_id == admin_id


@pytest.mark.asyncio
async def test_get_all_planets_in_game(
    mock_game_client, game_id, pack
):
    planets = await mock_game_client.get_all_planets_in_game(game_id)
    
    actual_planet_names = {planet.name for planet in planets}
    true_planet_names = {planet.name for planet in pack.planets}
    assert actual_planet_names == true_planet_names

@pytest.mark.asyncio
async def test_build_shield_for_cities(mock_game_client, city_id, city_id_2):
    await mock_game_client.build_shield_for_cities(city_id, city_id_2)
    async with mock_game_client.session() as s:
        city1 = await s.get(City, city_id)
        city2 = await s.get(City, city_id_2)

        assert city1.is_shielded
        assert city2.is_shielded


@pytest.mark.asyncio
async def test_develop_cities(mock_game_client, city_id, city_id_2):
    async with mock_game_client.session() as s:
        city1 = await s.get(City, city_id)
        city2 = await s.get(City, city_id_2)
        development1 = city1.development
        development2 = city2.development

    await mock_game_client.develop_cities(city_id, city_id_2)
    async with mock_game_client.session() as s:
        city1 = await s.get(City, city_id)
        city2 = await s.get(City, city_id_2)

        assert city1.development - development1 == game_config.DEVELOPMENT_BOOST
        assert city2.development - development2 == game_config.DEVELOPMENT_BOOST


@pytest.mark.asyncio
async def test_invent_for_planets(mock_game_client, planet_id, planet_id_2):
    await mock_game_client.invent_for_planets(planet_id, planet_id_2)

    async with mock_game_client.session() as s:
        planet = await s.get(Planet, planet_id)
        planet_2 = await s.get(Planet, planet_id_2)

        assert planet.is_invented
        assert planet_2.is_invented


@pytest.mark.parametrize(
    ["num_to_create", "meteorites", "result"], [(1, 2, 3), (2, 2, 4)]
)
@pytest.mark.asyncio
async def test_create_meteorites(
    mock_game_client, planet_id, num_to_create, meteorites, result
):
    async with mock_game_client.session() as s:
        planet = await s.get(Planet, planet_id)
        planet.meteorites = meteorites
        await s.commit()

    await mock_game_client.create_meteorites(planet_id, num_to_create)

    async with mock_game_client.session() as s:
        planet = await s.get(Planet, planet_id)
        assert planet.meteorites == result


@pytest.mark.asyncio
async def test_attack_cities(
    mock_game_client, city_id, city_id_2, city_id_3, game_id
):
    async with mock_game_client.session() as s:
        city1 = await s.get(City, city_id)
        city2 = await s.get(City, city_id_2)
        game = await s.get(Game, game_id)
        game.round = 1
        city1.is_shielded = True
        city2.is_shielded = True
        await s.commit()

    await mock_game_client.attack_cities(city_id, city_id, city_id_2, city_id_3)

    async with mock_game_client.session() as s:
        city1 = await s.get(City, city_id)
        city2 = await s.get(City, city_id_2)
        city3 = await s.get(City, city_id_3)

        assert city1.development == 0
        assert city2.development != 0
        assert not city2.is_shielded
        assert city3.development == 0


@pytest.mark.parametrize(
    ["times", "result"],
    [
        (1, game_config.DEFAULT_GAME_ECO_RATE + game_config.ECO_BOOST_RATE),
        (2, game_config.DEFAULT_GAME_ECO_RATE + 2 * game_config.ECO_BOOST_RATE),
    ],
)
@pytest.mark.asyncio
async def test_eco_boost(mock_game_client, game_id, times, result):
    await mock_game_client.eco_boost(game_id, times)

    async with mock_game_client.session() as s:
        game = await s.get(Game, game_id)
        assert game.ecorate == result


@pytest.mark.asyncio
async def test_send_sanctions(mock_game_client, planet_id, planet_id_2):
    sanctions = [
        SanctionDto(planet_from=planet_id, planet_to=planet_id_2, num_round=1),
        SanctionDto(planet_from=planet_id_2, planet_to=planet_id, num_round=1),
    ]

    await mock_game_client.send_sanctions(sanctions)

    async with mock_game_client.session() as s:
        for sanction in sanctions:
            db_sanc = await s.get(
                Sanction,
                sanction.model_dump()
            )
            assert db_sanc


@pytest.mark.parametrize(
    ["balance", "amount", "result"],
    [
        (100, -100, FailureReason.NEGATIVE_AMOUNT),
        (100, 200, FailureReason.NOT_ENOUGH_MONEY),
        (200, 100, FailureReason.SUCCESS),
    ],
)
@pytest.mark.asyncio
async def test_transfer(
    mock_game_client, planet_id, planet_id_2, balance, amount, result
):
    async with mock_game_client.session() as s:
        planet = await s.get(Planet, planet_id)
        planet.balance = balance
        await s.commit()

    res = await mock_game_client.transfer(planet_id, planet_id_2, amount)
    assert res == result

    if result == FailureReason.SUCCESS:
        async with mock_game_client.session() as s:
            planet1 = await s.get(Planet, planet_id)
            planet2 = await s.get(Planet, planet_id_2)
            assert planet1.balance == balance - amount
            assert planet2.balance == game_config.DEFAULT_BALANCE + amount


@pytest.mark.asyncio
async def test_end_current_round(
    mock_game_client, mocker, planet_id, planet_id_2, game_id, city_id
):
    orders_info = {
        planet_id: {
            OrderType.SHIELD: [city_id],
            OrderType.DEVELOP: [city_id],
            OrderType.CREATE: 1,
            OrderType.SANCTIONS: [planet_id_2],
            OrderType.INVENT: True,
            OrderType.ECO: True,
        },
        planet_id_2: {
            OrderType.ATTACK: [city_id],
            OrderType.CREATE: 2,
            OrderType.INVENT: True,
            OrderType.ECO: True
        }
    }

    async with mock_game_client.session() as s:
        game = await s.get(Game, game_id)
        game.round = 2
        game.status = GameStatus.ROUND
        await s.commit()

    mock_future = asyncio.Future()
    mock_future.set_result(None)

    mock_create_meteorites = mocker.patch.object(
        mock_game_client, "create_meteorites", return_value=mock_future
    )
    mock_develop_cities = mocker.patch.object(
        mock_game_client, "develop_cities", return_value=mock_future
    )
    mock_attack_cities = mocker.patch.object(
        mock_game_client, "attack_cities", return_value=mock_future
    )
    mock_build_shield_for_cities = mocker.patch.object(
        mock_game_client, "build_shield_for_cities", return_value=mock_future
    )
    mock_invent_for_planets = mocker.patch.object(
        mock_game_client, "invent_for_planets", return_value=mock_future
    )
    mock_send_sanctions = mocker.patch.object(
        mock_game_client, "send_sanctions", return_value=mock_future
    )
    mock_eco_boost = mocker.patch.object(
        mock_game_client, "eco_boost", return_value=mock_future
    )

    await mock_game_client.end_current_round(game_id, orders_info)

    mock_create_meteorites.assert_any_call(planet_id, 1)
    mock_create_meteorites.assert_any_call(planet_id_2, 2)
    mock_develop_cities.assert_any_call(city_id)
    mock_attack_cities.assert_any_call(city_id)
    mock_build_shield_for_cities.assert_any_call(city_id)
    mock_invent_for_planets.assert_any_call(planet_id, planet_id_2)
    mock_send_sanctions.assert_any_call(
        [SanctionDto(planet_from=planet_id, planet_to=planet_id_2, num_round=2)]
    )
    mock_eco_boost.assert_any_call(game_id, 2)

    async with mock_game_client.session() as s:
        game = await s.get(Game, game_id)
        assert game.status == GameStatus.MEETING


@pytest.mark.parametrize(
    ["status", "expected_result"],
    [
        (GameStatus.MEETING, FailureReason.SUCCESS),
        (GameStatus.WAITING, FailureReason.SUCCESS),
        (GameStatus.ROUND, FailureReason.CANNOT_START_ROUND),
    ],
)
@pytest.mark.asyncio
async def test_start_new_round(
    mock_game_client, game_id,
    admin_id, player_ids, planet_ids,
    status, expected_result
):
    result = await mock_game_client.start_new_round(admin_id)
    assert result == FailureReason.STARTING_GAME_WITHOUT_BEING_IN

    round = None
    async with mock_game_client.session() as s:
        admin = await s.get(Admin, admin_id)
        admin.game_id = game_id
        for player_id, planet_id in zip(player_ids, planet_ids):
            planet = await s.get(Planet, planet_id)
            planet.owner_id = player_id
            await s.commit()

        game = await s.get(Game, game_id)
        game.status = status
        if status != GameStatus.WAITING:
            game.round = 1
        round = game.round
        await s.commit()

    if round is None:
        round = 0

    result = await mock_game_client.start_new_round(admin_id)
    assert result == expected_result

    if result == FailureReason.SUCCESS:
        async with mock_game_client.session() as s:
            game = await s.get(Game, game_id)
            new_round = game.round
            assert new_round - round == 1
