import functools
import logging
from typing import (
    Awaitable,
    Callable,
    Concatenate,
    ParamSpec,
    TypeVar,
    Self
)

from async_lru import alru_cache
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.orm import joinedload, selectinload

from database.config import database_config
from database.models import (
    City,
    Game,
    Planet,
    ModelBase,
    Sanction,
)
from database.schemas import (
    CityDto,
    GameDto,
    PlanetDto,
    SanctionDto,
)
from game.config import game_config

logger = logging.getLogger(__name__)

ReturnType = TypeVar('ReturnType')
ParamsType = ParamSpec('ParamsType')
ClientType = TypeVar('ClientType', bound='DatabaseClient')


class DatabaseClient:
    def __init__(self, session: async_sessionmaker[AsyncSession]):
        self.session = session

    @staticmethod
    def set_transaction(
        method: Callable[Concatenate[ClientType, AsyncSession, ParamsType], Awaitable[ReturnType]]
    ) -> Callable[Concatenate[ClientType, ParamsType], Awaitable[ReturnType]]:
        @functools.wraps(method)
        async def wrapper(
            self: ClientType,
            *args: ParamsType.args,
            **kwargs: ParamsType.kwargs
        ) -> ReturnType:
            async with self.session() as s:
                res = await method(self, s, *args, **kwargs)
                await s.commit()
            return res

        return wrapper

    @staticmethod
    def get_transaction(
        method: Callable[Concatenate[ClientType, AsyncSession, ParamsType], Awaitable[ReturnType]]
    ) -> Callable[Concatenate[ClientType, ParamsType], Awaitable[ReturnType]]:
        @functools.wraps(method)
        async def wrapper(
            self: ClientType,
            *args: ParamsType.args,
            **kwargs: ParamsType.kwargs
        ) -> ReturnType:
            async with self.session() as s:
                res = await method(self, s, *args, **kwargs)
                return res

        return wrapper

    @classmethod
    async def create(cls, engine: AsyncEngine):
        self = cls()
        self.session = async_sessionmaker(engine)
        async with engine.begin() as conn:
            await conn.run_sync(ModelBase.metadata.create_all)
        return self

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    @get_transaction
    async def get_game(self, s: AsyncSession, game_id: int) -> GameDto | None:
        game = await s.get(Game, game_id)
        if game:
            return GameDto.model_validate(game)

        return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    @get_transaction
    async def get_game_by_planet_id(
        self, s: AsyncSession, planet_id: int
    ) -> GameDto | None:
        stmt = (
            select(Game)
            .join(Planet, Game.id == Planet.game_id)
            .where(Planet.id == planet_id)
        )

        res = await s.execute(stmt)
        game = res.scalars().first()
        if game:
            return GameDto.model_validate(game)

        return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    @get_transaction
    async def get_game_by_city_id(
        self, s: AsyncSession, city_id: int
    ) -> GameDto | None:
        stmt = (
            select(Game)
            .join(Planet, Game.id == Planet.game_id)
            .join(City, City.planet_id == Planet.id)
            .where(City.id == city_id)
        )

        res = await s.execute(stmt)
        game = res.scalars().first()
        if game:
            return GameDto.model_validate(game)

        return None

    @get_transaction
    async def get_city(self, s: AsyncSession, city_id: int) -> CityDto | None:
        city = await s.get(City, city_id)
        if city:
            return CityDto.model_validate(city)
        return None

    @get_transaction
    async def get_planet(
        self,
        s: AsyncSession,
        planet_id: int,
        load_development: bool = True,
    ) -> PlanetDto | None:
        options = ()
        if load_development:
            options = (
                selectinload(Planet.cities),
                joinedload(Planet.game)
            )
        planet = (await s.execute(
            select(Planet)
            .options(*options)
            .where(Planet.id == planet_id)
        )).scalar_one_or_none()
        if planet:
            return PlanetDto.model_validate(planet)
        return None
    
    @get_transaction
    async def get_planet_by_city_id(
        self, s: AsyncSession, city_id: int
    ) -> PlanetDto | None:
        city_res = await s.execute(
            select(Planet).
            join(City, City.planet_id == Planet.id)
            .where(City.id == city_id)
        )
        city = city_res.scalar_one_or_none()
        if city:
            return CityDto.model_validate(city)
        return None

    @get_transaction
    async def get_player_planet(
        self,
        s: AsyncSession,
        player_id: int,
        game_id: int,
        load_development: bool = True,
    ) -> PlanetDto | None:
        options = ()
        if load_development:
            options = (
                selectinload(Planet.cities),
                joinedload(Planet.game)
            )
        result = await s.execute(
            select(Planet)
            .options(*options)
            .where(
                Planet.owner_id == player_id,
                Planet.game_id == game_id
            )
        )
        planet = result.scalar_one_or_none()
        if planet:
            return PlanetDto.model_validate(planet)
        return None

    @get_transaction
    async def get_cities_of_planet(
        self, s: AsyncSession, planet_id: int, only_alive: bool = True
    ) -> list[CityDto] | None:
        if only_alive:
            stmt = select(City).where(
                City.planet_id == planet_id and City.development > 0
            )
        else:
            stmt = select(City).where(City.planet_id == planet_id)
        result = await s.execute(stmt)
        if result:
            return TypeAdapter(list[CityDto]).validate_python(result.scalars().all())
        return None

    @get_transaction
    async def get_planets_of_game(
        self,
        s: AsyncSession,
        game_id: int,
        load_development: bool = True,
    ) -> list[PlanetDto] | None:
        options = ()
        if load_development:
            options = (
                selectinload(Planet.cities),
                joinedload(Planet.game)
            )
        planets = (await s.execute(
            select(Planet)
            .options(*options)
            .where(Planet.game_id == game_id)
        )).scalars().all()

        logger.debug(f'Planets[0].development: {planets[0].development}')

        if planets:
            return TypeAdapter(list[PlanetDto]).validate_python(planets)
        return None

    async def _clear_game_cache(self, game_id: int, soft: bool = False) -> None:
        self.get_game.cache_invalidate(game_id)
        if soft:
            return

        async with self.session() as s:
            res_planets = await s.execute(
                (select(Planet).where(Planet.game_id == Game.id))
            )
            all_planets = [planet.id for planet in res_planets.scalars().all()]
            res_cities = await s.execute(
                (select(City).where(City.planet_id.in_(all_planets)))
            )
            all_cities = [city.id for city in res_cities.scalars().all()]
        for planet_id in all_planets:
            self.get_game_by_planet_id.cache_invalidate(planet_id)

        for city_id in all_cities:
            self.get_game_by_city_id.cache_invalidate(city_id)

    def _rate_of_life_in_city(self, city: CityDto, eco_rate: int) -> float:
        return city.development * eco_rate / 100

    async def _rate_of_life_in_planet(self, planet_id: int, eco_rate: int) -> float:
        cities = await self.get_cities_of_planet(planet_id, False)
        return sum(self._rate_of_life_in_city(city, eco_rate) for city in cities) / len(
            cities
        )

    def _city_income(self, city: CityDto, eco_rate: int) -> float:
        return game_config.INCOME_COEFFICIENT * self._rate_of_life_in_city(
            city, eco_rate
        )

    async def _planet_income(
        self, planet_id: int, eco_rate: int, number_of_planets: int
    ) -> float:
        cities = await self.get_cities_of_planet(planet_id, False)
        sanctions = await self.get_all_sanctions_on_planet(planet_id)
        sanc_cofficient = (number_of_planets - len(sanctions)) / (len(sanctions) + 1)
        return (
            sum(self._city_income(city, eco_rate) for city in cities) * sanc_cofficient
        )

    @get_transaction
    async def get_all_sanctions_on_planet(
        self, s: AsyncSession, planet_id: int
    ) -> list[SanctionDto]:
        sanctions_res = await s.execute(
            (select(Sanction).where(Sanction.planet_to == planet_id))
        )
        sanctions = sanctions_res.scalars().all()
        return TypeAdapter(list[SanctionDto]).validate_python(sanctions)
