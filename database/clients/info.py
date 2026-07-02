import logging

from async_lru import alru_cache
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.base_client import DatabaseClient
from database.config import database_config
from database.models import City, Game, Order, Planet
from database.schemas import CityDto, PlanetDto
from game.schemas import OrderType

logger = logging.getLogger(__name__)


class InfoClient(DatabaseClient):
    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    @DatabaseClient.get_transaction
    async def _get_current_round(
        self, s: AsyncSession, planet_id: int
    ) -> int:
        res_game = await s.execute(
            select(Game)
            .join(Planet, Planet.game_id == Game.id)
            .where(Planet.id == planet_id)
        )
        return res_game.scalar_one().round
        
    @DatabaseClient.get_transaction
    async def ordered_shielding(
        self, s: AsyncSession, planet_id: int, round: int | None = None
    ) -> list[CityDto]:
        if not round:
            round = await self._get_current_round(planet_id)
        res_cities = await s.execute(
            select(City)
            .join(Order, Order.argument == City.id)
            .where(
                Order.action == OrderType.SHIELD,
                Order.planet_id == planet_id,
                Order.round == round
            )
        )
        return TypeAdapter(list[CityDto]).validate_python(
            res_cities.scalars().all()
        )
    
    @DatabaseClient.get_transaction
    async def ordered_development(
        self, s: AsyncSession, planet_id: int, round: int | None = None
    ) -> list[CityDto]:
        if not round:
            round = await self._get_current_round(planet_id)
        res_cities = await s.execute(
            select(City)
            .join(Order, Order.argument == City.id)
            .where(
                Order.action == OrderType.DEVELOP,
                Order.planet_id == planet_id,
                Order.round == round
            )
        )
        return TypeAdapter(list[CityDto]).validate_python(
            res_cities.scalars().all()
        )

    @DatabaseClient.get_transaction
    async def is_invent_in_order(
        self, s: AsyncSession, planet_id: int, round: int | None = None
    ) -> bool:
        if not round:
            round = await self._get_current_round(planet_id)
        res_orders = await s.execute(
            select(Order)
            .where(
                Order.round == round,
                Order.action == OrderType.INVENT,
                Order.planet_id == planet_id
            )
        )
        return bool(res_orders.scalars().all())
    
    @DatabaseClient.get_transaction
    async def number_of_ordered_meteorites(
        self, s: AsyncSession, planet_id: int, round: int | None = None
    ) -> int:
        if not round:
            round = await self._get_current_round(planet_id)
        res_orders = await s.execute(
            select(Order)
            .where(
                Order.round == round,
                Order.action == OrderType.CREATE,
                Order.planet_id == planet_id
            )
        )
        order = res_orders.scalar_one_or_none()
        return order.argument if order else 0
    
    @DatabaseClient.get_transaction
    async def ordered_sanctions(
        self, s: AsyncSession, planet_id: int, round: int | None = None
    ) -> list[PlanetDto]:
        if not round:
            round = await self._get_current_round(planet_id)
        res_cities = await s.execute(
            select(Planet)
            .join(Order, Order.argument == Planet.id)
            .where(
                Order.action == OrderType.SANCTIONS,
                Order.planet_id == planet_id,
                Order.round == round
            )
        )
        return TypeAdapter(list[PlanetDto]).validate_python(
            res_cities.scalars().all()
        )
    
    @DatabaseClient.get_transaction
    async def is_planned_eco_boost(
        self, s: AsyncSession, planet_id: int, round: int | None = None
    ) -> bool:
        if not round:
            round = await self._get_current_round(planet_id)
        res_orders = await s.execute(
            select(Order)
            .where(
                Order.round == round,
                Order.action == OrderType.ECO,
                Order.planet_id == planet_id
            )
        )
        return bool(res_orders.scalars().all())
    
    @DatabaseClient.get_transaction
    async def ordered_attacks(
        self, s: AsyncSession, planet_id: int, round: int | None = None
    ) -> dict[int, CityDto]:
        if not round:
            round = await self._get_current_round(planet_id)
        res_cities = await s.execute(
            select(City)
            .join(Order, Order.argument == City.id)
            .where(
                Order.action == OrderType.ATTACK,
                Order.planet_id == planet_id,
                Order.round == round
            )
        )
        cities = TypeAdapter(list[CityDto]).validate_python(
            res_cities.scalars().all()
        )
        attacks = dict()
        for city in cities:
            attacks.get(city.planet_id, []).append(city)
        
        return attacks
