import logging

from async_lru import alru_cache
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from database.base_client import DatabaseClient
from database.models import Admin, City, Game, Planet, Player
from database.schemas import AdminDto, GameDto, GameStatus, PlanetDto, PlayerDto
from presets.pack import Pack
from pydantic import TypeAdapter

from database.config import database_config

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
    async def create_game(self, s: AsyncSession, admin_id: int, pack: Pack) -> GameDto:
        game = Game()
        s.add(game)
        await s.flush()
        for _planet in pack.planets:
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
    async def get_number_of_planets(
        self, s: AsyncSession, game_id: int
    ) -> int:
        results = await s.execute(
            select(Planet)
            .where(Planet.game_id == game_id)
        )
        return len(results.scalars().all())
    
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
