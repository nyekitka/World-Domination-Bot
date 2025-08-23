from uuid import uuid4

import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from database.base_client import DatabaseClient
from database.clients import (
    ActionsClient,
    GameClient,
    UserClient
)
from database.models import Admin, City, Game, ModelBase, Planet, Player
from database.schemas import GameStatus
from presets.pack import Pack, PackCity, PackPlanet


@pytest.fixture(scope='session')
def mock_admin_id():
    return 1


@pytest.fixture(scope='session')
def mock_player_ids():
    return list(range(4))


@pytest.fixture(scope='session')
def game_id():
    return 1
    

@pytest.fixture()
def planet_id() -> int:
    return 1

@pytest.fixture()
def city_id() -> int:
    return 11


@pytest.fixture()
def non_existing_city_id():
    return 0


@pytest.fixture()
def non_existing_planet_id():
    return 0


@pytest.fixture()
def non_existing_game_id():
    return 0


@pytest.fixture(scope='session')
def mock_pack() -> Pack:
    return Pack(
        name='pack',
        planets=[
            PackPlanet(
                name='Planet1',
                cities=[
                    PackCity(name='City11'),
                    PackCity(name='City12'),
                    PackCity(name='City13'),
                    PackCity(name='City14'),
                ]
            ),
            PackPlanet(
                name='Planet2',
                cities=[
                    PackCity(name='City21'),
                    PackCity(name='City22'),
                    PackCity(name='City23'),
                    PackCity(name='City24'),
                ]
            ),
            PackPlanet(
                name='Planet3',
                cities=[
                    PackCity(name='City31'),
                    PackCity(name='City32'),
                    PackCity(name='City33'),
                    PackCity(name='City34'),
                ]
            ),
            PackPlanet(
                name='Planet4',
                cities=[
                    PackCity(name='City41'),
                    PackCity(name='City42'),
                    PackCity(name='City43'),
                    PackCity(name='City44'),
                ]
            ),
        ]
    )


@pytest.fixture(scope='session')
def planet_name_to_id():
    return {
        'Planet1': 1,
        'Planet2': 2,
        'Planet3': 3,
        'Planet4': 4,
    }


@pytest.fixture(scope='session')
def city_name_to_id():
    return {
        'City11': 11,
        'City12': 12,
        'City13': 13,
        'City14': 14,
        'City21': 21,
        'City22': 22,
        'City23': 23,
        'City24': 24,
        'City31': 31,
        'City32': 32,
        'City33': 33,
        'City34': 34,
        'City41': 41,
        'City42': 42,
        'City43': 43,
        'City44': 44,
    }


@pytest_asyncio.fixture(scope='session')
async def mock_engine(
    mock_pack,
    mock_admin_id,
    mock_player_ids,
    game_id,
    planet_name_to_id,
    city_name_to_id
) -> AsyncEngine:
    engine = create_async_engine(
        "sqlite+aiosqlite:///test.db"
    )
    session = async_sessionmaker(engine)
    async with engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.drop_all)
        await conn.run_sync(ModelBase.metadata.create_all)

    admin = Admin(tg_id=mock_admin_id)
    players = [
        Player(tg_id=tg_id)
        for tg_id in mock_player_ids
    ]
    game = Game(id=game_id, status=GameStatus.WAITING)

    planets = []
    cities = []
    for planet_pack in mock_pack.planets:
        planets.append(
            Planet(
                id=planet_name_to_id[planet_pack.name],
                name=planet_pack.name,
                game_id=game_id
            )
        )
        for city_pack in planet_pack.cities:
            cities.append(
                City(
                    id=city_name_to_id[city_pack.name],
                    name=city_pack.name,
                    planet_id=planet_name_to_id[planet_pack.name]
                )
            )

    async with session() as s:
        s.add(admin)
        s.add_all(players)
        s.add(game)
        s.add_all(planets)
        s.add_all(cities)
        await s.commit()
    
    return engine


@pytest_asyncio.fixture()
async def mock_database_client(mock_engine) -> DatabaseClient:
    client = await DatabaseClient.create(mock_engine)
    return client



@pytest_asyncio.fixture()
async def mock_actions_client(mock_engine) -> ActionsClient:
    client = await ActionsClient.create(mock_engine)
    return client


@pytest_asyncio.fixture()
async def mock_user_client(mock_engine) -> UserClient:
    client = await UserClient.create(mock_engine)
    return client


@pytest_asyncio.fixture()
async def mock_game_client(mock_engine) -> GameClient:
    client = await GameClient.create(mock_engine)
    return client
