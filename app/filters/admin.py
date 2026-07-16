from typing import Self

from aiogram import types
from aiogram.filters import Filter

from database.clients import UserClient

class AdminFilter(Filter):
    def __init__(self, inverse: bool = False):
        self.inverse = inverse
    
    async def __call__(
        self,
        message: types.Message,
        psql_user_client: UserClient
    ) -> bool:
        res = await psql_user_client.is_admin(message.from_user.id)
        return res ^ self.inverse
    
    def __invert__(self) -> Self:
        return AdminFilter(not self.inverse)


class OwnerFilter(Filter):
    def __call__(self, message: types.Message, owner_id: int) -> bool:
        return message.from_user.id == owner_id
