import logging
from typing import Self

from aiogram import types
from aiogram.filters import Filter
from sqlalchemy.ext.asyncio import AsyncSession

from database.clients import UserClient


class AdminFilter(Filter):
    def __init__(self, inverse: bool = False):
        self.inverse = inverse

    async def __call__(
        self, message: types.Message, session: AsyncSession, user_client: UserClient
    ) -> bool:
        res = await user_client.is_user_admin(session, message.from_user.id)
        print(
            f'[DEBUG] id(user_client)={id(user_client)}, '
            f'type(is_user_admin)={type(user_client.is_user_admin)}, '
            f'res={res}, inverse={self.inverse}, final={res ^ self.inverse}'
        )
        return res ^ self.inverse

    def __invert__(self) -> Self:
        return AdminFilter(not self.inverse)


class OwnerFilter(Filter):
    async def __call__(
        self, obj: types.Message | types.CallbackQuery, owner_id: int
    ) -> bool:
        return obj.from_user.id == owner_id
