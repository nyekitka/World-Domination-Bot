import pytest

from database.config import game_config
from database.schemas import FailureReason
from test.database.steps.getters import get_balance_of_planet
from test.database.steps.setters import set_balance_for_planet


@pytest.mark.parametrize(
    ('balance', 'exp_new_balance', 'exp_result'),
    [
        (game_config.SHIELD_COST + 1, 1, FailureReason.SUCCESS),
        (1, 1, FailureReason.NOT_ENOUGH_MONEY),
    ]
)
@pytest.mark.asyncio
async def test_order_shield_for_city_without_order(
    mock_actions_client, city_id, planet_id, balance, exp_new_balance, exp_result
):
    await set_balance_for_planet(
        mock_actions_client.session, planet_id, balance
    )

    result = mock_actions_client.order_shield_for_city(city_id)
    new_balance = get_balance_of_planet(mock_actions_client.session, planet_id)

    assert result == exp_result
    assert new_balance == exp_new_balance
