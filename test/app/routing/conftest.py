import datetime
from collections.abc import Callable
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from aiogram import Dispatcher, Router
from aiogram.types import CallbackQuery, Message, Update

from app.handlers.ingame import ingame_router
from app.handlers.lobby import lobby_router
from app.handlers.main_page import main_page_router


@pytest.fixture(scope='session')
def dispatcher():
    dp = Dispatcher()
    dp.include_routers(main_page_router, ingame_router, lobby_router)
    return dp


@pytest.fixture()
def call_update(message, user, request):
    return Update(
        update_id=1,
        callback_query=CallbackQuery(
            id='id',
            from_user=user,
            chat_instance='chat',
            message=message,
            data=request.param,
        ),
    )


@pytest.fixture()
def message_update(chat, user, request):
    return Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.datetime.now(
                tz=ZoneInfo('Europe/Moscow')
            ),
            chat=chat,
            from_user=user,
            text=request.param,
        ),
    )


@pytest.fixture()
def patch_handler(monkeypatch):
    def _patch(
        router: Router, original_callback: Callable, event_type: str = 'message'
    ) -> AsyncMock:
        handler_mock = AsyncMock()
        observer = getattr(router, event_type)
        for handler_obj in observer.handlers:
            if handler_obj.callback is original_callback:
                monkeypatch.setattr(handler_obj, 'callback', handler_mock)
                return handler_mock
        raise ValueError('Handler is not found')

    return _patch
