from collections.abc import Awaitable
from types import TracebackType

from redis import Redis

from storage.clients.base import BaseClient


class _UpdateContextManager:
    def __init__(
        self,
        user_id: int,
        money_key: str,
        exit_handler: Awaitable,
        update_client: UpdateClient,
    ):
        self.user_id = user_id
        self.money_key = money_key
        self.exit_handler = exit_handler
        self.client = update_client

    async def __aenter__(self):
        self.client.increment(self.user_id, self.money_key)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        count_val = self.client.decrement(self.user_id, self.money_key)
        if count_val <= 0:
            await self.exit_handler
        if count_val < 0:
            self.client.delete(self.user_id, self.money_key)


class UpdateClient(BaseClient):
    def __init__(
        self,
        client: Redis,
    ):
        super().__init__(client)

    def __call__(
        self,
        user_id: int,
        money_key: str,
        exit_handler: Awaitable,
    ) -> _UpdateContextManager:
        return _UpdateContextManager(
            user_id, money_key, exit_handler, self
        )
