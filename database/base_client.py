import logging

from async_lru import alru_cache
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
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
    @classmethod
    async def create(cls, engine: AsyncEngine):
        self = cls()
        self.session = async_sessionmaker(engine)
        async with engine.begin() as conn:
            await conn.run_sync(ModelBase.metadata.create_all)
        return self

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_game(self, game_id: int) -> GameDto | None:
        async with self.session() as s:
            game = await s.get(Game, game_id)
            if game:
                return GameDto.model_validate(game)

            return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_game_by_planet_id(self, planet_id: int) -> GameDto | None:
        stmt = (
            select(Game)
            .join(Planet, Game.id == Planet.game_id)
            .where(Planet.id == planet_id)
        )
        async with self.session() as s:
            res = await s.execute(stmt)
            game = res.scalars().first()
            if game:
                return GameDto.model_validate(game)

            return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_game_by_city_id(self, city_id: int) -> GameDto | None:
        stmt = (
            select(Game)
            .join(Planet, Game.id == Planet.game_id)
            .join(City, City.planet_id == Planet.id)
            .where(City.id == city_id)
        )
        async with self.session() as s:
            res = await s.execute(stmt)
            game = res.scalars().first()
            if game:
                return GameDto.model_validate(game)

            return None

    async def get_city(self, city_id: int) -> CityDto | None:
        async with self.session() as s:
            city = await s.get(City, city_id)
            if city:
                return CityDto.model_validate(city)
            return None

    async def get_planet(self, planet_id: int) -> PlanetDto | None:
        async with self.session() as s:
            planet = await s.get(Planet, planet_id)
            if planet:
                return PlanetDto.model_validate(planet)
            return None

    async def get_cities_of_planet(
        self, planet_id: int, only_alive: bool = True
    ) -> list[CityDto] | None:
        if only_alive:
            stmt = select(City).where(
                City.planet_id == planet_id and City.development > 0
            )
        else:
            stmt = select(City).where(City.planet_id == planet_id)
        async with self.session() as s:
            result = await s.execute(stmt)
            if result:
                return TypeAdapter(list[CityDto]).validate_python(
                    result.scalars().all()
                )
            return None

    async def get_planets_of_game(self, planet_id: int) -> list[PlanetDto] | None:
        async with self.session() as s:
            result = await s.execute((select(City).where(City.planet_id == planet_id)))
            if result:
                return TypeAdapter(list[CityDto]).validate_python(
                    result.scalars().all()
                )
            return None

    async def _clear_game_cache(self, game_id: int, soft: bool = False) -> None:
        self.get_game(game_id).delete()
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
            self.get_game_by_planet_id(planet_id).delete()

        for city_id in all_cities:
            self.get_game_by_city_id(city_id).delete()

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

    async def get_all_sanctions_on_planet(self, planet_id: int) -> list[SanctionDto]:
        async with self.session() as s:
            sanctions_res = await s.execute(
                (select(Sanction).where(Sanction.planet_to == planet_id))
            )
            sanctions = sanctions_res.scalars().all()
            return TypeAdapter(list[SanctionDto]).validate_python(sanctions)
