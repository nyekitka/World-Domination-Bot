import pytest

from database.config import game_config


@pytest.mark.asyncio
async def test_get_game(mock_database_client, game_id):
    game = await mock_database_client.get_game(game_id)

    assert game
    assert game.id == game_id
    assert game.ecorate == game_config.DEFAULT_GAME_ECO_RATE


@pytest.mark.asyncio
async def test_get_non_existing_game(mock_database_client):
    game = await mock_database_client.get_game(1234567)

    assert not game


@pytest.mark.asyncio
async def test_game_by_planet_id(mock_database_client, game_id, planet_id):
    game = await mock_database_client.get_game_by_planet_id(planet_id)

    assert game
    assert game.id == game_id


@pytest.mark.asyncio
async def test_game_by_city_id(mock_database_client, game_id, city_id):
    game = await mock_database_client.get_game_by_city_id(city_id)

    assert game
    assert game.id == game_id


@pytest.mark.asyncio
async def test_get_planet(mock_database_client, planet_id):
    planet = await mock_database_client.get_planet(planet_id)

    assert planet
    assert planet.balance == game_config.DEFAULT_BALANCE
    assert not planet.meteorites
    assert not planet.is_invented


@pytest.mark.asyncio
async def test_get_city(mock_database_client, city_id):
    city = await mock_database_client.get_city(city_id)

    assert city
    assert not city.is_shielded
    assert city.development == game_config.DEFAULT_DEVELOPMENT


@pytest.mark.asyncio
async def test_get_cities_of_planet(mock_database_client, planet_id, pack):
    cities = await mock_database_client.get_cities_of_planet(planet_id)

    assert cities

    city_names = [city.name for city in cities]
    planet = pack.planets[0]
    for city in planet.cities:
        assert city.name in city_names


@pytest.mark.asyncio
async def test_get_planets_of_game(mock_database_client, game_id, pack):
    planets = await mock_database_client.get_planets_of_game(game_id)

    assert planets

    planet_names = [planet.name for planet in planets]
    for planet in pack.planets:
        assert planet.name in planet_names
