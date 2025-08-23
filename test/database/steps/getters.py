from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import Planet


async def get_balance_of_planet(
    session: async_sessionmaker,
    planet_id: int
) -> int:
    async with session() as s:
        planet = await s.get(Planet, planet_id)
        return planet.balance
