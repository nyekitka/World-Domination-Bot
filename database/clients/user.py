import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.base_client import DatabaseClient
from database.models import Admin, Game, Planet, Player
from database.schemas import AdminDto, FailureReason, GameStatus, PlayerDto, UserDto

logger = logging.getLogger(__name__)


class UserClient(DatabaseClient):
    @DatabaseClient.set_transaction
    async def make_new_user_if_not_exists(
        self, s: AsyncSession, tg_id: int, is_admin: bool
    ) -> UserDto:
        user: Player | Admin | None = None
        if is_admin:
            user = await s.get(Admin, tg_id)
            if user:
                return AdminDto.model_validate(user)
        else:
            user = await s.get(Player, tg_id)
            if user:
                return PlayerDto.model_validate(user)

        logger.info("Creating new user with tg_id=%s and is_admin=%s", tg_id, is_admin)

        if is_admin:
            user = Admin(tg_id=tg_id)
        else:
            user = Player(tg_id=tg_id)

        s.add(user)
        if is_admin:
            return AdminDto.model_validate(user)

        return PlayerDto.model_validate(user)

    @DatabaseClient.set_transaction
    async def make_new_user(
        self, s: AsyncSession, tg_id: int, is_admin: bool
    ) -> UserDto:
        if is_admin:
            user = Admin(tg_id=tg_id)
        else:
            user = Player(tg_id=tg_id)

        s.add(user)
        if is_admin:
            return AdminDto.model_validate(user)

        return PlayerDto.model_validate(user)

    @DatabaseClient.get_transaction
    async def get_user(self, s: AsyncSession, tg_id: int) -> UserDto | None:
        user = await s.get(Player, tg_id)
        if user:
            return PlayerDto.model_validate(user)
        user = await s.get(Admin, tg_id)
        if user:
            return AdminDto.model_validate(user)

        return user

    @DatabaseClient.set_transaction
    async def join_user(
        self, s: AsyncSession, user_id: int, game_id: int
    ) -> FailureReason:
        user = await s.get(Player, user_id)
        if user:
            return await self._join_player(s, user, game_id)
        user = await s.get(Admin, user_id)
        if user:
            return await self._join_admin(user, game_id)

        return FailureReason.OBJECT_NOT_FOUND

    async def _join_player(
        self, s: AsyncSession, player: Player, game_id: int
    ) -> FailureReason:
        if player.game_id:
            return FailureReason.ALREADY_IN_GAME

        game = await self.get_game(game_id)
        if not game:
            return FailureReason.OBJECT_NOT_FOUND

        if game.status == GameStatus.ENDED:
            return FailureReason.GAME_ENDED

        planet = await s.execute(
            (select(Planet).where(Planet.owner_id == player.tg_id))
        )
        if planet.all():
            player.game_id = game_id
            await s.commit()
            return FailureReason.SUCCESS

        free_planets = await s.execute(
            select(Planet).where(Planet.game_id == game_id, Planet.owner_id is None)
        )
        planet = free_planets.scalars().first()
        if not planet:
            return FailureReason.GAME_IS_FULL

        planet.owner_id = player.tg_id
        player.game_id = game_id

        return FailureReason.SUCCESS

    async def _join_admin(self, admin: Admin, game_id: int) -> FailureReason:
        if admin.game_id:
            return FailureReason.ALREADY_IN_GAME

        game = await self.get_game(game_id)
        if not game:
            return FailureReason.OBJECT_NOT_FOUND

        admin.game_id = game_id

        return FailureReason.SUCCESS

    @DatabaseClient.set_transaction
    async def kick_user(self, s: AsyncSession, user_id: int) -> FailureReason:
        user = await s.get(Player, user_id)
        if user:
            return await self._kick_player(s, user)
        user = await s.get(Admin, user_id)
        if user:
            return await self._kick_admin(s, user)

        return FailureReason.OBJECT_NOT_FOUND

    async def _kick_player(self, s: AsyncSession, player: Player) -> FailureReason:
        if player.game_id is None:
            return FailureReason.NOT_IN_GAME

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

        return FailureReason.SUCCESS

    async def _kick_admin(self, s: AsyncSession, admin: Admin) -> FailureReason:
        if admin.game_id is None:
            return FailureReason.NOT_IN_GAME

        admin.game_id = None

        return FailureReason.SUCCESS
