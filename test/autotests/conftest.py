import datetime
from random import randint
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import (
    AnswerCallbackQuery,
    DeleteMessage,
    DeleteMessages,
    EditMessageText,
    EditMessageReplyMarkup,
    SendMessage,
    SendRichMessage,
)
from fakeredis import FakeRedis
from sqlalchemy.ext.asyncio import AsyncSession

from database.clients import (
    GameClient,
    InfoClient,
    UserClient,
)

from app.config import bot_config
from app.handlers import main_page_router, lobby_router, ingame_router
from game.config import game_config
from messages.renderer import MessageRenderer
from storage.clients.actions import ActionsClient
from storage.clients.messages import MessagesClient
from test.autotests.mocked_bot import MockedBot


@pytest.fixture()
def test_db_config() -> dict[str, str]:
    return {
        'user': 'postgres',
        'host': 'test-db',
        'port': '5432',
        'name': 'test_db',
        'password': '123',
        'version': '18',
    }


@pytest.fixture()
def user1():
    return types.User(
        id=123456789,
        is_bot=False,
        first_name='Nikita',
        last_name='Klinov',
        username='nyekitka',
    )


@pytest.fixture()
def user2():
    return types.User(
        id=987654321,
        is_bot=False,
        first_name='Pavel',
        last_name='Durove',
        username='du.rove',
    )


@pytest.fixture()
def admin_user():
    return types.User(
        id=214365879,
        is_bot=False,
        first_name='Osama',
        last_name='Bin Laden',
        username='wc_fragrance',
    )


@pytest.fixture()
def owner_user():
    return types.User(
        id=int(bot_config.OWNER),
        is_bot=False,
        username='bibi',
        first_name='Benjamin',
        last_name='Netanyahu',
    )


@pytest.fixture()
def game_client():
    return GameClient()


@pytest.fixture()
def info_client():
    return InfoClient()


@pytest.fixture()
def user_client():
    return UserClient()


@pytest.fixture()
def messages_client():
    return MessagesClient(
        redis_client=FakeRedis(),
        ex=1,
    )


@pytest.fixture()
def actions_client():
    return ActionsClient(
        client=FakeRedis(),
        ex=1,
        game_config=game_config,
    )


@pytest.fixture()
def mock_session():
    return Mock(spec=AsyncSession)


@pytest.fixture()
def mock_bot():
    bot = MockedBot()
    bot.add_result_for(AnswerCallbackQuery, True)
    bot.add_result_for(DeleteMessage, True)
    bot.add_result_for(DeleteMessages, True)
    bot.add_result_for(EditMessageText, True)
    bot.add_result_for(EditMessageReplyMarkup, True)
    mock_message = types.Message(
        message_id=1,
        date=datetime.datetime.now(
            tz=ZoneInfo('Europe/Moscow'),
        ),
        chat=types.Chat(id=1, type='type'),
    )
    bot.add_result_for(SendMessage, mock_message)
    bot.add_result_for(SendRichMessage, mock_message)
    return bot


@pytest.fixture()
def bot_user(mock_bot):
    return types.User(
        id=mock_bot.id,
        is_bot=True,
        first_name='Space Domination Bot',
        username='SpaceDominationBot',
    )


@pytest.fixture()
def chat1():
    return types.Chat(
        id=123456789,
        type='private',
        title='title',
        username='nyekitka',
        first_name='Nikita',
        last_name='Klinov',
    )


@pytest.fixture()
def chat2():
    return types.Chat(
        id=987654321,
        type='private',
        title='title',
        username='du.rove',
        first_name='Pavel',
        last_name='Durove',
    )


@pytest.fixture()
def admin_chat():
    return types.Chat(
        id=214365879,
        type='private',
        title='title',
        username='wc_fragrance',
        first_name='Osama',
        last_name='Bin Laden',
    )


@pytest.fixture()
def owner_chat():
    return types.Chat(
        id=int(bot_config.OWNER),
        type='private',
        title='title',
        username='bibi',
        first_name='Benjamin',
        last_name='Netanyahu',
    )

@pytest.fixture()
def get_message(mock_bot, chat1, user1):
    def wrapper(
        message_text: str | None = None,
        chat: types.Chat = chat1,
        user: types.User = user1,
    ) -> types.Message:
        message = types.Message(
            message_id=randint(1, 1_000_000),
            date=datetime.datetime.now(
                tz=ZoneInfo('Europe/Moscow'),
            ),
            chat=chat,
            from_user=user,
            text=message_text,
        )
        message._bot = mock_bot
        return message
    return wrapper


@pytest.fixture()
def get_call(user1, mock_bot, bot_user, chat1):
    def wrapper(
        user: types.User = user1,
        message_user: types.User = bot_user,
        call_data: str | None = None,
        message_text: str | None = None,
        chat: types.Chat = chat1
    ):
        call = types.CallbackQuery(
            id='1488',
            from_user=user,
            chat_instance='chat_instance',
            message=types.Message(
                message_id=randint(1, 1_000_00),
                chat=chat,
                date=datetime.datetime.now(tz=ZoneInfo('Europe/Moscow')),
                from_user=message_user,
                text=message_text
            ),
            data=call_data,
        )
        call._bot = mock_bot
        return call
    return wrapper


@pytest.fixture()
def get_chat_full_info_for_chat():
    def wrapper(chat: types.Chat) -> types.ChatFullInfo:
        return types.ChatFullInfo(
            id=chat.id,
            type='type',
            accent_color_id=0,
            max_reaction_count=10,
            accepted_gift_types=types.AcceptedGiftTypes(
                unlimited_gifts=False,
                limited_gifts=False,
                unique_gifts=False,
                premium_subscription=False,
                gifts_from_channels=False,
            ),
            username=chat.username,
            first_name=chat.first_name,
            last_name=chat.last_name,
        )
    return wrapper


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture()
def get_fsm_context(storage, mock_bot, chat1):
    def wrapper(
        chat: types.Chat = chat1
    ):
        return FSMContext(
            storage=storage,
            key=StorageKey(
                bot_id=mock_bot.id,
                chat_id=chat.id,
                user_id=chat.id,
            ),
        )
    return wrapper


@pytest.fixture(scope='session')
def dispatcher():
    dp = Dispatcher()
    dp.include_routers(main_page_router, ingame_router, lobby_router)
    return dp


@pytest.fixture()
def get_call_update():
    def wrapper(call: types.CallbackQuery):
        return types.Update(
            update_id=1,
            callback_query=call,
        )
    return wrapper


@pytest.fixture()
def get_message_update():
    def wrapper(message: types.Message):
        return types.Update(
            update_id=1,
            message=message,
        )
    return wrapper


@pytest.fixture()
def renderer():
    return MessageRenderer('ru')
