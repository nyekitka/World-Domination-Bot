from aiogram import BaseMiddleware

from features.config import feature_config
from messages.renderer import MessageRenderer


class I18nMiddleware(BaseMiddleware):
    def __init__(self, default_language: str = 'ru'):
        self.default_language = default_language
        self.message_renderers = {
            'ru': MessageRenderer('ru'),
            'en': MessageRenderer('en'),
        }

    async def __call__(self, handler, event, data):
        if not feature_config.I18N:
            language = self.default_language
            data['renderer'] = self.message_renderers[language]
            return await handler(event, data)
        
        user = data.get('event_from_user')
        language = self.default_language
        if user and hasattr(user, 'language_code') and user.language_code:
            language = user.language_code.split('-')[0]
            if language not in ('ru', 'en'):
                language = self.default_language
        data['renderer'] = self.message_renderers[language]
        return await handler(event, data)
