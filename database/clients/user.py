import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.base_client import DatabaseClient
from database.models import Admin, Game, Planet, Player
from database.schemas import AdminDto, GameStatus, PlayerDto, UserDto
from game.schemas import FailureReason

logger = logging.getLogger(__name__)


class UserClient(DatabaseClient):
    async def make_new_user_if_not_exists(
        self, s: AsyncSession, tg_id: int, is_admin: bool
    ) -> UserDto:
        user: Player | Admin | None = None

        user = await s.get(Player, tg_id)
        if user:
            return PlayerDto.model_validate(user)
        else:
            user = await s.get(Admin, tg_id)
            if user:
                return AdminDto.model_validate(user)

        logger.info('Creating new user with tg_id=%s and is_admin=%s', tg_id, is_admin)

        if is_admin:
            user = Admin(tg_id=tg_id)
        else:
            user = Player(tg_id=tg_id)

        s.add(user)
        if is_admin:
            return AdminDto.model_validate(user)

        return PlayerDto.model_validate(user)

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

    async def get_user(self, s: AsyncSession, tg_id: int) -> UserDto | None:
        user = await s.get(Player, tg_id)
        if user:
            return PlayerDto.model_validate(user)
        user = await s.get(Admin, tg_id)
        if user:
            return AdminDto.model_validate(user)

        return user

    async def is_user_admin(self, s: AsyncSession, tg_id: int) -> bool:
        user = await s.get(Admin, tg_id)
        return user is not None

    async def join_user(
        self, s: AsyncSession, user_id: int, game_id: int
    ) -> FailureReason:
        user = await s.get(Player, user_id)
        if user:
            return await self._join_player(s, user, game_id)
        user = await s.get(Admin, user_id)
        if user:
            return await self._join_admin(s, user, game_id)

        return FailureReason.OBJECT_NOT_FOUND

    async def _join_player(
        self, s: AsyncSession, player: Player, game_id: int
    ) -> FailureReason:
        if player.game_id:
            return FailureReason.ALREADY_IN_GAME

        game = await self.get_game(s, game_id)
        if not game:
            return FailureReason.OBJECT_NOT_FOUND

        if game.status == GameStatus.ENDED:
            return FailureReason.GAME_ENDED

        planet = await s.execute(
            select(Planet).where(Planet.owner_id == player.tg_id)
        )
        if planet.all():
            player.game_id = game_id
            return FailureReason.SUCCESS

        free_planets = await s.execute(
            select(Planet).where(Planet.game_id == game_id, Planet.owner_id == None)
        )
        planet = free_planets.scalars().first()
        if not planet:
            return FailureReason.GAME_IS_FULL

        planet.owner_id = player.tg_id
        player.game_id = game_id

        return FailureReason.SUCCESS

    async def _join_admin(
        self, s: AsyncSession, admin: Admin, game_id: int
    ) -> FailureReason:
        if admin.game_id:
            return FailureReason.ALREADY_IN_GAME

        game = await self.get_game(s, game_id)
        if not game:
            return FailureReason.OBJECT_NOT_FOUND

        admin.game_id = game_id

        return FailureReason.SUCCESS

    async def kick_user(self, s: AsyncSession, user_id: int) -> FailureReason:
        user = await s.get(Player, user_id)
        if user:
            return await self._kick_player(s, user)
        user = await s.get(Admin, user_id)
        if user:
            return self._kick_admin(user)

        return FailureReason.OBJECT_NOT_FOUND

    async def _kick_player(self, s: AsyncSession, player: Player) -> FailureReason:
        if player.game_id is None:
            return FailureReason.NOT_IN_GAME

        game = await s.get(Game, player.game_id)
        if game.status == GameStatus.WAITING:
            await s.execute(
                
                    update(Planet)
                    .where(Planet.owner_id == player.tg_id)
                    .values(owner_id=None)
                
            )
        player.game_id = None

        return FailureReason.SUCCESS

    def _kick_admin(self, admin: Admin) -> FailureReason:
        if admin.game_id is None:
            return FailureReason.NOT_IN_GAME

        admin.game_id = None

        return FailureReason.SUCCESS

    async def promote_to_admin(self, s: AsyncSession, player_id: int) -> FailureReason:
        player = await s.get(Player, player_id)
        if player is None:
            return FailureReason.OBJECT_NOT_FOUND

        if player.game_id:
            game = await s.get(Game, player.game_id)
            if game.status != GameStatus.WAITING:
                return FailureReason.WAIT_TILL_GAME_ENDS

            await self._kick_player(s, player)

        admin = Admin(tg_id=player.tg_id)
        s.add(admin)
        await s.delete(player)

        return FailureReason.SUCCESS

    async def fire_admin(self, s: AsyncSession, admin_id: int) -> FailureReason:
        admin = await s.get(Admin, admin_id)
        if admin is None:
            return FailureReason.OBJECT_NOT_FOUND

        self._kick_admin(admin)

        player = Player(tg_id=admin.tg_id)
        s.add(player)
        await s.delete(admin)

        return FailureReason.SUCCESS
