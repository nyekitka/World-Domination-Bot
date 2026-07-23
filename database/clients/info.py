import logging

from async_lru import alru_cache
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.base_client import DatabaseClient
from database.config import database_config
from database.models import City, Game, Order, Planet
from database.schemas import CityDto, PlanetDto
from game.config import game_config
from game.schemas import OrderInfo, OrderType

logger = logging.getLogger(__name__)


class InfoClient(DatabaseClient):
    @DatabaseClient.get_transaction
    async def get_all_orders_in_game(
        self, s: AsyncSession,
        game_id: int,
    ) -> list[dict[int, OrderInfo]]:
        """
        Returns all orders of players in every round.
        i-th item in list -- orders in (i + 1)-th round
        represented as dictionary where key is planet id and value
        is OrderInfo
        """

        orders = (await s.execute(
            select(Order)
            .join(Planet, Planet.id == Order.planet_id)
            .join(Game, Game.id == Planet.game_id)
            .where(Game.id == game_id)
        )).scalars().all()
        all_planets = (await s.execute(
            select(Planet)
            .where(Planet.game_id == game_id)
        )).scalars().all()
        max_round = game_config.ROUND_NUM
        all_orders: list[dict[int, OrderInfo]] = [
            {
                planet.id : dict()
                for planet in all_planets
            } for _ in range(max_round)
        ]

        for order in orders:
            if order.action in (OrderType.INVENT, OrderType.ECO):
                all_orders[order.round][order.planet_id][order.action] = True
            elif order.action == OrderType.CREATE:
                all_orders[order.round][order.planet_id][OrderType.CREATE] = order.argument
            else:
                all_orders[order.round][order.planet_id].setdefault(order.action, []).append(order.argument)
        
        return all_orders
