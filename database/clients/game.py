from collections import Counter
import logging

from async_lru import alru_cache
from sqlalchemy import insert, not_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.base_client import DatabaseClient
from database.models import Admin, City, Game, Order, Planet, Player, Sanction
from database.schemas import AdminDto, GameDto, GameStatus, OrderDto, PlanetDto, PlayerDto, SanctionDto
from game.config import game_config
from game.schemas import FailureReason, OrderType
from presets.pack import Pack
from pydantic import TypeAdapter

from database.config import database_config
from storage.schemas import OrderInfo

logger = logging.getLogger(__name__)


class GameClient(DatabaseClient):
    @DatabaseClient.get_transaction
    async def get_all_games(
        self, s: AsyncSession, every: bool = False
    ) -> list[GameDto]:
        if every:
            stmt = select(Game)
        else:
            stmt = (
                select(Game)
                .where(Game.status != GameStatus.ENDED)
            )
        result = await s.execute(stmt)
        games = result.scalars().all()
        return TypeAdapter(list[GameDto]).validate_python(games)

    @DatabaseClient.set_transaction
    async def create_game(
        self, s: AsyncSession,
        admin_id: int, pack: Pack,
        number_of_planets: int = -1
    ) -> GameDto:
        if number_of_planets == -1:
            number_of_planets = len(pack.planets)
        if number_of_planets > len(pack.planets):
            number_of_planets = len(pack.planets)
        game = Game(num_planets=number_of_planets)
        s.add(game)
        await s.flush()
        for i, _planet in enumerate(pack.planets):
            if i == number_of_planets:
                break
            planet = Planet(name=_planet.name, game_id=game.id)
            s.add(planet)
            await s.flush()
            for _city in _planet.cities:
                city = City(name=_city.name, planet_id=planet.id)
                s.add(city)
            await s.flush()

        stmt = update(Admin).where(Admin.tg_id == admin_id).values(game_id=game.id)
        await s.execute(stmt)

        return GameDto.model_validate(game)

    @DatabaseClient.set_transaction
    async def end_game(self, s: AsyncSession, game_id: int) -> None:
        await s.execute(
            (update(Player).where(Player.game_id == game_id).values(game_id=None))
        )
        await s.execute(
            (update(Admin).where(Admin.game_id == game_id).values(game_id=None))
        )
        await s.execute(
            (update(Game).where(Game.id == game_id).values(status=GameStatus.ENDED))
        )

        await self._clear_game_cache(game_id, True)
    
    @DatabaseClient.get_transaction
    async def get_all_active_players(
        self, s: AsyncSession, game_id: int
    ) -> list[PlayerDto]:
        result = await s.execute(
            select(Player)
            .where(Player.game_id == game_id)
        )
        players = result.scalars().all()
        return TypeAdapter(list[PlayerDto]).validate_python(players)
    
    @DatabaseClient.get_transaction
    async def get_all_active_admins(
        self, s: AsyncSession, game_id: int
    ) -> list[PlayerDto]:
        result = await s.execute(
            select(Admin)
            .where(Admin.game_id == game_id)
        )
        admins = result.scalars().all()
        return TypeAdapter(list[AdminDto]).validate_python(admins)

    
    @alru_cache(ttl=database_config.EXPIRE_CACHE)
    @DatabaseClient.get_transaction
    async def get_all_planets_in_game(
        self,
        s: AsyncSession,
        game_id: int,
        load_development: bool = True
    ) -> list[PlanetDto]:
        options = ()
        if load_development:
            options = (
                selectinload(Planet.cities),
                joinedload(Planet.game)
            )
        results = await s.execute(
            select(Planet)
            .options(*options)
            .where(Planet.game_id == game_id)
        )
        return TypeAdapter(list[PlanetDto]).validate_python(
            results.scalars().all()
        )

    @DatabaseClient.set_transaction
    async def build_shield_for_cities(self, s: AsyncSession, *city_ids: int) -> None:
        stmt = update(City).where(City.id.in_(city_ids)).values(is_shielded=True)
        await s.execute(stmt)


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
    async def invent_for_planets(self, s: AsyncSession, *planet_ids: int) -> None:
        stmt = update(Planet).where(Planet.id.in_(planet_ids)).values(is_invented=True)
        await s.execute(stmt)


    @DatabaseClient.set_transaction
    async def create_meteorites(self, s: AsyncSession, planet_id: int, n: int) -> None:
        planet = await s.get(Planet, planet_id)
        planet.meteorites += n


    @DatabaseClient.set_transaction
    async def attack_cities(
        self, s: AsyncSession, *city_ids: int
    ) -> None:
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
    async def eco_boost(
        self, s: AsyncSession,
        game_id: int,
        times: int = 1
    ) -> None:
        stmt = (
            update(Game)
            .where(Game.id == game_id)
            .values({Game.ecorate: Game.ecorate + game_config.ECO_BOOST_RATE * times})
        )
        if times:
            await s.execute(stmt)


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
        self, s: AsyncSession,
        planet_from_id: int,
        planet_to_id: int,
        amount: int
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
    async def spend(
        self, s: AsyncSession,
        planet_id: int,
        money: int,
        meteorites: int,
    ) -> FailureReason:
        planet = await s.get(Planet, planet_id)
        if planet is None:
            return FailureReason.OBJECT_NOT_FOUND
        
        if planet.balance < money:
            return FailureReason.NOT_ENOUGH_MONEY
        
        if planet.meteorites < meteorites:
            return FailureReason.NOT_ENOUGH_METEORITES
        
        planet.meteorites -= meteorites
        planet.balance -= money
        await s.commit()
    

    @DatabaseClient.set_transaction
    async def end_current_round(
        self,
        s: AsyncSession,
        game_id: int,
        orders: dict[int, OrderInfo],
    ) -> FailureReason:
        await self._clear_game_cache(game_id)

        game = await s.get(Game, game_id)
        if not game:
            return FailureReason.OBJECT_NOT_FOUND

        if game.status != GameStatus.ROUND:
            return FailureReason.ROUND_IS_NOT_GOING

        orders_by_action = {
            action: []
            for action in OrderType
            if action not in [OrderType.ECO, OrderType.CREATE]
        }
        num_eco_boosts = 0

        for planet_id in orders:
            await self.create_meteorites(planet_id, orders[planet_id].created)
            num_eco_boosts += int(orders[planet_id].eco_boost)
            orders_by_action[OrderType.SANCTIONS].extend([
                SanctionDto(
                    planet_from=planet_id,
                    planet_to=other_planet_id,
                    num_round=game.round,
                )
                for other_planet_id in orders[planet_id].sanctions
            ])
            orders_by_action[OrderType.ATTACK].extend([
                OrderDto(
                    action=OrderType.ATTACK,
                    planet_id=planet_id,
                    argument=city_id,
                    round=game.round
                )
                for city_id in orders[planet_id].attacked
            ])
            if orders[planet_id].is_invented:
                orders_by_action[OrderType.INVENT].append(planet_id)
            orders_by_action[OrderType.DEVELOP].extend([
                OrderDto(
                    action=OrderType.DEVELOP,
                    planet_id=planet_id,
                    argument=city_id,
                    round=game.round
                )
                for city_id in orders[planet_id].developed
            ])
            orders_by_action[OrderType.SHIELD].extend([
                OrderDto(
                    action=OrderType.SHIELD,
                    planet_id=planet_id,
                    argument=city_id,
                    round=game.round
                )
                for city_id in orders[planet_id].shielded    
            ])

        for action, orders_list in orders_by_action.items():
            match action:
                case OrderType.DEVELOP:
                    await self.develop_cities(*orders_list)
                case OrderType.ATTACK:
                    await self.attack_cities(*orders_list)
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
    async def start_new_round(self, s: AsyncSession, initiator_id: int) -> FailureReason:
        admin = await s.get(Admin, initiator_id)
        if admin is None:
            return FailureReason.OBJECT_NOT_FOUND
        
        if admin.game_id is None:
            return FailureReason.STARTING_GAME_WITHOUT_BEING_IN
        
        game = await s.get(Game, admin.game_id)
        if game.status not in (GameStatus.WAITING, GameStatus.MEETING):
            return FailureReason.CANNOT_START_ROUND

        planets = await self.get_planets_of_game(game.id)

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
        game.round = 1 if game.round is None else game.round + 1
        await s.commit()
        return FailureReason.SUCCESS
