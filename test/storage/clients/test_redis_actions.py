import pytest
from redis import Redis

from game.config import game_config
from game.schemas import FailureReason
from storage.clients.actions import ActionsClient


@pytest.fixture()
def mock_actions_storage(mocker) -> ActionsClient:
    return ActionsClient(
        mocker.Mock(Redis),
        100,
        game_config
    )

@pytest.fixture()
def planet_id():
    return 1

@pytest.fixture()
def other_planet_id():
    return 2

@pytest.fixture()
def city_id():
    return 1

@pytest.fixture()
def city_id2():
    return 2


@pytest.mark.parametrize(
    ('is_shielded', 'balance', 'new_balance', 'true_result'),
    [
        (False, game_config.SHIELD_COST + 1, 1, FailureReason.SUCCESS),
        (False, game_config.SHIELD_COST - 1, None, FailureReason.NOT_ENOUGH_MONEY),
        (True, 1, game_config.SHIELD_COST + 1, FailureReason.SUCCESS)
    ]
)
def test_shield_city(
    mock_actions_storage, planet_id,
    city_id, is_shielded, balance,
    new_balance, true_result
):
    mock_actions_storage.client.sismember.return_value = is_shielded
    mock_actions_storage.client.get.return_value = balance

    result = mock_actions_storage.shield_city(planet_id, city_id)
    if new_balance is not None:
        mock_actions_storage.client.set.assert_called_with(
            name=f'money_balance:{planet_id}',
            value=str(new_balance),
            ex=mock_actions_storage.ex
        )
    else:
        mock_actions_storage.client.set.assert_not_called()
    
    assert true_result == result


@pytest.mark.parametrize(
    ('is_developed', 'balance', 'new_balance', 'true_result'),
    [
        (False, game_config.DEVELOPMENT_COST + 1, 1, FailureReason.SUCCESS),
        (False, game_config.DEVELOPMENT_COST - 1, None, FailureReason.NOT_ENOUGH_MONEY),
        (True, 1, game_config.DEVELOPMENT_COST + 1, FailureReason.SUCCESS)
    ]
)
def test_develop_city(
    mock_actions_storage, planet_id,
    city_id, is_developed, balance,
    new_balance, true_result
):
    mock_actions_storage.client.sismember.return_value = is_developed
    mock_actions_storage.client.get.return_value = balance

    result = mock_actions_storage.develop_city(planet_id, city_id)
    if new_balance is not None:
        mock_actions_storage.client.set.assert_called_with(
            name=f'money_balance:{planet_id}',
            value=str(new_balance),
            ex=mock_actions_storage.ex
        )
    else:
        mock_actions_storage.client.set.assert_not_called()
    
    assert true_result == result


@pytest.mark.parametrize(
    ('is_attacked', 'balance', 'new_balance', 'true_result'),
    [
        (False, 1, 0, FailureReason.SUCCESS),
        (False, 0, None, FailureReason.NOT_ENOUGH_METEORITES),
        (True, 1, 2, FailureReason.SUCCESS)
    ]
)
def test_attack_city(
    mock_actions_storage, planet_id,
    city_id, is_attacked, balance,
    new_balance, true_result
):
    mock_actions_storage.client.sismember.return_value = is_attacked
    mock_actions_storage.client.get.return_value = balance

    result = mock_actions_storage.attack_city(planet_id, city_id)
    if new_balance is not None:
        mock_actions_storage.client.set.assert_called_with(
            name=f'meteorites_balance:{planet_id}',
            value=str(new_balance),
            ex=mock_actions_storage.ex
        )
    else:
        mock_actions_storage.client.set.assert_not_called()
    
    assert true_result == result


def test_sanction_planet(
    mock_actions_storage, planet_id,
    other_planet_id,
):
    mock_actions_storage.client.sismember.return_value = True
    mock_actions_storage.client.get.return_value = 0

    result = mock_actions_storage.sanction_planet(planet_id, other_planet_id)
    assert result == FailureReason.SUCCESS
    mock_actions_storage.client.srem.assert_called_once_with(
        f'sanctions:{planet_id}',
        str(other_planet_id)
    )
    mock_actions_storage.client.sadd.assert_not_called()


    mock_actions_storage.client.sismember.return_value = False

    result = mock_actions_storage.sanction_planet(planet_id, other_planet_id)
    assert result == FailureReason.SUCCESS
    mock_actions_storage.client.sadd.assert_called_once_with(
        f'sanctions:{planet_id}',
        str(other_planet_id)
    )
    # called once cause it's been called before where sismember.return_value = True
    mock_actions_storage.client.srem.assert_called_once()


@pytest.mark.parametrize(
    ('ordered_before', 'balance', 'ordered', 'new_balance', 'expected'),
    [
        (None, game_config.CREATE_COST, 1, 0, FailureReason.SUCCESS),
        (0, game_config.CREATE_COST, 1, 0, FailureReason.SUCCESS),
        (1, game_config.CREATE_COST, 0, 2 * game_config.CREATE_COST, FailureReason.SUCCESS),
        (1, game_config.CREATE_COST, 3, None, FailureReason.NOT_ENOUGH_MONEY),
    ]
)
def test_create_meteorites(
    mock_actions_storage, mocker, planet_id,
    ordered_before, balance, ordered, new_balance, expected
):
    def get_side_effect(key: str) -> str:
        if key.startswith('create'):
            return None if ordered_before is None else str(ordered_before)
        else:
            return str(balance)
    
    mocker.patch.object(mock_actions_storage.client, 'get', side_effect=get_side_effect)

    result = mock_actions_storage.create_meteorites(planet_id, ordered)
    assert result == expected
    if new_balance is None:
        mock_actions_storage.client.set.assert_not_called()
    else:
        mock_actions_storage.client.set.assert_any_call(
            name=f'money_balance:{planet_id}',
            value=str(new_balance),
            ex=mock_actions_storage.ex
        )
        mock_actions_storage.client.set.assert_any_call(
            name=f'create:{planet_id}',
            value=str(ordered),
            ex=mock_actions_storage.ex
        )


@pytest.mark.parametrize(
    ('invented_before', 'balance', 'invented_after', 'new_balance', 'expected'),
    [
        (None, game_config.INVENTION_COST, True, 0, FailureReason.SUCCESS),
        (False, game_config.INVENTION_COST, True, 0, FailureReason.SUCCESS),
        (False, 1, None, None, FailureReason.NOT_ENOUGH_MONEY),
        (True, 0, False, game_config.INVENTION_COST, FailureReason.SUCCESS)
    ]
)
def test_invent(
    mock_actions_storage, mocker, planet_id,
    invented_before, balance, invented_after, new_balance, expected
):
    def get_side_effect(key: str) -> str:
        if key.startswith('invent'):
            return None if invented_before is None else str(int(invented_before))
        else:
            return str(balance)
    
    mocker.patch.object(mock_actions_storage.client, 'get', side_effect=get_side_effect)

    result = mock_actions_storage.invent(planet_id)
    assert result == expected

    if new_balance is not None:
        mock_actions_storage.client.set.assert_any_call(
            name=f'money_balance:{planet_id}',
            value=str(new_balance),
            ex=mock_actions_storage.ex
        )
    else:
        mock_actions_storage.client.set.assert_not_called()
    
    if invented_after is not None:
        if invented_after:
            mock_actions_storage.client.set.assert_any_call(
                name=f'invent:{planet_id}',
                value='1',
                ex=mock_actions_storage.ex
            )
        else:
            mock_actions_storage.client.delete.assert_called_once_with(
                f'invent:{planet_id}'
            )


@pytest.mark.parametrize(
    ('eco_before', 'balance', 'eco_after', 'new_balance', 'expected'),
    [
        (None, game_config.ECO_COST, True, 0, FailureReason.SUCCESS),
        (False, game_config.ECO_COST, True, 0, FailureReason.SUCCESS),
        (False, 0, None, None, FailureReason.NOT_ENOUGH_METEORITES),
        (True, 0, False, game_config.ECO_COST, FailureReason.SUCCESS)
    ]
)
def test_eco_boost(
    mock_actions_storage, mocker, planet_id,
    eco_before, balance, eco_after, new_balance, expected
):
    def get_side_effect(key: str) -> str:
        if key.startswith('eco'):
            return None if eco_before is None else str(int(eco_before))
        else:
            return str(balance)
    
    mocker.patch.object(mock_actions_storage.client, 'get', side_effect=get_side_effect)

    result = mock_actions_storage.eco_boost(planet_id)
    assert result == expected

    if new_balance is not None:
        mock_actions_storage.client.set.assert_any_call(
            name=f'meteorites_balance:{planet_id}',
            value=str(new_balance),
            ex=mock_actions_storage.ex
        )
    else:
        mock_actions_storage.client.set.assert_not_called()
    
    if eco_after is not None:
        if eco_after:
            mock_actions_storage.client.set.assert_any_call(
                name=f'eco:{planet_id}',
                value='1',
                ex=mock_actions_storage.ex
            )
        else:
            mock_actions_storage.client.delete.assert_called_once_with(
                f'eco:{planet_id}'
            )


@pytest.mark.parametrize(
    ('any_negotiation_exists', 'side_negotiator', 'expected_result'),
    [
        (False, None, FailureReason.SUCCESS),
        (True, None, FailureReason.ALREADY_NEGOTIATING),
        (False, '2', FailureReason.SUCCESS),
        (False, '1', FailureReason.BILATERAL_NEGOTIATIONS),
    ]
)
def test_make_negotiations(
    mock_actions_storage, planet_id, other_planet_id,
    any_negotiation_exists, side_negotiator, expected_result
):
    mock_actions_storage.client.exists.return_value = any_negotiation_exists
    mock_actions_storage.client.get.return_value = side_negotiator

    result = mock_actions_storage.make_negotiations(planet_id, other_planet_id)
    assert result == expected_result
    if expected_result == FailureReason.SUCCESS:
        mock_actions_storage.client.set.assert_called_once_with(
            name=f'negotiate:{planet_id}',
            value=str(other_planet_id),
            ex=mock_actions_storage.ex
        )


def test_end_negotiations(mock_actions_storage, planet_id):
    mock_actions_storage.end_negotiations(planet_id)

    assert mock_actions_storage.client.delete(f'negotiate:{planet_id}')


def test_get_shielded_cities(mock_actions_storage, planet_id, city_id, city_id2):
    mock_actions_storage.client.smembers.return_value = [str(city_id), str(city_id2)]

    result = mock_actions_storage.get_shielded_cities(planet_id)
    assert result == [city_id, city_id2]
    mock_actions_storage.client.smembers.assert_called_once_with(f'shield:{planet_id}')


def test_get_developed_cities(mock_actions_storage, planet_id, city_id, city_id2):
    mock_actions_storage.client.smembers.return_value = [str(city_id), str(city_id2)]

    result = mock_actions_storage.get_developed_cities(planet_id)
    assert result == [city_id, city_id2]
    mock_actions_storage.client.smembers.assert_called_once_with(f'develop:{planet_id}')


def test_get_shielded_cities(mock_actions_storage, planet_id, city_id, city_id2):
    mock_actions_storage.client.smembers.return_value = [str(city_id), str(city_id2)]

    result = mock_actions_storage.get_attacked_cities(planet_id)
    assert result == [city_id, city_id2]
    mock_actions_storage.client.smembers.assert_called_once_with(f'attack:{planet_id}')


def test_get_sanctioned_planets(mock_actions_storage, planet_id, other_planet_id):
    mock_actions_storage.client.smembers.return_value = [str(other_planet_id)]

    result = mock_actions_storage.get_sanctioned_planets(planet_id)
    assert result == [other_planet_id]
    mock_actions_storage.client.smembers.assert_called_once_with(f'sanctions:{planet_id}')


@pytest.mark.parametrize(
    ('inmemory_meteorites', 'expected_result'),
    [
        (None, 0), ('0', 0), ('2', 2)
    ]
)
def test_get_created_meteorites(
    mock_actions_storage, planet_id, inmemory_meteorites, expected_result
):
    mock_actions_storage.client.get.return_value = inmemory_meteorites

    actual_result = mock_actions_storage.get_created_meteorites(planet_id)
    assert actual_result == expected_result
    mock_actions_storage.client.get.assert_called_once_with(f'create:{planet_id}')


@pytest.mark.parametrize(
    ('inmemory_eco', 'expected_result'),
    [(None, False), ('0', False), ('1', True)]
)
def test_get_eco_boost(
    mock_actions_storage, planet_id, inmemory_eco, expected_result
):
    mock_actions_storage.client.get.return_value = inmemory_eco

    actual_result = mock_actions_storage.get_eco_boost(planet_id)
    assert actual_result == expected_result
    mock_actions_storage.client.get.assert_called_once_with(f'eco:{planet_id}')


@pytest.mark.parametrize(
    ('inmemory_invent', 'expected_result'),
    [(None, False), ('0', False), ('1', True)]
)
def test_get_invented(
    mock_actions_storage, planet_id, inmemory_invent, expected_result
):
    mock_actions_storage.client.get.return_value = inmemory_invent

    actual_result = mock_actions_storage.get_invented(planet_id)
    assert actual_result == expected_result
    mock_actions_storage.client.get.assert_called_once_with(f'invent:{planet_id}')
