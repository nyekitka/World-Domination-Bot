from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.clients import (
    GameClient,
    UserClient,
)
from storage.clients import (
    ActionsClient,
    MessagesClient
)


class AppMiddleware(BaseMiddleware):
    def __init__(
        self,
        psql_user_client: UserClient,
        psql_game_client: GameClient,
        redis_actions_client: ActionsClient,
        redis_messages_client: MessagesClient,
    ):
        self.user_client = psql_user_client
        self.game_client = psql_game_client
        self.actions_client = redis_actions_client
        self.messages_client = redis_messages_client
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        data['user_client'] = self.user_client
        data['game_client'] = self.game_client
        data['actions_client'] = self.actions_client
        data['messages_client'] = self.messages_client
        
        result = await handler(event, data)
        return result
