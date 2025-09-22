import logging
from typing import Awaitable

from async_lru import alru_cache
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from database.config import database_config, game_config
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

logger = logging.getLogger(__name__)


class DatabaseClient:
    def __init__(self, session: async_sessionmaker[AsyncSession]):
        self.session = session

    @staticmethod
    def set_transaction(method: Awaitable) -> Awaitable:
        async def wrapper(self, *args, **kwargs) -> None:
            async with self.session() as s:
                res = await method(self, s, *args, **kwargs)
                await s.commit()
            return res

        return wrapper

    @staticmethod
    def get_transaction(method: Awaitable) -> Awaitable:
        async def wrapper(self, *args, **kwargs):
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
    async def get_planet(self, s: AsyncSession, planet_id: int) -> PlanetDto | None:
        planet = await s.get(Planet, planet_id)
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
        self, s: AsyncSession, game_id: int
    ) -> list[PlanetDto] | None:
        result = await s.execute((select(Planet).where(Planet.game_id == game_id)))
        if result:
            return TypeAdapter(list[PlanetDto]).validate_python(result.scalars().all())
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
