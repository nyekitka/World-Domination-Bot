from unittest.mock import AsyncMock

from aiogram.types import Message
from pytest_mock import MockerFixture


def mock_answer_message(mocker: MockerFixture) -> AsyncMock:
    answer_mock = AsyncMock()
    mocker.patch.object(Message, 'answer', answer_mock)
    return answer_mock
