import logging
import traceback
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import bot_config
from database.clients import (
    GameClient,
    InfoClient,
    UserClient,
)
from storage.clients import (
    ActionsClient,
    MessagesClient,
)

logger = logging.getLogger(__name__)


class DBMiddleware(BaseMiddleware):
    def __init__(
        self,
        psql_user_client: UserClient,
        psql_game_client: GameClient,
        psql_info_client: InfoClient,
        session_factory: async_sessionmaker[AsyncSession],
        redis_actions_client: ActionsClient,
        redis_messages_client: MessagesClient,
    ):
        self.user_client = psql_user_client
        self.game_client = psql_game_client
        self.info_client = psql_info_client
        self.session_factory = session_factory
        self.actions_client = redis_actions_client
        self.messages_client = redis_messages_client
        self.owner_id = int(bot_config.OWNER)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data['user_client'] = self.user_client
        data['game_client'] = self.game_client
        data['actions_client'] = self.actions_client
        data['messages_client'] = self.messages_client
        data['info_client'] = self.info_client
        data['owner_id'] = self.owner_id

        async with self.session_factory() as session:
            data['session'] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e: # noqa: BLE001
                await session.rollback()
                logger.info(
                    'Error occured while handling an event: %s\nTraceback: %s',
                    e,
                    traceback.format_exc(),
                )
