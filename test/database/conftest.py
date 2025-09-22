import pytest
import pytest_asyncio
from pytest_postgresql import factories
from pytest_postgresql.janitor import DatabaseJanitor

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from database.base_client import DatabaseClient
from database.clients import ActionsClient, GameClient, UserClient
from database.models import Admin, City, Game, ModelBase, Planet, Player
from database.schemas import GameStatus
from presets.pack import Pack, PackCity, PackPlanet


test_db = factories.postgresql_noproc(
    dbname="test_db", port="5432", user="postgres", password="123", host="test-db"
)


@pytest.fixture()
def admin_id() -> int:
    return 1


@pytest.fixture()
def player_id() -> int:
    return 2


@pytest.fixture()
def non_existing_user_id() -> int:
    return 123


@pytest.fixture()
def player_ids() -> list[int]:
    return list(range(2, 6))


@pytest.fixture()
def game_id() -> int:
    return 1


@pytest.fixture()
def planet_id() -> int:
    return 1


@pytest.fixture()
def planet_id_2() -> int:
    return 2


@pytest.fixture()
def planet_id_3() -> int:
    return 3


@pytest.fixture()
def planet_ids() -> list[int]:
    return list(range(1, 5))


@pytest.fixture()
def city_id() -> int:
    return 1


@pytest.fixture()
def city_id_2() -> int:
    return 2


@pytest.fixture()
def non_existing_city_id() -> int:
    return 0


@pytest.fixture()
def non_existing_planet_id() -> int:
    return 0


@pytest.fixture()
def non_existing_game_id() -> int:
    return 0


@pytest.fixture()
def pack() -> Pack:
    return Pack(
        name="pack",
        planets=[
            PackPlanet(
                name="Planet1",
                cities=[
                    PackCity(name="City11"),
                    PackCity(name="City12"),
                    PackCity(name="City13"),
                    PackCity(name="City14"),
                ],
            ),
            PackPlanet(
                name="Planet2",
                cities=[
                    PackCity(name="City21"),
                    PackCity(name="City22"),
                    PackCity(name="City23"),
                    PackCity(name="City24"),
                ],
            ),
            PackPlanet(
                name="Planet3",
                cities=[
                    PackCity(name="City31"),
                    PackCity(name="City32"),
                    PackCity(name="City33"),
                    PackCity(name="City34"),
                ],
            ),
            PackPlanet(
                name="Planet4",
                cities=[
                    PackCity(name="City41"),
                    PackCity(name="City42"),
                    PackCity(name="City43"),
                    PackCity(name="City44"),
                ],
            ),
        ],
    )


@pytest.fixture()
def planet_name_to_id() -> dict[str, int]:
    return {
        "Planet1": 1,
        "Planet2": 2,
        "Planet3": 3,
        "Planet4": 4,
    }


@pytest.fixture()
def city_name_to_id() -> dict[str, int]:
    return {
        "City11": 1,
        "City12": 2,
        "City13": 3,
        "City14": 4,
        "City21": 5,
        "City22": 6,
        "City23": 7,
        "City24": 8,
        "City31": 9,
        "City32": 10,
        "City33": 11,
        "City34": 12,
        "City41": 13,
        "City42": 14,
        "City43": 15,
        "City44": 16,
    }


@pytest_asyncio.fixture
async def mock_session(pack, admin_id, player_ids, game_id, planet_name_to_id, test_db):
    with DatabaseJanitor(
        user=test_db.user,
        dbname=test_db.dbname,
        host=test_db.host,
        port=test_db.port,
        password=test_db.password,
        version=test_db.version,
    ):
        engine = create_async_engine(
            f"postgresql+asyncpg://{test_db.user}:{test_db.password}"
            f"@{test_db.host}:{test_db.port}/{test_db.dbname}",
            echo=True,
        )
        session = async_sessionmaker(engine)
        async with engine.begin() as conn:
            await conn.run_sync(ModelBase.metadata.drop_all)
            await conn.run_sync(ModelBase.metadata.create_all)

        admin = Admin(tg_id=admin_id)
        players = [Player(tg_id=tg_id) for tg_id in player_ids]
        game = Game(status=GameStatus.WAITING)

        planets = []
        cities = []
        for planet_pack in pack.planets:
            planets.append(Planet(name=planet_pack.name, game_id=game_id))
            for city_pack in planet_pack.cities:
                cities.append(
                    City(
                        name=city_pack.name,
                        planet_id=planet_name_to_id[planet_pack.name],
                    )
                )

        async with session() as s:
            s.add(game)
            await s.commit()
            s.add(admin)
            s.add_all(players)
            await s.commit()
            s.add_all(planets)
            await s.commit()
            s.add_all(cities)
            await s.commit()

        yield session


@pytest.fixture()
def mock_database_client(mock_session):
    client = DatabaseClient(mock_session)
    yield client


@pytest.fixture()
def mock_actions_client(mock_session):
    client = ActionsClient(mock_session)
    yield client


@pytest.fixture()
def mock_user_client(mock_session):
    client = UserClient(mock_session)
    yield client


@pytest.fixture()
def mock_game_client(mock_session):
    client = GameClient(mock_session)
    yield client
