from collections.abc import Awaitable, Callable
from inspect import iscoroutinefunction

from asgiref.sync import markcoroutinefunction
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import HttpRequest, HttpResponse

from app.config import bot_config
from web_app.app.settings import django_settings


def unsign_auth_token(token: str | None) -> int | None:
    if token is None:
        return None

    signer = TimestampSigner(key=bot_config.TOKEN)

    try:
        user_id = signer.unsign(token, max_age=django_settings.EXPIRE_LINK_SECONDS)
        return int(user_id)
    except (BadSignature, SignatureExpired):
        return None


def sign_user_id(user_id: int) -> str:
    signer = TimestampSigner(key=bot_config.TOKEN)
    return signer.sign(str(user_id))


class VerifierMiddleware:
    async_capable = True
    sync_capable = False

    def __init__(self, get_response: Callable[[HttpRequest], Awaitable[HttpResponse]]):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    async def __call__(self, request: HttpRequest):
        if request.path == '/health':
            return await self.get_response(request)

        token = request.GET.get('auth_token')
        request.user_id = unsign_auth_token(token)

        return await self.get_response(request)
