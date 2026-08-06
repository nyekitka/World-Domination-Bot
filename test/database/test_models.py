from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from database.models import City, Game, Planet, Sanction
from game.config import game_config


@pytest.mark.asyncio
async def test_rate_of_life_and_income_instance_loaded(session, city_id):
    """Тест вычислений на уровне Python (инстанса), когда связи загружены."""
    stmt = (
        select(City)
        .options(joinedload(City.planet).joinedload(Planet.game))
        .where(City.id == city_id)
    )
    city = (await session.execute(stmt)).scalar_one()

    # Устанавливаем предсказуемые значения
    city.development = 50
    city.planet.game.ecorate = 90

    expected_rate = Decimal('45.0')
    assert city.rate_of_life == expected_rate

    assert city.income == int(game_config.INCOME_COEFFICIENT * float(expected_rate))


@pytest.mark.asyncio
async def test_rate_of_life_and_income_instance_unloaded(session, city_id):
    stmt = select(City).where(City.id == city_id)
    city = (await session.execute(stmt)).scalar_one()

    assert city.rate_of_life is None
    assert city.income is None


@pytest.mark.asyncio
async def test_rate_of_life_and_income_expression(session, city_id, game_id):
    city = await session.get(City, city_id)
    city.development = 50
    game = await session.get(Game, city_id)
    game.ecorate = 90
    await session.commit()

    stmt = select(City.rate_of_life, City.income).where(City.id == city_id)
    result = await session.execute(stmt)
    rate_expr, income_expr = result.one()

    expected_rate = Decimal('45.0')
    expected_income = int(game_config.INCOME_COEFFICIENT * float(expected_rate))

    assert rate_expr == expected_rate
    assert income_expr == expected_income


@pytest.mark.asyncio
async def test_rate_of_life_instance_loaded(session, planet_id):
    stmt = (
        select(Planet)
        .options(joinedload(Planet.game), joinedload(Planet.cities))
        .where(Planet.id == planet_id)
    )
    planet = (await session.execute(stmt)).unique().scalar_one()

    planet.game.ecorate = 100
    # Задаем городам развитие: 10, 20, 30, 40 -> среднее 25
    for i, city in enumerate(planet.cities):
        city.development = 10 * (i + 1)

    expected_rate = Decimal('25.0')
    assert planet.rate_of_life == expected_rate

    with pytest.raises(NotImplementedError):
        _ = planet.income


@pytest.mark.asyncio
async def test_rate_of_life_instance_unloaded_and_empty(session, game_id):
    stmt = select(Planet).limit(1)
    planet = (await session.execute(stmt)).scalar_one()
    assert planet.rate_of_life is None

    empty_planet = Planet(name='EmptyPlanet', game_id=game_id)
    session.add(empty_planet)
    await session.flush()

    stmt_loaded = (
        select(Planet)
        .options(joinedload(Planet.game), joinedload(Planet.cities))
        .where(Planet.id == empty_planet.id)
    )
    empty_planet_loaded = (await session.execute(stmt_loaded)).unique().scalar_one()
    
    assert empty_planet_loaded.rate_of_life == Decimal('0.0')


@pytest.mark.asyncio
async def test_rate_of_life_and_income_expression(
    session, planet_id, planet_id_2, game_id
):
    stmt = select(Planet).options(selectinload(Planet.cities)).where(Planet.id == planet_id)
    planet = (await session.execute(stmt)).scalar_one()

    game = await session.get(Game, game_id)
    game.ecorate = 60
    game.round = 2

    # Выставляем развитие городам для среднего = 25
    for i, city in enumerate(planet.cities):
        city.development = 10 * (i + 1)

    sanction = Sanction(
        planet_from=planet_id_2,
        planet_to=planet_id,
        num_round=game.round - 1
    )
    session.add(sanction)
    await session.commit()

    stmt_expr = select(Planet.rate_of_life, Planet.income).where(Planet.id == planet_id)
    result = await session.execute(stmt_expr)
    rate_expr, income_expr = result.one()

    assert rate_expr == Decimal('15.0')

    # Planet's income is the sum of cities' incomes multiplied by sanctions factor
    # Sanctions factor: 1 - 1 * 0.6 / 4 = 0.85
    # City's income equals its rate of life multiplied by eco rate and by 3
    # So income equals
    # 0.6 * 3 * 0.85 * (10 + 20 + 30 + 40) = 153
    expected_planet_income = 153

    assert income_expr == expected_planet_income
