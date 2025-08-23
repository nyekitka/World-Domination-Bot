import logging

from sqlalchemy import select, update
from database.base_client import DatabaseClient
from database.models import Admin, Game, Planet, Player
from database.schemas import FailureReason, GameStatus, UserDto

logger = logging.getLogger(__name__)


class UserClient(DatabaseClient):
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

    def _clear_user_cache(self, tg_id: int) -> None:
        self.get_user(tg_id).delete()

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
