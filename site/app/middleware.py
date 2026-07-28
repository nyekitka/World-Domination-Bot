from typing import Awaitable, Callable

from django.http import HttpRequest, HttpResponse

from database import session_factory


class DBClientMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], Awaitable[HttpResponse]]):
        self.get_response = get_response
        self.async_capable = True
        self.sync_capable = False

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        async with session_factory() as session:
            request.db_session = session

            response = await self.get_response(request)

            if 200 <= response.status_code < 400:
                await session.commit()
            else:
                await session.rollback()
        return response
