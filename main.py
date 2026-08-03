import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher

from app.middlewares.db import DBMiddleware
from app.handlers import (
    ingame_router, main_page_router, lobby_router
)
from database import engine, session_factory
from database.clients import (
    GameClient, InfoClient, UserClient
)
from database.models import ModelBase
from game.config import game_config
from storage import redis_client
from storage.clients import (
    ActionsClient, MessagesClient
)
from storage.config import redis_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

logger = logging.getLogger(__name__)



async def main():
    logger.info('Starting the bot...')
    bot_token = os.environ.get('BOT_TOKEN')

    bot = Bot(token=bot_token)
    dp = Dispatcher()

    logger.info('Creating database tables...')
    async with engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.create_all)

    logger.info('Creating owner user...')
    async with session_factory() as session, session.begin():
        await UserClient().make_new_user_if_not_exists(
            session,
            int(os.environ.get('OWNER')),
            True
        )

    logger.info('Setting up dispatcher')
    middleware = DBMiddleware(
        psql_user_client=UserClient(),
        psql_game_client=GameClient(),
        psql_info_client=InfoClient(),
        session_factory=session_factory,
        redis_actions_client=ActionsClient(
            redis_client, redis_config.EXPIRE_KEY_SECONDS, game_config
        ),
        redis_messages_client=MessagesClient(
            redis_client, redis_config.EXPIRE_KEY_SECONDS
        ),
    )
    dp.update.outer_middleware(middleware)
    dp.include_routers(
        main_page_router,
        lobby_router,
        ingame_router
    )

    logger.info('Starting polling...')
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Working was interrupted.")
