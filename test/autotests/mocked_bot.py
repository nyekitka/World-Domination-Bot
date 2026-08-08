from collections import deque
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.methods.base import Response, TelegramType
from aiogram.types import UNSET_PARSE_MODE, User
import pytest


class MockedSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.responses: dict[type[TelegramMethod[TelegramType]], Response[TelegramType]] = dict()
        self.requests: deque[TelegramMethod[TelegramType]] = deque()
        self.closed = True

    def get_request(self) -> TelegramMethod[TelegramType]:
        return self.requests.pop()

    async def close(self):
        self.closed = True

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = UNSET_PARSE_MODE,
    ) -> TelegramType:
        self.closed = False
        self.requests.append(method)
        response = self.responses.get(type(method), None)
        if response is None:
            raise ValueError(f'No response for type {type(method)}')
        self.check_response(
            bot=bot,
            method=method,
            status_code=response.error_code,
            content=response.model_dump_json(),
        )
        return response.result  # type: ignore

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:  # pragma: no cover
        yield b''

    def add_response_for(
        self,
        method: type[TelegramMethod[TelegramType]],
        result: Any,
    ):
        self.responses[method] = Response[method.__returning__](  # type: ignore
            ok=True,
            result=result,
            error_code=200,
        )



class MockedBot(Bot):
    if TYPE_CHECKING:
        session: MockedSession

    def __init__(self, **kwargs):
        super().__init__(
            kwargs.pop('token', '42:TEST'), session=MockedSession(), **kwargs
        )
        self._me = User(
            id=self.id,
            is_bot=True,
            first_name='FirstName',
            last_name='LastName',
            username='tbot',
            language_code='uk-UA',
        )

    def add_result_for(
        self,
        method: type[TelegramMethod[TelegramType]],
        result: Any,
    ) -> Response[TelegramType]:
        self.session.add_response_for(method, result)
        return self.session.responses[method]

    def get_request(self) -> TelegramMethod[TelegramType]:
        return self.session.get_request()

    def assert_method_called(
        self,
        method: type[TelegramMethod[TelegramType]],
        **kwargs,
    ):
        for request in self.session.requests:
            if isinstance(request, method):
                for key, value in kwargs.items():
                    if not (
                        hasattr(request, key)
                        and getattr(request, key) == value
                    ):
                        break
                else:
                    return
        pytest.fail((
            f'Telegram method {method} with kwargs={kwargs} is not found'
            f'\nPresent methods: {self.session.requests}'
        ))

    def assert_method_not_called(
        self,
        method: type[TelegramMethod[TelegramType]],
        **kwargs,
    ):
        for request in self.session.requests:
            if isinstance(request, method):
                for key, value in kwargs.items():
                    if not (
                        hasattr(request, key)
                        and getattr(request, key) == value
                    ):
                        break
                else:
                    pytest.fail(f'Telegram method {method} with kwargs={kwargs} is found')
