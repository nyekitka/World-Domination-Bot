from decimal import Decimal
from types import SimpleNamespace

import pytest

from database.schemas import CityDto, GameDto, PlanetDto, PlayerDto
from messages.renderer import MessageRenderer


@pytest.fixture(scope='module')
def renderer_ru() -> MessageRenderer:
    return MessageRenderer('ru')


@pytest.fixture(scope='module')
def renderer_en() -> MessageRenderer:
    return MessageRenderer('en')


@pytest.fixture
def user_ru():
    return SimpleNamespace(
        first_name='Иван',
        full_name='Иван Попов',
        id=1,
    )


@pytest.fixture
def user_en():
    return SimpleNamespace(
        first_name='Alice',
        full_name='Alice Smith',
        id=2,
    )


@pytest.fixture
def game() -> GameDto:
    return GameDto(
        id=1,
        num_planets=4,
        round=2,
        ecorate=67,
    )


@pytest.fixture
def planet() -> PlanetDto:
    return PlanetDto(
        id=1,
        game_id=1,
        name='Земля',
        is_invented=True,
        meteorites=3,
        rate_of_life=Decimal('45.5'),
    )


@pytest.fixture
def planet_not_invented() -> PlanetDto:
    return PlanetDto(
        id=2,
        game_id=1,
        name='Марс',
        is_invented=False,
        meteorites=0,
        rate_of_life=Decimal('10.0'),
    )


@pytest.fixture
def to_planet() -> PlanetDto:
    return PlanetDto(
        id=3,
        game_id=1,
        name='Юпитер',
    )


@pytest.fixture
def from_planet() -> PlanetDto:
    return PlanetDto(
        id=4,
        game_id=1,
        name='Сатурн',
    )


@pytest.fixture
def cities() -> list[CityDto]:
    return [
        CityDto(
            id=1,
            planet_id=1,
            name='Москва',
            development=0,
            rate_of_life=50.0,
        ),
        CityDto(
            id=2,
            planet_id=1,
            name='Питер',
            development=70,
            is_shielded=True,
            rate_of_life=80.0,
        ),
    ]


@pytest.fixture()
def user_dto() -> PlayerDto:
    return PlayerDto(
        tg_id=1,
        game_id=1,
    )


@pytest.fixture()
def user_dto_without_game() -> PlayerDto:
    return PlayerDto(
        tg_id=1,
        game_id=None,
    )
