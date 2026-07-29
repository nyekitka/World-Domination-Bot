import pytest

from game.config import game_config


@pytest.mark.asyncio
async def test_get_game(database_client, session, game_id):
    game = await database_client.get_game(session, game_id)

    assert game
    assert game.id == game_id
    assert game.ecorate == game_config.DEFAULT_GAME_ECO_RATE


@pytest.mark.asyncio
async def test_get_non_existing_game(database_client, session):
    game = await database_client.get_game(session, 1234567)

    assert not game


@pytest.mark.asyncio
async def test_game_by_planet_id(database_client, session, game_id, planet_id):
    game = await database_client.get_game_by_planet_id(session, planet_id)

    assert game
    assert game.id == game_id


@pytest.mark.asyncio
async def test_game_by_city_id(database_client, session, game_id, city_id):
    game = await database_client.get_game_by_city_id(session, city_id)

    assert game
    assert game.id == game_id


@pytest.mark.asyncio
async def test_get_planet(database_client, session, planet_id):
    planet = await database_client.get_planet(session, planet_id)

    assert planet
    assert planet.balance == game_config.DEFAULT_BALANCE
    assert not planet.meteorites
    assert not planet.is_invented
    assert planet.development == game_config.DEFAULT_DEVELOPMENT * game_config.DEFAULT_GAME_ECO_RATE / 100

    same_planet = await database_client.get_planet(session, planet_id, False)
    assert same_planet.development is None


@pytest.mark.asyncio
async def test_get_city(database_client, session, city_id):
    city = await database_client.get_city(session, city_id)

    assert city
    assert not city.is_shielded
    assert city.development == game_config.DEFAULT_DEVELOPMENT


@pytest.mark.asyncio
async def test_get_cities_of_planet(
    database_client, session, planet_id, pack
):
    cities = await database_client.get_cities_of_planet(session, planet_id)

    assert cities

    for city in cities:
        assert city.rate_of_life == game_config.DEFAULT_GAME_ECO_RATE / 100 * game_config.DEFAULT_DEVELOPMENT

    city_names = [city.name for city in cities]
    planet = pack.planets[0]
    for city in planet.cities:
        assert city.name in city_names


@pytest.mark.asyncio
async def test_get_planets_of_game(database_client, session, game_id, pack):
    planets = await database_client.get_planets_of_game(session, game_id)

    assert planets

    planet_names = [planet.name for planet in planets]
    for planet in pack.planets:
        assert planet.name in planet_names
