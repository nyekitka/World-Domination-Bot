from collections import Counter
import logging

from pydantic import TypeAdapter
import ring
from sqlalchemy import delete, select, update, insert
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.sql.functions import coalesce

from database.config import database_config, game_config
from database.models import (
    Admin,
    City,
    Game,
    Negotiation,
    Order,
    Planet,
    Player,
    ModelBase,
    Sanction,
)
from database.schemas import (
    CityDto,
    FailureReason,
    GameDto,
    GameStatus,
    OrderDto,
    OrderType,
    PlanetDto,
    SanctionDto,
    UserDto,
)
from presets.pack import Pack

logger = logging.getLogger(__name__)


class DatabaseClient:
    def __init__(self, engine: AsyncEngine):
        self.session = async_sessionmaker(engine)
        ModelBase.metadata.create_all(engine)

    async def make_new_user_if_not_exists(self, tg_id: int, is_admin: bool) -> UserDto:
        async with self.session() as s:
            user: Player | Admin | None = None
            if is_admin:
                user = await s.get(Admin, tg_id)
            else:
                user = await s.get(Player, tg_id)
            if user:
                return UserDto.model_validate(user)

            logger.info(
                "Creating new user with tg_id=%s and is_admin=%s", tg_id, is_admin
            )

            if is_admin:
                user = Admin(tg_id=tg_id)
            else:
                user = Player(tg_id=tg_id)

            s.add(user)
            await s.commit()
            return UserDto.model_validate(user)

    async def make_new_user(self, tg_id: int, is_admin: bool) -> UserDto:
        async with self.session() as s:
            if is_admin:
                user = Admin(tg_id=tg_id)
            else:
                user = Player(tg_id=tg_id)

            s.add(user)
            await s.commit()
            return UserDto.model_validate(user)

    async def get_user(self, tg_id: int) -> UserDto | None:
        async with self.session() as s:
            user = await s.get(Player, tg_id=tg_id)
            if user:
                return UserDto.model_validate(user)
            user = await s.get(Admin, tg_id=tg_id)
            return UserDto.model_validate(user)

    @ring.lru(expire=database_config.EXPIRE_CACHE)
    async def get_game(self, game_id: int) -> GameDto | None:
        async with self.session() as s:
            game = await s.get(Game, game_id=game_id)
            if game:
                return GameDto.model_validate(game)

            return None

    @ring.lru(expire=database_config.EXPIRE_CACHE)
    async def get_game_by_planet_id(self, planet_id: int) -> GameDto | None:
        stmt = (
            select(Game).join(Game.id == Planet.game_id).where(Planet.id == planet_id)
        )
        async with self.session() as s:
            res = await s.execute(stmt)
            game = res.scalars().first()
            if game:
                return GameDto.model_validate(game)

            return None

    @ring.lru(expire=database_config.EXPIRE_CACHE)
    async def get_game_by_city_id(self, city_id: int) -> GameDto | None:
        stmt = (
            select(Game)
            .join(Game.id == Planet.game_id)
            .join(City.planet_id == Planet.id)
            .where(City.id == city_id)
        )
        async with self.session() as s:
            res = await s.execute(stmt)
            game = res.scalars().first()
            if game:
                return GameDto.model_validate(game)

            return None

    async def kick_user_from_game(self, tg_id: int) -> None:
        async with self.session() as s:
            stmt_player = (
                update(Player).where(Player.tg_id == tg_id).values(game_id=None)
            )
            stmt_admin = update(Admin).where(Admin.tg_id == tg_id).values(game_id=None)
            await s.execute(stmt_admin)
            await s.execute(stmt_player)
            await s.commit()

    async def create_game(self, admin_id: int, pack: Pack) -> GameDto:
        async with self.session() as s:
            game = Game()
            s.add(game)
            for _planet in pack.planets:
                planet = Planet(name=_planet.name, game_id=game.id)
                s.add(planet)
                for _city in _planet.cities:
                    city = City(name=_city.name, planet_id=planet.id)
                    s.add(city)

            await s.commit()
            stmt = update(Admin).where(Admin.tg_id == admin_id).values(game_id=game.id)
            await s.execute(stmt)
            await s.commit()
            return GameDto.model_validate(game)

    async def order_shield_for_city(self, city_id: int) -> FailureReason:
        async with self.session() as s:
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
                await s.commit()
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
            await s.commit()
            return FailureReason.SUCCESS

    async def build_shield_for_cities(self, *city_ids: int) -> None:
        stmt = update(City).where(City.id.in_(city_ids)).values(is_shielded=True)
        async with self.session() as s:
            await s.execute(stmt)
            await s.commit()

    async def get_city(self, city_id: int) -> CityDto | None:
        async with self.session() as s:
            city = await s.get(City, city_id)
            if city:
                return CityDto.model_validate(city)
            return None

    async def order_development(self, city_id: int) -> FailureReason:
        async with self.session() as s:
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
                await s.commit()
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
            await s.commit()
            return FailureReason.SUCCESS

    async def develop_cities(self, *city_ids: int) -> None:
        async with self.session() as s:
            stmt = (
                update(City)
                .where(City.id.in_(city_ids))
                .values(
                    {City.development: City.development + game_config.DEVELOPMENT_BOOST}
                )
            )
            await s.execute(stmt)
            await s.commit()

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
                return TypeAdapter[list[CityDto]].validate_python(
                    result.scalars().all()
                )
            return None

    async def get_planets_of_game(self, planet_id: int) -> list[PlanetDto] | None:
        async with self.session() as s:
            result = await s.execute((select(City).where(City.planet_id == planet_id)))
            if result:
                return TypeAdapter[list[CityDto]].validate_python(
                    result.scalars().all()
                )
            return None

    async def accept_diplomatist(
        self, planet_from: int, planet_to: int
    ) -> FailureReason:
        stmt_negotiations = select(Negotiation).where(
            Negotiation.planet_to == planet_to
            or (
                Negotiation.planet_from == planet_to
                and Negotiation.planet_to == planet_from
            )
        )
        async with self.session() as s:
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

            these_negotiation = Negotiation(
                planet_from=planet_from, planet_to=planet_to
            )

            s.add(these_negotiation)
            await s.commit()
            return FailureReason.SUCCESS

    async def end_negotiations(self, planet_from: int, planet_to: int) -> None:
        async with self.session() as s:
            stmt = delete(Negotiation).where(
                Negotiation.planet_from == planet_from
                and Negotiation.planet_to == planet_to
            )
            await s.execute(stmt)
            await s.commit()

    async def order_invent(self, planet_id: int) -> FailureReason:
        async with self.session() as s:
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
                },
            )
            if order:
                planet.balance += game_config.INVENTION_COST
                await s.delete(order)
            elif (
                planet.balance >= game_config.INVENTION_COST and not planet.is_invented
            ):
                planet.balance -= game_config.INVENTION_COST
                order = Order(
                    planet_id=planet_id, action=OrderType.INVENT, round=game.round
                )
                s.add(order)
            elif planet.is_invented:
                return FailureReason.ALREADY_INVENTED
            else:
                return FailureReason.NOT_ENOUGH_MONEY
            await s.commit()
            return FailureReason.SUCCESS

    async def invent_for_planets(self, *planet_ids: int) -> None:
        stmt = update(Planet).where(Planet.id.in_(planet_ids)).values(is_invented=True)
        async with self.session() as s:
            await s.execute(stmt)
            await s.commit()

    async def is_invent_in_order(self, planet_id: int) -> bool | None:
        async with self.session() as s:
            game = await self.get_game_by_planet_id(planet_id)
            if not game:
                return None

            order = await s.get(
                Order,
                {
                    "action": OrderType.INVENT,
                    "planet_id": planet_id,
                    "round": game.round,
                },
            )

            return bool(order)

    async def order_create_meteorites(self, planet_id: int, n: int) -> FailureReason:
        async with self.session() as s:
            planet = await s.get(Planet, planet_id)
            if not planet:
                return FailureReason.OBJECT_NOT_FOUND

            if not planet.is_invented:
                return FailureReason.IS_NOT_INVENTED

            game = await s.get(Game, planet.game_id)
            order = await s.get(
                Order,
                {
                    "planet_id": planet_id,
                    "round": game.round,
                    "action": OrderType.CREATE,
                },
            )
            ordered = order.argument if order else 0
            diff = n - ordered

            if planet.balance < diff:
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
            await s.commit()

    async def create_meteorites(self, planet_id: int, n: int) -> None:
        async with self.session() as s:
            planet = await s.get(Planet, planet_id)
            planet.meteorites += n
            await s.commit()

    async def order_attack_city(self, planet_id: int, city_id: int) -> FailureReason:
        async with self.session() as s:
            planet = await s.get(Planet, planet_id)
            city = await s.get(City, city_id)
            if not planet or not city:
                return FailureReason.OBJECT_NOT_FOUND

            if planet.is_invented:
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
                await s.commit()
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
            await s.commit()
            return FailureReason.SUCCESS

    async def attack_cities(self, orders: list[OrderDto]) -> None:
        city_ids = [order.argument for order in orders]
        counter = Counter(city_ids)
        once_attacked = set()
        twice_attacked = set()
        for city_id in counter:
            if counter[city_id] == 1:
                once_attacked.add(city_id)
            else:
                twice_attacked.add(city_id)

        stmt_for_twice = (
            update(City)
            .where(City.id.in_(twice_attacked))
            .values(development=0, is_shielded=False)
        )
        stmt_for_once_shielded = (
            update(City)
            .where(City.id.in_(once_attacked) and City.is_shielded)
            .values(is_shielded=False)
        )
        stmt_for_once_not_shielded = (
            update(City)
            .where(City.id.in_(twice_attacked) and not City.is_shielded)
            .values(development=0)
        )

        async with self.session() as s:
            await s.execute(stmt_for_twice)
            await s.execute(stmt_for_once_shielded)
            await s.execute(stmt_for_once_not_shielded)
            await s.commit()

    async def order_eco_boost(self, planet_id: int) -> FailureReason:
        async with self.session() as s:
            planet = await s.get(Planet, planet_id)
            game = await s.get(Game, planet.game_id)
            order = await s.get(
                Order,
                {"planet_id": planet_id, "round": game.round, "action": OrderType.ECO},
            )
            if order:
                planet.balance += 1
                await s.delete(order)
                await s.commit()
                return FailureReason.SUCCESS

            if not planet.balance:
                return FailureReason.NOT_ENOUGH_METEORITES

            planet.balance -= 1
            order = Order(planet_id=planet_id, round=game.round, action=OrderType.ECO)
            s.add(order)

            await s.commit()
            return FailureReason.SUCCESS

    async def eco_boost(self, game_id: int, times: int = 1) -> None:
        stmt = (
            update(Game)
            .where(Game.id == game_id)
            .values({Game.ecorate: Game.ecorate + game_config.ECO_BOOST_RATE * times})
        )
        async with self.session() as s:
            await s.execute(stmt)
            await s.commit()

    async def order_sanctions(self, planet_from: int, planet_to: int) -> None:
        async with self.session() as s:
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
            await s.commit()

    async def send_sanctions(self, sanctions: list[SanctionDto]) -> None:
        async with self.session() as s:
            if not sanctions:
                return

            stmt_add_orders = insert(Order).values(sanctions)
            await s.execute(stmt_add_orders)
            await s.commit()

    async def get_all_sanctions_on_planet(self, planet_id: int) -> list[SanctionDto]:
        async with self.session() as s:
            sanctions_res = await s.execute(
                (select(Sanction).where(Sanction.planet_to == planet_id))
            )
            sanctions = sanctions_res.scalars().all()
            return TypeAdapter(list[SanctionDto]).validate_python(sanctions)

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

    def _clear_user_cache(self, tg_id: int) -> None:
        self.get_user(tg_id).delete()

    async def end_current_round(self, game_id: int) -> FailureReason:
        self._clear_game_cache()

        async with self.session() as s:
            game = await s.get(Game, game_id)
            if not game:
                return FailureReason.OBJECT_NOT_FOUND

            if game.status != GameStatus.ROUND:
                return FailureReason.ROUND_IS_NOT_GOING

            stmt_orders = (
                select(Order)
                .join(Planet, Planet.id == Order.planet_id)
                .where(Planet.game_id == game_id and Order.round == game.round)
            )
            res = await s.execute(stmt_orders)
            orders = res.scalars().all()

        orders_by_action = {
            action: set()
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
                    orders_by_action[order.action].add(
                        SanctionDto(
                            planet_from=order.planet_id, planet_to=order.argument
                        )
                    )
                case _:
                    orders_by_action[order.action].add(order.argument)

        for action, orders_set in orders_by_action.items():
            match action:
                case OrderType.DEVELOP:
                    await self.develop_cities(*orders_set)
                case OrderType.ATTACK:
                    await self.attack_cities(*orders_set)
                case OrderType.SHIELD:
                    await self.build_shield_for_cities(*orders_set)
                case OrderType.INVENT:
                    await self.invent_for_planets(*orders_set)
                case OrderType.SANCTIONS:
                    await self.send_sanctions(list(orders))

        async with self.session() as s:
            await s.execute(
                (
                    update(Game)
                    .where(Game.id == game_id)
                    .values(
                        {
                            Game.ecorate: min(
                                Game.ecorate
                                + num_eco_boosts * game_config.ECO_BOOST_RATE,
                                100,
                            ),
                            Game.status: GameStatus.MEETING,
                        }
                    )
                )
            )
            await s.commit()

    async def end_game(self, game_id: int) -> None:
        async with self.session() as s:
            await s.execute(
                (update(Player).where(Player.game_id == game_id).values(game_id=None))
            )
            await s.execute(
                (update(Admin).where(Admin.game_id == game_id).values(game_id=None))
            )
            await s.execute(
                (update(Game).where(Game.id == game_id).values(status=GameStatus.ENDED))
            )
            await s.commit()
        self._clear_game_cache(game_id, True)

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

    async def start_new_round(self, game_id: int) -> FailureReason:
        async with self.session() as s:
            game = await s.get(Game, game_id)
            if game.status not in (GameStatus.WAITING, GameStatus.MEETING):
                return FailureReason.CANNOT_START_ROUND

            planets = await self.get_planets_of_game(game_id)

            if all(map(lambda pl: pl.owner_id is not None, planets)):
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

            await s.commit()

    async def transfer(
        self, planet_from_id: int, planet_to_id: int, amount: int
    ) -> FailureReason:
        if amount <= 0:
            return FailureReason.NEGATIVE_AMOUNT

        async with self.session() as s:
            planet_from = await s.get(Planet, planet_from_id)
            if planet_from.balance < amount:
                return FailureReason.NOT_ENOUGH_MONEY

            planet_to = await s.get(Planet, planet_to_id)
            if planet_from.game_id != planet_to.game_id:
                return FailureReason.DIFFERENT_GAMES

            planet_from.balance -= amount
            planet_to.balance += amount
            await s.commit()

    async def join_user(self, user_id: int, game_id: int) -> FailureReason:
        async with self.session() as s:
            user = await s.get(Player, user_id)
            if user:
                return self._join_player(user, game_id)
            user = await s.get(Admin, user_id)
            if user:
                return self._join_admin(user, game_id)

        return FailureReason.OBJECT_NOT_FOUND

    async def _join_player(self, player: Player, game_id: int) -> FailureReason:
        if player.game_id:
            return FailureReason.ALREADY_IN_GAME

        game = await self.get_game(game_id)
        if not game:
            return FailureReason.OBJECT_NOT_FOUND

        if game.status == GameStatus.ENDED:
            return FailureReason.GAME_ENDED

        async with self.session() as s:
            planet = await s.execute(
                (select(Planet).where(Planet.owner_id == player.tg_id))
            )
            if planet.all():
                player.game_id = game_id
                await s.commit()
                return FailureReason.SUCCESS

            free_planets = await s.execute(
                (
                    select(Planet).where(
                        Planet.game_id == game_id and Planet.owner_id is None
                    )
                )
            )
            planet = free_planets.scalars().first()
            if not planet:
                return FailureReason.GAME_IS_FULL

            planet.owner_id = player.tg_id
            player.game_id = game_id
            await s.commit()

        return FailureReason.SUCCESS

    async def _join_admin(self, admin: Admin, game_id: int) -> FailureReason:
        if admin.game_id:
            return FailureReason.ALREADY_IN_GAME

        game = await self.get_game(game_id)
        if not game:
            return FailureReason.OBJECT_NOT_FOUND

        async with self.session() as s:
            admin.game_id = game_id
            await s.commit()

        return FailureReason.SUCCESS

    async def kick_user(self, user_id: int) -> FailureReason:
        async with self.session() as s:
            user = await s.get(Player, user_id)
            if user:
                return self._kick_player(user)
            user = await s.get(Admin, user_id)
            if user:
                return self._kick_admin(user)

        return FailureReason.OBJECT_NOT_FOUND

    async def _kick_player(self, player: Player) -> FailureReason:
        if player.game_id is None:
            return FailureReason.NOT_IN_GAME

        async with self.session() as s:
            game = await s.get(Game, player.game_id)
            if game.status == GameStatus.WAITING:
                await s.execute(
                    (
                        update(Planet)
                        .where(Planet.owner_id == player.tg_id)
                        .values(owner_id=None)
                    )
                )
            player.game_id = None
            await s.commit()

        return FailureReason.SUCCESS

    async def _kick_admin(self, admin: Admin) -> FailureReason:
        if admin.game_id is None:
            return FailureReason.NOT_IN_GAME

        async with self.session() as s:
            admin.game_id = None
            await s.commit()

        return FailureReason.SUCCESS
