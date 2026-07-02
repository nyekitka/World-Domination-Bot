import pytest
from redis import Redis

from storage.clients.messages import MessagesClient
from storage.schemas import MessageType, INFO_MESSAGE_TYPES, PLANET_MESSAGE_TYPES


@pytest.fixture()
def mock_messages_storage(mocker) -> MessagesClient:
    return MessagesClient(
        mocker.Mock(Redis),
        100
    )


@pytest.fixture()
def message_id() -> int:
    return 123456789


@pytest.fixture()
def tg_id() -> int:
    return 9876543210


def test_get_info_message_id(
    mock_messages_storage, message_id, tg_id
):
    mock_messages_storage.client.get.return_value = message_id

    result = mock_messages_storage.get_info_message_id(tg_id, MessageType.ECO)
    assert result == message_id
    mock_messages_storage.client.get.assert_called_once_with(
        f'info:eco:{tg_id}'
    )


def test_set_info_message_id(
    mocker, mock_messages_storage, message_id, tg_id
):
    mock_messages_storage.set_info_message_id(tg_id, MessageType.ECO, message_id)

    mock_messages_storage.client.set.assert_called_once_with(
        name=f'info:eco:{tg_id}',
        value=str(message_id),
        ex=mocker.ANY
    )

def test_delete_info_message_id(
    mock_messages_storage, tg_id
):
    mock_messages_storage.delete_info_message_id(tg_id, MessageType.ECO,)

    mock_messages_storage.client.delete.assert_called_once_with(
        f'info:eco:{tg_id}',
    )

@pytest.mark.parametrize(
    ('redis_message_id', 'real_message_id'),
    [
        ('1', 1),
        (None, None)
    ]
)
def test_get_planet_message_id(
    mock_messages_storage, redis_message_id, real_message_id, tg_id, planet_id
):
    mock_messages_storage.client.hget.return_value = redis_message_id

    result = mock_messages_storage.get_planet_message_id(
        tg_id, MessageType.ATTACK, planet_id
    )
    assert result == real_message_id
    mock_messages_storage.client.hget.assert_called_once_with(
        f'planet:attack:{tg_id}',
        str(planet_id)
    )


@pytest.mark.parametrize(
    ('planet_ids', 'redis_planet_ids'),
    [
        ((1,), ('1',)),
        ((1, 2), ('1', '2'))
    ]
)
def test_delete_planet_message_ids(
    mock_messages_storage, tg_id, planet_ids, redis_planet_ids
):
    mock_messages_storage.delete_planet_message_ids(tg_id, MessageType.ATTACK, *planet_ids)
    mock_messages_storage.client.hdel.assert_called_once_with(
        f'planet:attack:{tg_id}',
        *redis_planet_ids
    )

def test_set_planet_message_id(
    mock_messages_storage, tg_id, planet_id, message_id
):
    mock_messages_storage.set_planet_message_id(tg_id, planet_id, MessageType.ATTACK, message_id)
    mock_messages_storage.client.hset.assert_called_once_with(
        f'planet:attack:{tg_id}',
        str(planet_id),
        str(message_id)
    )

@pytest.mark.parametrize(
    ('mock_kvs', 'true_result'),
    [
        (
            {
                'info:city': '1234',
                'info:eco': '2345',
                'planet:attack': {
                    '1': '2143',
                    '2': '1432'
                }
            },
            [1234, 2345, 2143, 1432]
        ),
        (
            {
                'info:meteorites': '1234',
            },
            [1234]
        ),
    ]
)
def test_find_all_messages(
    mock_messages_storage, mocker, mock_kvs, true_result, tg_id
):
    patched_mock_kvs = {
        f'{k}:{tg_id}' : v
        for k, v in mock_kvs.items()
    }
    def get_side_effect(key: str) -> str | None:
        if key in patched_mock_kvs:
            if isinstance(patched_mock_kvs[key], str):
                return patched_mock_kvs[key]
        return None
    
    def hget_side_effect(key: str) -> dict[str, str] | None:
        if key in patched_mock_kvs:
            if isinstance(patched_mock_kvs[key], dict):
                return patched_mock_kvs[key]
        return None
    
    mocker.patch.object(mock_messages_storage.client, 'get', side_effect=get_side_effect)
    mocker.patch.object(mock_messages_storage.client, 'hgetall', side_effect=hget_side_effect)

    result = mock_messages_storage.find_all_messages(tg_id)
    assert sorted(result) == sorted(true_result)

def test_delete_all_messages(
    mock_messages_storage, tg_id
):
    mock_messages_storage.delete_all_messages(tg_id)
    for message_type in INFO_MESSAGE_TYPES:
        mock_messages_storage.client.delete.assert_any_call(f'info:{message_type}:{tg_id}')
    
    for message_type in PLANET_MESSAGE_TYPES:
        mock_messages_storage.client.delete.assert_any_call(f'planet:{message_type}:{tg_id}')
