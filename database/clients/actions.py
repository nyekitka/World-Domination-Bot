from collections import Counter
import logging

from pydantic import TypeAdapter
from sqlalchemy import and_, delete, insert, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.base_client import DatabaseClient
from database.models import City, Game, Negotiation, Order, Planet, Sanction
from database.schemas import FailureReason, GameStatus, OrderDto, OrderType, SanctionDto
from sqlalchemy.sql.functions import coalesce

from database.config import game_config

logger = logging.getLogger(__name__)


class ActionsClient(DatabaseClient):
    @DatabaseClient.set_transaction
    async def order_shield_for_city(
        self, s: AsyncSession, city_id: int
    ) -> FailureReason:
        city = await s.get(City, city_id)
        if not city:
            return FailureReason.OBJECT_NOT_FOUND

        planet = await s.get(Planet, city.planet_id)
        game = await s.get(Game, planet.game_id)
        order = await s.get(
            Order,
            {
                "planet_id": planet.id,
                "round": game.round,
                "action": OrderType.SHIELD,
                "argument": city_id,
            },
        )
        if order:
            planet.balance += game_config.SHIELD_COST
            await s.delete(order)
            return FailureReason.SUCCESS

        if planet.balance < game_config.SHIELD_COST:
            return FailureReason.NOT_ENOUGH_MONEY

        planet.balance -= game_config.SHIELD_COST
        order = Order(
            planet_id=planet.id,
            action=OrderType.SHIELD,
            round=game.round,
            argument=city_id,
        )
        s.add(order)
        return FailureReason.SUCCESS

    @DatabaseClient.set_transaction
    async def build_shield_for_cities(self, s: AsyncSession, *city_ids: int) -> None:
        stmt = update(City).where(City.id.in_(city_ids)).values(is_shielded=True)
        await s.execute(stmt)

    @DatabaseClient.set_transaction
    async def order_development(self, s: AsyncSession, city_id: int) -> FailureReason:
        city = await s.get(City, city_id)
        if not city:
            return FailureReason.OBJECT_NOT_FOUND

        planet = await s.get(Planet, city.planet_id)
        game = await s.get(Game, planet.game_id)
        order = await s.get(
            Order,
            {
                "planet_id": planet.id,
                "action": OrderType.DEVELOP,
                "round": game.round,
                "argument": city_id,
            },
        )
        if order:
            planet.balance += game_config.DEVELOPMENT_COST
            await s.delete(order)
            return FailureReason.SUCCESS

        if planet.balance < game_config.DEVELOPMENT_COST:
            return FailureReason.NOT_ENOUGH_MONEY

        planet.balance -= game_config.DEVELOPMENT_COST
        order = Order(
            planet_id=planet.id,
            action=OrderType.DEVELOP,
            round=game.round,
            argument=city_id,
        )
        s.add(order)
        return FailureReason.SUCCESS

    @DatabaseClient.set_transaction
    async def develop_cities(self, s: AsyncSession, *city_ids: int) -> None:
        stmt = (
            update(City)
            .where(City.id.in_(city_ids))
            .values(
                {City.development: City.development + game_config.DEVELOPMENT_BOOST}
            )
        )
        await s.execute(stmt)

    @DatabaseClient.set_transaction
    async def accept_diplomatist(
        self, s: AsyncSession, planet_from: int, planet_to: int
    ) -> FailureReason:
        stmt_negotiations = select(Negotiation).where(
            or_(
                Negotiation.planet_to == planet_to,
                and_(
                    Negotiation.planet_from == planet_to,
                    Negotiation.planet_to == planet_from,
                ),
            )
        )
        logger.debug(stmt_negotiations)
        negotiations = await s.execute(stmt_negotiations)
        row = negotiations.scalars().first()
        if row:
            if row.planet_to == planet_to and row.planet_from == planet_from:
                return FailureReason.ALREADY_NEGOTIATING
            elif row.planet_to == planet_to:
                return FailureReason.PLANET_IS_BUSY

            return FailureReason.BILATERAL_NEGOTIATIONS

        game = await self.get_game_by_planet_id(planet_from)
        if game.status != GameStatus.ROUND:
            return FailureReason.UNTIMELY_NEGOTIATIONS

        these_negotiation = Negotiation(planet_from=planet_from, planet_to=planet_to)

        s.add(these_negotiation)
        return FailureReason.SUCCESS

    @DatabaseClient.set_transaction
    async def end_negotiations(
        self, s: AsyncSession, planet_from: int, planet_to: int
    ) -> None:
        stmt = delete(Negotiation).where(
            Negotiation.planet_from == planet_from
            and Negotiation.planet_to == planet_to
        )
        await s.execute(stmt)

    @DatabaseClient.set_transaction
    async def order_invent(self, s: AsyncSession, planet_id: int) -> FailureReason:
        planet = await s.get(Planet, planet_id)
        if not planet:
            return FailureReason.OBJECT_NOT_FOUND

        game = await self.get_game(planet.game_id)
        order = await s.get(
            Order,
            {
                "planet_id": planet_id,
                "action": OrderType.INVENT,
                "round": game.round,
                "argument": 0,
            },
        )
        if order:
            planet.balance += game_config.INVENTION_COST
            await s.delete(order)
        elif planet.balance >= game_config.INVENTION_COST and not planet.is_invented:
            planet.balance -= game_config.INVENTION_COST
            order = Order(
                planet_id=planet_id, action=OrderType.INVENT, round=game.round
            )
            s.add(order)
        elif planet.is_invented:
            return FailureReason.ALREADY_INVENTED
        else:
            return FailureReason.NOT_ENOUGH_MONEY
        return FailureReason.SUCCESS

    @DatabaseClient.set_transaction
    async def invent_for_planets(self, s: AsyncSession, *planet_ids: int) -> None:
        stmt = update(Planet).where(Planet.id.in_(planet_ids)).values(is_invented=True)
        await s.execute(stmt)

    @DatabaseClient.get_transaction
    async def is_invent_in_order(self, s: AsyncSession, planet_id: int) -> bool | None:
        game = await self.get_game_by_planet_id(planet_id)
        if not game:
            return None

        order = await s.get(
            Order,
            {
                "action": OrderType.INVENT,
                "planet_id": planet_id,
                "round": game.round,
                "argument": 0,
            },
        )

        return bool(order)

    @DatabaseClient.set_transaction
    async def order_create_meteorites(
        self, s: AsyncSession, planet_id: int, n: int
    ) -> FailureReason:
        planet = await s.get(Planet, planet_id)
        if not planet:
            return FailureReason.OBJECT_NOT_FOUND

        if not planet.is_invented:
            return FailureReason.IS_NOT_INVENTED

        game = await s.get(Game, planet.game_id)
        order = await s.execute(
            select(Order).where(
                Order.action == OrderType.CREATE,
                Order.planet_id == planet_id,
                Order.round == game.round,
            )
        )
        order = order.scalars().first()
        ordered = order.argument if order else 0
        diff = n - ordered

        if planet.balance < diff * game_config.CREATE_COST:
            return FailureReason.NOT_ENOUGH_MONEY

        planet.balance -= diff * game_config.CREATE_COST
        if ordered:
            order.argument = n
        else:
            order = Order(
                planet_id=planet_id,
                round=game.round,
                action=OrderType.CREATE,
                argument=n,
            )
            s.add(order)

        return FailureReason.SUCCESS

    @DatabaseClient.set_transaction
    async def create_meteorites(self, s: AsyncSession, planet_id: int, n: int) -> None:
        planet = await s.get(Planet, planet_id)
        planet.meteorites += n

    @DatabaseClient.set_transaction
    async def order_attack_city(
        self, s: AsyncSession, planet_id: int, city_id: int
    ) -> FailureReason:
        planet = await s.get(Planet, planet_id)
        city = await s.get(City, city_id)
        if not planet or not city:
            return FailureReason.OBJECT_NOT_FOUND

        if not planet.is_invented:
            return FailureReason.IS_NOT_INVENTED

        if city.planet_id == planet_id:
            return FailureReason.SELF_ATTACK

        game = await s.get(Game, planet.game_id)

        order = await s.get(
            Order,
            {
                "planet_id": planet_id,
                "action": OrderType.ATTACK,
                "round": game.round,
                "argument": city_id,
            },
        )

        if order:
            planet.meteorites += 1
            await s.delete(order)
            return FailureReason.SUCCESS

        if not planet.meteorites:
            return FailureReason.NOT_ENOUGH_METEORITES

        planet.meteorites -= 1
        order = Order(
            planet_id=planet_id,
            action=OrderType.ATTACK,
            round=game.round,
            argument=city_id,
        )
        s.add(order)
        return FailureReason.SUCCESS

    @DatabaseClient.set_transaction
    async def attack_cities(self, s: AsyncSession, orders: list[OrderDto]) -> None:
        city_ids = [order.argument for order in orders]
        counter = Counter(city_ids)
        once_attacked = set()

        twice_attacked = set()
        for city_id in counter:
            if counter[city_id] == 1:
                once_attacked.add(city_id)
            else:
                twice_attacked.add(city_id)
        logger.debug(once_attacked)
        logger.debug(twice_attacked)

        stmt_for_twice = (
            update(City)
            .where(City.id.in_(twice_attacked))
            .values(development=0, is_shielded=False)
        )
        logger.debug(stmt_for_twice)
        stmt_for_once_shielded = (
            update(City)
            .where(City.id.in_(once_attacked), City.is_shielded)
            .values(is_shielded=False)
        )
        logger.debug(stmt_for_once_shielded)
        stmt_for_once_not_shielded = (
            update(City)
            .where(City.id.in_(once_attacked), not_(City.is_shielded))
            .values(development=0)
        )
        logger.debug(stmt_for_once_not_shielded)

        if twice_attacked:
            await s.execute(stmt_for_twice)

        if once_attacked:
            await s.execute(stmt_for_once_not_shielded)
            await s.execute(stmt_for_once_shielded)

    @DatabaseClient.set_transaction
    async def order_eco_boost(self, s: AsyncSession, planet_id: int) -> FailureReason:
        planet = await s.get(Planet, planet_id)
        game = await s.get(Game, planet.game_id)
        order = await s.get(
            Order,
            {
                "planet_id": planet_id,
                "round": game.round,
                "action": OrderType.ECO,
                "argument": 0,
            },
        )
        if order:
            planet.meteorites += 1
            await s.delete(order)
            return FailureReason.SUCCESS

        if not planet.meteorites:
            return FailureReason.NOT_ENOUGH_METEORITES

        planet.meteorites -= 1
        order = Order(planet_id=planet_id, round=game.round, action=OrderType.ECO)
        s.add(order)

        return FailureReason.SUCCESS

    @DatabaseClient.set_transaction
    async def eco_boost(self, s: AsyncSession, game_id: int, times: int = 1) -> None:
        stmt = (
            update(Game)
            .where(Game.id == game_id)
            .values({Game.ecorate: Game.ecorate + game_config.ECO_BOOST_RATE * times})
        )
        if times:
            await s.execute(stmt)

    @DatabaseClient.set_transaction
    async def order_sanctions(
        self, s: AsyncSession, planet_from: int, planet_to: int
    ) -> None:
        game = await self.get_game_by_planet_id(planet_from)
        order = await s.get(
            Order,
            {
                "planet_id": planet_from,
                "action": OrderType.SANCTIONS,
                "round": game.round,
                "argument": planet_to,
            },
        )
        if order:
            await s.delete(order)

        else:
            order = Order(
                planet_id=planet_from,
                action=OrderType.SANCTIONS,
                round=game.round,
                argument=planet_to,
            )
            s.add(order)

    @DatabaseClient.set_transaction
    async def send_sanctions(
        self, s: AsyncSession, sanctions: list[SanctionDto]
    ) -> None:
        if not sanctions:
            return

        stmt_add_orders = insert(Sanction).values(
            TypeAdapter(list[SanctionDto]).dump_python(sanctions)
        )
        await s.execute(stmt_add_orders)

    @DatabaseClient.set_transaction
    async def transfer(
        self, s: AsyncSession, planet_from_id: int, planet_to_id: int, amount: int
    ) -> FailureReason:
        if amount <= 0:
            return FailureReason.NEGATIVE_AMOUNT

        planet_from = await s.get(Planet, planet_from_id)
        if planet_from.balance < amount:
            return FailureReason.NOT_ENOUGH_MONEY

        planet_to = await s.get(Planet, planet_to_id)
        if planet_from.game_id != planet_to.game_id:
            return FailureReason.DIFFERENT_GAMES

        planet_from.balance -= amount
        planet_to.balance += amount

        return FailureReason.SUCCESS

    @DatabaseClient.set_transaction
    async def end_current_round(self, s: AsyncSession, game_id: int) -> FailureReason:
        await self._clear_game_cache(game_id)

        game = await s.get(Game, game_id)
        if not game:
            return FailureReason.OBJECT_NOT_FOUND

        if game.status != GameStatus.ROUND:
            return FailureReason.ROUND_IS_NOT_GOING

        stmt_orders = (
            select(Order)
            .join(Planet, Planet.id == Order.planet_id)
            .where(Planet.game_id == game_id, Order.round == game.round)
        )
        res = await s.execute(stmt_orders)
        orders = res.scalars().all()

        orders_by_action = {
            action: []
            for action in OrderType
            if action not in [OrderType.ECO, OrderType.CREATE]
        }
        num_eco_boosts = 0

        for order in orders:
            match order.action:
                case OrderType.CREATE:
                    await self.create_meteorites(order.planet_id, order.argument)
                case OrderType.ECO:
                    num_eco_boosts += 1
                case OrderType.SANCTIONS:
                    orders_by_action[order.action].append(
                        SanctionDto(
                            planet_from=order.planet_id, planet_to=order.argument
                        )
                    )
                case OrderType.ATTACK:
                    orders_by_action[order.action].append(
                        OrderDto.model_validate(order)
                    )
                case OrderType.INVENT:
                    orders_by_action[order.action].append(order.planet_id)
                case _:
                    orders_by_action[order.action].append(order.argument)

        for action, orders_list in orders_by_action.items():
            match action:
                case OrderType.DEVELOP:
                    await self.develop_cities(*orders_list)
                case OrderType.ATTACK:
                    await self.attack_cities(orders_list)
                case OrderType.SHIELD:
                    await self.build_shield_for_cities(*orders_list)
                case OrderType.INVENT:
                    await self.invent_for_planets(*orders_list)
                case OrderType.SANCTIONS:
                    await self.send_sanctions(orders_list)

        await self.eco_boost(game_id, num_eco_boosts)

        await s.execute(
            (
                update(Game)
                .where(Game.id == game_id)
                .values(
                    {
                        Game.status: GameStatus.MEETING,
                    }
                )
            )
        )

    @DatabaseClient.set_transaction
    async def start_new_round(self, s: AsyncSession, game_id: int) -> FailureReason:
        game = await s.get(Game, game_id)
        if game.status not in (GameStatus.WAITING, GameStatus.MEETING):
            return FailureReason.CANNOT_START_ROUND

        planets = await self.get_planets_of_game(game_id)

        if not all(map(lambda pl: pl.owner_id is not None, planets)):
            return FailureReason.NOT_ENOUGH_PLAYERS

        if game.status == GameStatus.MEETING:
            for planet in planets:
                income = await self._planet_income(
                    planet.id, game.ecorate, len(planets)
                )
                await s.execute(
                    (
                        update(Planet)
                        .where(Planet.id == planet.id)
                        .values({Planet.balance: Planet.balance + income})
                    )
                )

        await s.execute(
            (
                update(Game)
                .where(Game.id == game_id)
                .values({Game.round: coalesce(Game.round, 0) + 1})
            )
        )
        return FailureReason.SUCCESS
