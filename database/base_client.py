import logging

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.alru_cache import alru_cache
from database.config import database_config
from database.models import (
    City,
    Game,
    Planet,
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
    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_game(self, s: AsyncSession, game_id: int) -> GameDto | None:
        game = await s.get(Game, game_id)
        if game:
            return GameDto.model_validate(game)

        return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
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

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_city(
        self, s: AsyncSession, city_id: int, load_rate: bool = False
    ) -> CityDto | None:
        options = ()
        if load_rate:
            options = (joinedload(City.planet).joinedload(Planet.game),)
        city = (
            await s.execute(select(City).options(*options).where(City.id == city_id))
        ).scalar_one_or_none()
        if city:
            return CityDto.model_validate(city)
        return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_planet(
        self,
        s: AsyncSession,
        planet_id: int,
        load_rate_of_life: bool = True,
    ) -> PlanetDto | None:
        options = ()
        if load_rate_of_life:
            options = (selectinload(Planet.cities), joinedload(Planet.game))
        planet = (
            await s.execute(
                select(Planet).options(*options).where(Planet.id == planet_id)
            )
        ).scalar_one_or_none()
        if planet:
            return PlanetDto.model_validate(planet)
        return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_planet_by_city_id(
        self, s: AsyncSession, city_id: int
    ) -> PlanetDto | None:
        planet_res = await s.execute(
            select(Planet)
            .join(City, City.planet_id == Planet.id)
            .where(City.id == city_id)
        )
        planet = planet_res.scalar_one_or_none()
        if planet:
            return PlanetDto.model_validate(planet)
        return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_player_planet(
        self,
        s: AsyncSession,
        player_id: int,
        game_id: int,
        load_rate_of_life: bool = True,
    ) -> PlanetDto | None:
        options = ()
        if load_rate_of_life:
            options = (selectinload(Planet.cities), joinedload(Planet.game))
        result = await s.execute(
            select(Planet)
            .options(*options)
            .where(Planet.owner_id == player_id, Planet.game_id == game_id)
        )
        planet = result.scalar_one_or_none()
        if planet:
            return PlanetDto.model_validate(planet)
        return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_cities_of_planet(
        self,
        s: AsyncSession,
        planet_id: int,
        only_alive: bool = True,
        with_rates: bool = True,
    ) -> list[CityDto] | None:
        options = ()
        if with_rates:
            options = (joinedload(City.planet).joinedload(Planet.game),)
        if only_alive:
            filters = (City.planet_id == planet_id, City.development > 0)
        else:
            filters = (City.planet_id == planet_id,)

        stmt = select(City).options(*options).where(*filters)
        result = await s.execute(stmt)
        if result:
            return TypeAdapter(list[CityDto]).validate_python(result.scalars().all())
        return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_planets_of_game(
        self,
        s: AsyncSession,
        game_id: int,
        load_rate_of_life: bool = True,
    ) -> list[PlanetDto] | None:
        options = ()
        if load_rate_of_life:
            options = (selectinload(Planet.cities), joinedload(Planet.game))
        planets = (
            (
                await s.execute(
                    select(Planet).options(*options).where(Planet.game_id == game_id)
                )
            )
            .scalars()
            .all()
        )

        if planets:
            return TypeAdapter(list[PlanetDto]).validate_python(planets)
        return None

    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    async def get_all_planets_and_cities(
        self, s: AsyncSession, game_id: int
    ) -> dict[int, tuple[PlanetDto, list[CityDto]]]:
        planets_result = await s.execute(
            select(Planet)
            .where(Planet.game_id == game_id)
            .options(
                selectinload(Planet.cities)
                .joinedload(City.planet)
                .joinedload(Planet.game),
                joinedload(Planet.game),
            )
        )
        planets = planets_result.scalars().all()
        result = {}
        for planet in planets:
            planet_dto = PlanetDto.model_validate(planet)
            cities_dto = TypeAdapter(list[CityDto]).validate_python(planet.cities)
            result[planet_dto.id] = (planet_dto, cities_dto)

        return result


    def _clear_game_cache(self) -> None:
        self.get_game.cache_clear()
        self.get_game_by_planet_id.cache_clear()
        self.get_game_by_city_id.cache_clear()
        self.get_city.cache_clear()
        self.get_planet.cache_clear()
        self.get_planet_by_city_id.cache_clear()
        self.get_player_planet.cache_clear()
        self.get_cities_of_planet.cache_clear()
        self.get_planets_of_game.cache_clear()
        self.get_all_planets_and_cities.cache_clear()


    async def get_all_sanctions_on_planet(
        self, s: AsyncSession, planet_id: int
    ) -> list[SanctionDto]:
        sanctions_res = await s.execute(
            select(Sanction).where(Sanction.planet_to == planet_id)
        )
        sanctions = sanctions_res.scalars().all()
        return TypeAdapter(list[SanctionDto]).validate_python(sanctions)
