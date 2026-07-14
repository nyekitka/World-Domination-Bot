from collections import Counter
import logging

from async_lru import alru_cache
from sqlalchemy import insert, not_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database.base_client import DatabaseClient
from database.models import Admin, City, Game, Order, Planet, Player, RoundInfo, Sanction
from database.schemas import AdminDto, CityData, CityDto, GameData, GameDto, GameStatus, OrderDto, PlanetData, PlanetDto, PlayerDto, RoundInfoDto, SanctionDto
from game.config import game_config
from game.schemas import FailureReason, OrderInfo, OrderType
from presets.pack import Pack
from pydantic import TypeAdapter

from database.config import database_config


logger = logging.getLogger(__name__)


class GameClient(DatabaseClient):
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

        await self._clear_game_cache(s, game_id, True)
    
    async def get_all_active_players(
        self, s: AsyncSession, game_id: int
    ) -> list[PlayerDto]:
        result = await s.execute(
            select(Player)
            .where(Player.game_id == game_id)
        )
        players = result.scalars().all()
        return TypeAdapter(list[PlayerDto]).validate_python(players)
    
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

    async def build_shield_for_cities(self, s: AsyncSession, *city_ids: int) -> None:
        if len(city_ids) == 0:
            return
        stmt = update(City).where(City.id.in_(city_ids)).values(is_shielded=True)
        await s.execute(stmt)


    async def develop_cities(self, s: AsyncSession, *city_ids: int) -> None:
        if len(city_ids) == 0:
            return
        stmt = (
            update(City)
            .where(City.id.in_(city_ids))
            .values(
                {City.development: City.development + game_config.DEVELOPMENT_BOOST}
            )
        )
        await s.execute(stmt)


    async def invent_for_planets(self, s: AsyncSession, *planet_ids: int) -> None:
        if len(planet_ids) == 0:
            return
        stmt = update(Planet).where(Planet.id.in_(planet_ids)).values(is_invented=True)
        await s.execute(stmt)


    async def create_meteorites(self, s: AsyncSession, planet_id: int, n: int) -> None:
        if n == 0:
            return
        planet = await s.get(Planet, planet_id)
        planet.meteorites += n


    async def attack_cities(
        self, s: AsyncSession, *city_ids: int
    ) -> None:
        if len(city_ids) == 0:
            return
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


    async def eco_boost(
        self, s: AsyncSession,
        game_id: int,
        times: int = 1
    ) -> None:
        if times == 0:
            return
        stmt = (
            update(Game)
            .where(Game.id == game_id)
            .values({Game.ecorate: Game.ecorate + game_config.ECO_BOOST_RATE * times})
        )
        await s.execute(stmt)


    async def send_sanctions(
        self, s: AsyncSession, sanctions: list[SanctionDto]
    ) -> None:
        if not sanctions:
            return

        stmt_add_orders = insert(Sanction).values(
            TypeAdapter(list[SanctionDto]).dump_python(sanctions)
        )
        await s.execute(stmt_add_orders)


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
    

    async def end_current_round(
        self,
        s: AsyncSession,
        game_id: int,
        orders: dict[int, OrderInfo],
    ) -> FailureReason:
        await self._clear_game_cache(s, game_id)

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
            await self.create_meteorites(s, planet_id, orders[planet_id].get(OrderType.CREATE, 0))
            num_eco_boosts += int(orders[planet_id].get(OrderType.ECO, 0))
            orders_by_action[OrderType.SANCTIONS].extend([
                SanctionDto(
                    planet_from=planet_id,
                    planet_to=other_planet_id,
                    num_round=game.round,
                )
                for other_planet_id in orders[planet_id].get(OrderType.SANCTIONS, [])
            ])
            if orders[planet_id].get(OrderType.INVENT, False):
                orders_by_action[OrderType.INVENT].append(planet_id)
            for action in (OrderType.ATTACK, OrderType.DEVELOP, OrderType.SHIELD):
                orders_by_action[action].extend(
                    orders[planet_id].get(action, [])
                )
                

        for action, objs in orders_by_action.items():
            match action:
                case OrderType.DEVELOP:
                    await self.develop_cities(s, *objs)
                case OrderType.ATTACK:
                    await self.attack_cities(s, *objs)
                case OrderType.SHIELD:
                    await self.build_shield_for_cities(s, *objs)
                case OrderType.INVENT:
                    await self.invent_for_planets(s, *objs)
                case OrderType.SANCTIONS:
                    await self.send_sanctions(s, objs)

        await self.eco_boost(s, game_id, num_eco_boosts)

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


    async def save_round_info(self, s: AsyncSession, game_id: int) -> FailureReason:
        game = await s.get(Game, game_id)
        if game is None:
            return FailureReason.OBJECT_NOT_FOUND

        planets = await self.get_planets_of_game(s, game_id)
        planets_data = []

        for planet in planets:
            cities = await self.get_cities_of_planet(s, planet.id, False, False)
            cities_data = [
                CityData(name=city.name, development=city.development)
                for city in cities
            ]
            planets_data.append(
                PlanetData(
                    name=planet.name,
                    development=planet.development,
                    cities_data=cities_data
                )
            )
        s.add(RoundInfo(
            game_id=game_id,
            round=game.round,
            info=GameData(
                planets_data=planets_data,
                eco_rate=game.ecorate
            ).model_dump()
        ))

    async def get_round_info(self, s: AsyncSession, game_id: int, round: int) -> RoundInfoDto | None:
        round_info = await s.get(RoundInfo, {'game_id': game_id, 'round': round})
        if round_info is None:
            return None

        return RoundInfoDto.model_validate(round_info)


    async def get_all_planets_and_cities(
        self, s: AsyncSession, game_id: int
    ) -> dict[int, tuple[PlanetDto, list[CityDto]]]:
        planets_result = await s.execute(
            select(Planet)
            .where(Planet.game_id == game_id)
            .options(
                selectinload(Planet.cities),
                joinedload(Planet.game)
            )
        )
        planets = planets_result.scalars().all()
        result = dict()
        for planet in planets:
            planet_dto = PlanetDto.model_validate(planet)
            cities_dto = TypeAdapter(list[CityDto]).validate_python(planet.cities)
            result[planet_dto.id] = (planet_dto, cities_dto)

        return result


    async def start_new_round(self, s: AsyncSession, initiator_id: int) -> FailureReason:
        admin = await s.get(Admin, initiator_id)
        if admin is None:
            return FailureReason.OBJECT_NOT_FOUND
        
        if admin.game_id is None:
            return FailureReason.STARTING_GAME_WITHOUT_BEING_IN
        
        game = await s.get(Game, admin.game_id)
        if game.status not in (GameStatus.WAITING, GameStatus.MEETING):
            return FailureReason.CANNOT_START_ROUND

        planets = await self.get_planets_of_game(s, game.id)

        if not all(map(lambda pl: pl.owner_id is not None, planets)):
            return FailureReason.NOT_ENOUGH_PLAYERS

        if game.status == GameStatus.MEETING:
            for planet in planets:
                income = await self._planet_income(
                    s, planet.id, game.ecorate, len(planets)
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


    @DatabaseClient.get_transaction
    async def get_sanctioned_planets(
        self, s: AsyncSession, planet_id: int
    ) -> list[PlanetDto]:
        """
        Returns all planets that were sanctioned in previous round.
        """
        num_round = (await s.execute(
            select(Game)
            .join(Planet, Game.id == Planet.game_id)
            .where(Planet.id == planet_id)
        )).scalar_one().round
        if num_round == 1:
            return []
        sanctioned_planets_result = await s.execute(
            select(Planet)
            .join(Sanction, Sanction.planet_to == Planet.id)
            .where(
                Sanction.planet_from == planet_id,
                Sanction.num_round == num_round - 1
            )
        )
        sanction_planets = sanctioned_planets_result.scalars().all()
        return TypeAdapter(list[PlanetDto]).validate_python(sanction_planets)
