import asyncio

import pytest
from pytest_lazy_fixtures import lf
from sqlalchemy import select

from database.models import (
    Admin, City, Game,
    Negotiation, Order, Planet,
    Player, RoundInfo, Sanction
)
from database.schemas import CityData, GameData, GameStatus, OrderDto, PlanetData, RoundInfoDto, SanctionDto
from game.config import game_config
from game.schemas import FailureReason, OrderType
from game.schemas import OrderInfo


@pytest.mark.asyncio
async def test_get_games(game_client, session, game_id):
    games = await game_client.get_all_games(session)
    assert len(games) == 1
    assert games[0].id == game_id


@pytest.mark.parametrize(
    'num_planets',
    (-1, 2, 6)
)
@pytest.mark.asyncio
async def test_create_game(
    game_client, session, admin_id, pack, num_planets
):
    game = await game_client.create_game(session, admin_id, pack, num_planets)
    if num_planets == -1:
        num_planets = len(pack.planets)
    
    admin = await session.get(Admin, admin_id)
    assert admin.game_id == game.id
    for i, planet in enumerate(pack.planets):
        result = await session.execute(
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
            result = await session.execute(
                select(City).where(
                    City.name == city.name, City.planet_id == orm_planet.id
                )
            )
            orm_city = result.scalar_one_or_none()
            assert orm_city


@pytest.mark.asyncio
async def test_end_game(game_client, session, game_id, player_ids, admin_id):
    admin = await session.get(Admin, admin_id)
    admin.game_id = game_id
    for player_id in player_ids:
        player = await session.get(Player, player_id)
        player.game_id = game_id
    await session.commit()

    await game_client.end_game(session, game_id)

    admin = await session.get(Admin, admin_id)
    assert admin.game_id is None
    for player_id in player_ids:
        player = await session.get(Player, player_id)
        assert player.game_id is None

    game = await session.get(Game, game_id)
    assert game.status == GameStatus.ENDED


@pytest.mark.asyncio
async def test_get_all_active_players(
    game_client, session, player_ids, game_id
):
    for player_id in player_ids:
        player_model = await session.get(Player, player_id)
        player_model.game_id = game_id
        await session.commit()
        
    result = await game_client.get_all_active_players(session, game_id)
    ids = {player.tg_id for player in result}
    assert ids == set(player_ids)


@pytest.mark.asyncio
async def test_get_all_active_admins(
    game_client, session, admin_id, player_ids, game_id
):
    for player_id in player_ids:
        player_model = await session.get(Player, player_id)
        player_model.game_id = game_id
        await session.commit()
    admin = await session.get(Admin, admin_id)
    admin.game_id = game_id
    await session.commit()
        
    result = await game_client.get_all_active_admins(session, game_id)
    assert len(result) == 1
    assert result[0].tg_id == admin_id


@pytest.mark.asyncio
async def test_get_all_planets_in_game(
    game_client, session, game_id, pack
):
    planets = await game_client.get_all_planets_in_game(session, game_id)
    
    actual_planet_names = {planet.name for planet in planets}
    true_planet_names = {planet.name for planet in pack.planets}
    assert actual_planet_names == true_planet_names

@pytest.mark.asyncio
async def test_build_shield_for_cities(game_client, session, city_id, city_id_2):
    await game_client.build_shield_for_cities(session, city_id, city_id_2)

    city1 = await session.get(City, city_id)
    city2 = await session.get(City, city_id_2)

    assert city1.is_shielded
    assert city2.is_shielded


@pytest.mark.asyncio
async def test_develop_cities(game_client, session, city_id, city_id_2):
    city1 = await session.get(City, city_id)
    city2 = await session.get(City, city_id_2)
    development1 = city1.development
    development2 = city2.development

    await game_client.develop_cities(session, city_id, city_id_2)

    city1 = await session.get(City, city_id)
    city2 = await session.get(City, city_id_2)

    assert city1.development - development1 == game_config.DEVELOPMENT_BOOST
    assert city2.development - development2 == game_config.DEVELOPMENT_BOOST


@pytest.mark.asyncio
async def test_invent_for_planets(game_client, session, planet_id, planet_id_2):
    await game_client.invent_for_planets(session, planet_id, planet_id_2)

    planet = await session.get(Planet, planet_id)
    planet_2 = await session.get(Planet, planet_id_2)

    assert planet.is_invented
    assert planet_2.is_invented


@pytest.mark.parametrize(
    ["num_to_create", "meteorites", "result"], [(1, 2, 3), (2, 2, 4)]
)
@pytest.mark.asyncio
async def test_create_meteorites(
    game_client, session, planet_id, num_to_create, meteorites, result
):
    planet = await session.get(Planet, planet_id)
    planet.meteorites = meteorites
    await session.commit()

    await game_client.create_meteorites(session, planet_id, num_to_create)

    planet = await session.get(Planet, planet_id)
    assert planet.meteorites == result


@pytest.mark.asyncio
async def test_attack_cities(
    game_client, session, city_id, city_id_2, city_id_3, game_id
):
    city1 = await session.get(City, city_id)
    city2 = await session.get(City, city_id_2)
    game = await session.get(Game, game_id)
    game.round = 1
    city1.is_shielded = True
    city2.is_shielded = True
    await session.commit()

    await game_client.attack_cities(session, city_id, city_id, city_id_2, city_id_3)

    await session.refresh(city1)
    await session.refresh(city2)
    city3 = await session.get(City, city_id_3)

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
async def test_eco_boost(game_client, session, game_id, times, result):
    await game_client.eco_boost(session, game_id, times)

    game = await session.get(Game, game_id)
    assert game.ecorate == result


@pytest.mark.asyncio
async def test_send_sanctions(game_client, session, planet_id, planet_id_2):
    sanctions = [
        SanctionDto(planet_from=planet_id, planet_to=planet_id_2, num_round=1),
        SanctionDto(planet_from=planet_id_2, planet_to=planet_id, num_round=1),
    ]

    await game_client.send_sanctions(session, sanctions)

    for sanction in sanctions:
        db_sanc = await session.get(
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
    game_client, session, planet_id, planet_id_2, balance, amount, result
):
    planet = await session.get(Planet, planet_id)
    planet.balance = balance
    await session.commit()

    res = await game_client.transfer(session, planet_id, planet_id_2, amount)
    assert res == result

    if result == FailureReason.SUCCESS:
        planet1 = await session.get(Planet, planet_id)
        planet2 = await session.get(Planet, planet_id_2)
        assert planet1.balance == balance - amount
        assert planet2.balance == game_config.DEFAULT_BALANCE + amount


@pytest.mark.asyncio
async def test_end_current_round(
    game_client, session, mocker,
    planet_id, planet_id_2, game_id, city_id
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

    game = await session.get(Game, game_id)
    game.round = 2
    game.status = GameStatus.ROUND
    await session.commit()

    mock_future = asyncio.Future()
    mock_future.set_result(None)

    mock_create_meteorites = mocker.patch.object(
        game_client, "create_meteorites", return_value=mock_future
    )
    mock_develop_cities = mocker.patch.object(
        game_client, "develop_cities", return_value=mock_future
    )
    mock_attack_cities = mocker.patch.object(
        game_client, "attack_cities", return_value=mock_future
    )
    mock_build_shield_for_cities = mocker.patch.object(
        game_client, "build_shield_for_cities", return_value=mock_future
    )
    mock_invent_for_planets = mocker.patch.object(
        game_client, "invent_for_planets", return_value=mock_future
    )
    mock_send_sanctions = mocker.patch.object(
        game_client, "send_sanctions", return_value=mock_future
    )
    mock_eco_boost = mocker.patch.object(
        game_client, "eco_boost", return_value=mock_future
    )

    await game_client.end_current_round(session, game_id, orders_info)
    await session.commit()

    mock_create_meteorites.assert_any_call(session, planet_id, 1)
    mock_create_meteorites.assert_any_call(session, planet_id_2, 2)
    mock_develop_cities.assert_any_call(session, city_id)
    mock_attack_cities.assert_any_call(session, city_id)
    mock_build_shield_for_cities.assert_any_call(session, city_id)
    mock_invent_for_planets.assert_any_call(session, planet_id, planet_id_2)
    mock_send_sanctions.assert_any_call(
        session,
        [SanctionDto(planet_from=planet_id, planet_to=planet_id_2, num_round=2)]
    )
    mock_eco_boost.assert_any_call(session, game_id, 2)

    game = await session.get(Game, game_id)
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
    game_client, game_id, session,
    admin_id, player_ids, planet_ids,
    status, expected_result
):
    result = await game_client.start_new_round(session, admin_id)
    assert result == FailureReason.STARTING_GAME_WITHOUT_BEING_IN

    round = None

    admin = await session.get(Admin, admin_id)
    admin.game_id = game_id
    for player_id, planet_id in zip(player_ids, planet_ids):
        planet = await session.get(Planet, planet_id)
        planet.owner_id = player_id
        await session.commit()

    game = await session.get(Game, game_id)
    game.status = status
    if status != GameStatus.WAITING:
        game.round = 1
    round = game.round
    await session.commit()

    if round is None:
        round = 0

    result = await game_client.start_new_round(session, admin_id)
    assert result == expected_result

    if result == FailureReason.SUCCESS:
        game = await session.get(Game, game_id)
        new_round = game.round
        assert new_round - round == 1


@pytest.mark.asyncio
async def test_save_round_info(
    game_client, session, game_id, city_id
):
    game = await session.get(Game, game_id)
    game.round = 2
    game.ecorate = 20

    city = await session.get(City, city_id)
    city.development = 15
    city_name = city.name
    await session.commit()

    await game_client.save_round_info(session, game_id)

    round_info = await session.get(RoundInfo, {'game_id': game_id, 'round': 2})
    assert round_info.info['eco_rate'] == 20

    for planet in round_info.info['planets_data']:
        for city in planet['cities_data']:
            if city['name'] == city_name:
                assert city['development'] == 15
                break

@pytest.mark.asyncio
async def test_get_round_info(
    game_client, session, game_id
):
    round_info = RoundInfo(
        game_id=game_id,
        round=1,
        info={
            'eco_rate': 13,
            'planets_data': [
                {
                    'name': 'Planet',
                    'development': 10,
                    'cities_data': [
                        {
                            'name': 'City',
                            'development': 9
                        }
                    ]
                }
            ]
        }
    )
    session.add(round_info)
    await session.commit()

    expected_result = RoundInfoDto(
        game_id=game_id,
        round=1,
        info=GameData(
            eco_rate=13,
            planets_data=[
                PlanetData(
                    name='Planet',
                    development=10,
                    cities_data=[CityData(
                        name='City',
                        development=9,
                    )],
                )
            ]
        )
    )

    result = await game_client.get_round_info(session, game_id, 1)
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_all_planets_and_cities(
    game_client, session, game_id, pack
):
    result = await game_client.get_all_planets_and_cities(session, game_id)
    for planet_id in result:
        planet, cities = result[planet_id]
        pack_planet = None
        for p in pack.planets:
            if p.name == planet.name:
                pack_planet = p
                break
        else:
            pytest.fail(f'Some unknown planet found in result: {planet.name}')
        
        assert planet.development is not None
        for city in cities:
            assert any([
                city.name == pack_city.name
                for pack_city in pack_planet.cities
            ])
@pytest.mark.parametrize(
    ('sanction_round', 'expected_result'),
    [
        (1, [lf('planet_id_2'), lf('planet_id_3')]),
        (2, [])
    ]
)
@pytest.mark.asyncio
async def test_get_sanctioned_planets(
    game_client, session, planet_id, planet_id_2, planet_id_3,
    game_id, sanction_round, expected_result
):
    game = await session.get(Game, game_id)
    game.round = 2
    
    sanctions = [Sanction(
        planet_from=planet_id,
        planet_to=other_planet,
        num_round=sanction_round
    ) for other_planet in (planet_id_2, planet_id_3)]
    session.add_all(sanctions)
    await session.commit()
    
    result = await game_client.get_sanctioned_planets(session, planet_id)
    sanctioned_ids = [
        planet.id for planet in result
    ]
    assert sanctioned_ids == expected_result
