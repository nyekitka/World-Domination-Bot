import pytest
from redis.asyncio import Redis

from storage.clients.messages import MessagesClient
from storage.schemas import MessageType


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


def test_set_info_message_id(
    mocker, mock_messages_storage, message_id, tg_id
):
    mock_messages_storage.set_info_message_id(tg_id, MessageType.ECO, message_id)

    mock_messages_storage.client.set.assert_called_once_with(
        name=f'info:eco:{tg_id}',
        value=str(message_id),
        ex=mocker.ANY
    )