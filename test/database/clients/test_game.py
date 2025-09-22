import pytest
from sqlalchemy import select

from database.models import Admin, City, Game, Planet, Player
from database.schemas import GameStatus


@pytest.mark.asyncio
async def test_create_game(mock_game_client, admin_id, pack):
    game = await mock_game_client.create_game(admin_id, pack)

    async with mock_game_client.session() as s:
        admin = await s.get(Admin, admin_id)
        assert admin.game_id == game.id
        for planet in pack.planets:
            result = await s.execute(
                select(Planet).where(
                    Planet.name == planet.name, Planet.game_id == game.id
                )
            )
            orm_planet = result.scalars().all()
            assert orm_planet

            for city in planet.cities:
                result = await s.execute(
                    select(City).where(
                        City.name == city.name, City.planet_id == orm_planet[0].id
                    )
                )
                orm_city = result.scalars().all()
                assert orm_city


@pytest.mark.asyncio
async def test_end_game(mock_game_client, game_id, player_ids, admin_id):
    async with mock_game_client.session() as s:
        admin = await s.get(Admin, admin_id)
        admin.game_id = game_id
        for player_id in player_ids:
            player = await s.get(Player, player_id)
            player.game_id = game_id
        await s.commit()

    await mock_game_client.end_game(game_id)

    async with mock_game_client.session() as s:
        admin = await s.get(Admin, admin_id)
        assert admin.game_id is None
        for player_id in player_ids:
            player = await s.get(Player, player_id)
            assert player.game_id is None

        game = await s.get(Game, game_id)
        assert game.status == GameStatus.ENDED
