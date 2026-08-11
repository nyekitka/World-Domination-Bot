import os
from collections.abc import Awaitable, Callable
from inspect import iscoroutinefunction

from asgiref.sync import markcoroutinefunction
from django.http import HttpRequest, HttpResponse, JsonResponse

from app.config import bot_config
from web_app.stats.auth import verify_telegram_init_data


class VerifierMiddleware:
    async_capable = True
    sync_capable = False

    def __init__(self, get_response: Callable[[HttpRequest], Awaitable[HttpResponse]]):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    async def __call__(self, request: HttpRequest):
        if not request.path.startswith('/api/'):
            return await self.get_response(request)

        auth_header = request.headers.get('Authorization', '')
        init_data = (
            auth_header.replace('tma ', '')
            if auth_header.startswith('tma ')
            else request.GET.get('_tgData')
        )

        if not init_data:
            return JsonResponse({'error': 'Forbidden'}, status=403)

        tg_data = verify_telegram_init_data(
            init_data, bot_config.TOKEN
        )

        if not tg_data:
            return JsonResponse({'error': 'Forbidden'}, status=403)

        request.telegram_user = tg_data.get('user')
        return await self.get_response(request)
