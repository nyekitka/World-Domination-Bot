import pytest

from database.models import Order
from game.schemas import OrderType


@pytest.mark.asyncio
async def test_get_all_orders_in_game(
    mock_info_client, game_id,
    city_id, city_id_2, city_id_3,
    planet_id, planet_id_2, planet_id_3
):
    all_orders = [
        {
            planet_id_2: {
                OrderType.ATTACK: [city_id_2],
                OrderType.CREATE: 3,
                OrderType.DEVELOP: [city_id],
                OrderType.SANCTIONS: [planet_id]
            },
            planet_id_3: {
                OrderType.ATTACK: [city_id_3],
                OrderType.INVENT: True,
                OrderType.ECO: True,
            },
        },
        {
            planet_id: {
                OrderType.ATTACK: [city_id_2, city_id_3],
                OrderType.CREATE: 1,
                OrderType.SHIELD: [city_id],
            },
        },
    ]
    orders = [
        Order(action=OrderType.ATTACK, planet_id=planet_id_2, round=1, argument=city_id_2),
        Order(action=OrderType.CREATE, planet_id=planet_id_2, round=1, argument=3),
        Order(action=OrderType.DEVELOP, planet_id=planet_id_2, round=1, argument=city_id),
        Order(action=OrderType.SANCTIONS, planet_id=planet_id_2, round=1, argument=planet_id),
        Order(action=OrderType.ATTACK, planet_id=planet_id_3, round=1, argument=city_id_3),
        Order(action=OrderType.INVENT, planet_id=planet_id_3, round=1, argument=True),
        Order(action=OrderType.ECO, planet_id=planet_id_3, round=1, argument=True),
        Order(action=OrderType.ATTACK, planet_id=planet_id, round=2, argument=city_id_2),
        Order(action=OrderType.ATTACK, planet_id=planet_id, round=2, argument=city_id_3),
        Order(action=OrderType.CREATE, planet_id=planet_id, round=2, argument=1),
        Order(action=OrderType.SHIELD, planet_id=planet_id, round=2, argument=city_id),
    ]

    async with mock_info_client.session() as s:
        s.add_all(orders)
        await s.commit()
    
    result = await mock_info_client.get_all_orders_in_game(game_id)
    assert result == all_orders
