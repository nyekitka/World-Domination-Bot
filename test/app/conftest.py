import datetime
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession

from database.clients import (
    GameClient,
    InfoClient,
    UserClient,
)
from game.config import game_config
from storage.clients.actions import ActionsClient
from storage.clients.messages import MessagesClient
from test.app.mocked_bot import MockedBot


@pytest.fixture()
def user_id():
    return 123456789


@pytest.fixture()
def other_user_id():
    return 987654321


@pytest.fixture()
def user(user_id):
    return types.User(id=user_id, is_bot=False, first_name='Nikita', last_name='Klinov')


@pytest.fixture()
def other_user(other_user_id):
    return types.User(
        id=other_user_id, is_bot=False, first_name='Pavel', last_name='Durove'
    )


@pytest.fixture()
def game_id():
    return 1


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
        redis_client=Mock(),
        ex=1,
    )


@pytest.fixture()
def actions_client():
    return ActionsClient(
        client=Mock(),
        ex=1,
        game_config=game_config,
    )


@pytest.fixture()
def mock_session():
    return Mock(spec=AsyncSession)


@pytest.fixture()
def mock_bot():
    return MockedBot()


@pytest.fixture()
def chat():
    return types.Chat(
        id=67,
        type='private',
        title='title',
        username='nyekitka',
        first_name='Nikita',
        last_name='Klinov',
    )


@pytest.fixture()
def other_chat():
    return types.Chat(
        id=67,
        type='private',
        title='title',
        username='durove',
        first_name='Pavel',
        last_name='Durove',
    )


@pytest.fixture()
def message(mock_bot, chat, user, request):
    message_text = request.param if hasattr(request, 'param') else None
    message = types.Message(
        message_id=52,
        date=datetime.datetime.now(
            tz=ZoneInfo('Europe/Moscow'),
        ),
        chat=chat,
        from_user=user,
        text=message_text,
    )
    message._bot = mock_bot
    return message


@pytest.fixture()
def other_message(mock_bot, other_chat, other_user):
    message = types.Message(
        message_id=11,
        date=datetime.datetime.now(
            tz=ZoneInfo('Europe/Moscow'),
        ),
        chat=other_chat,
        from_user=other_user,
    )
    message._bot = mock_bot
    return message


@pytest.fixture()
def call(user, message, mock_bot, request):
    call = types.CallbackQuery(
        id='1488',
        from_user=user,
        chat_instance='chat_instance',
        message=message,
        data=request.param,
    )
    call._bot = mock_bot
    return call


@pytest.fixture()
def chat_full_info(user_id):
    return types.ChatFullInfo(
        id=user_id,
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
        user_name='nyekitka',
        first_name='Nikita',
        last_name='Klinov',
    )


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture()
def fsm_context(storage, mock_bot, chat, user_id):
    return FSMContext(
        storage=storage,
        key=StorageKey(
            bot_id=mock_bot.id,
            chat_id=chat.id,
            user_id=user_id,
        ),
    )


@pytest.fixture(autouse=True)
def mock_answer_call(mocker):
    mocker.patch('aiogram.types.CallbackQuery.answer', new_callable=AsyncMock)
