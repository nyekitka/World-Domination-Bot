import logging

from sqlalchemy import update
from database.base_client import DatabaseClient
from database.models import Admin, City, Game, Planet, Player
from database.schemas import GameDto, GameStatus
from presets.pack import Pack

logger = logging.getLogger(__name__)


class GameClient(DatabaseClient):
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
