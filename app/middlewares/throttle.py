from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from cachetools import TTLCache

from features.config import feature_config
from messages.renderer import MessageRenderer


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, throttle: float, cache_maxsize: int):
        self.throttle = throttle
        self.cache = TTLCache(maxsize=cache_maxsize, ttl=throttle)
        self.message_renderers = {
            'ru': MessageRenderer('ru'),
            'en': MessageRenderer('en'),
        }
        self.default_language = 'ru'

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        if event.callback_query is None:
            return await handler(event, data)
        
        user = data.get('event_from_user')
        current_time = datetime.now(
            tz=ZoneInfo('Europe/Moscow'),
        )
        renderer = self.message_renderers[self.default_language]
        if (
            hasattr(user, 'language_code')
            and user.language_code
            and feature_config.I18N
        ):
            language = user.language_code.split('-')[0]
            renderer = self.message_renderers.get(
                language,
                self.default_language
            )

        if user.id in self.cache:
            last_time: datetime = self.cache[user.id]
            if (current_time - last_time).total_seconds() < self.throttle:
                await event.callback_query.answer(
                    renderer.render('too_fast')['text'],
                    show_alert=False,
                )
                return

        self.cache[user.id] = current_time

        return await handler(event, data)
