import pytest

from keyboards.schemas import (
    Action,
    ActionType,
    get_action_data,
    get_action_from_data,
    validate_action,
)


@pytest.mark.parametrize(
    ('action_data', 'result'),
    [
        ('negotiate:24:21', True),
        ('invent:22:None', True),
        ('action:2:2', False),
        ('accept_negotiations:1:1', True),
        ('a:b:c', False),
        ('attack:1', False),
    ]
)
def test_validate_action(action_data, result):
    assert validate_action(action_data) == result


@pytest.mark.parametrize(
    ('result', 'action'),
    [
        ('negotiate:24:21', Action(
            action_type=ActionType.NEGOTIATE,
            planet_id=24,
            argument=21,
        )),
        ('accept_negotiations:1:1', Action(
            action_type=ActionType.ACCEPT_NEGOTIATIONS,
            planet_id=1,
            argument=1,
        )),
    ]
)
def test_action_transformations(action, result):
    assert get_action_from_data(result) == action
    assert get_action_data(action) == result
