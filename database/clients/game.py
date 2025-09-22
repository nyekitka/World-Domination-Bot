import logging

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from database.base_client import DatabaseClient
from database.models import Admin, City, Game, Planet, Player
from database.schemas import GameDto, GameStatus
from presets.pack import Pack

logger = logging.getLogger(__name__)


class GameClient(DatabaseClient):
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
