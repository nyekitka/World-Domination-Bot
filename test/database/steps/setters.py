from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import Planet


async def set_balance_for_planet(
    session: async_sessionmaker,
    planet_id: int,
    balance: int
) -> None:
    async with session() as s:
        s.execute((
            update(Planet)
            .where(Planet.id == planet_id)
            .values(balance=balance)
        ))
