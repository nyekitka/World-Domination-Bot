from aiogram import types
from aiogram.filters import CommandStart, CommandObject
from aiogram.methods import SendMessage, GetChat
import pytest
from pytest_lazy_fixtures import lf

from database.schemas import AdminDto, PlayerDto
from app.handlers.main_page import (
    accept_knight,
    fire_admin,
    refuse_knight,
    start,
    request,
)
from game.schemas import FailureReason
from test.app.mock_utils import mock_answer_message


@pytest.mark.parametrize(
    ['user_dto', 'expected_message', 'expected_keyboard'],
    [
        (
            None,
            'Привет, {0} 👋. Ты не находишься ни в одном из лобби. Чтобы войти в лобби нажми кнопку "Войти в лобби".',
            types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text='Войти в лобби')]]
            ),
        ),
        (
            PlayerDto(tg_id=1, game_id=None),
            'Привет, {0} 👋. Ты не находишься ни в одном из лобби. Чтобы войти в лобби нажми кнопку "Войти в лобби".',
            types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text='Войти в лобби')]]
            ),
        ),
        (
            PlayerDto(tg_id=1, game_id=1),
            'С возвращением, {0}!',
            types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text='Выйти из лобби')],
                ]
            ),
        ),
        (
            AdminDto(tg_id=1, game_id=None),
            'Приветствую, {0} 👋. Ты не администрируешь ни одну из игр. Чтобы войти в игру как администратор нажмите кнопку "Войти в лобби".',
            types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text='Создать лобби')],
                    [types.KeyboardButton(text='Войти в лобби')],
                ]
            ),
        ),
        (
            AdminDto(tg_id=1, game_id=1),
            'С возвращением, {0}!',
            types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text='Начать игру')],
                    [types.KeyboardButton(text='Выйти из лобби')],
                ]
            ),
        ),
    ],
)
@pytest.mark.asyncio
async def test_start(
    mocker,
    user_client,
    mock_session,
    message,
    user_dto,
    expected_message,
    expected_keyboard,
):
    mocker.patch.object(user_client, 'get_user', return_value=user_dto)
    answer_mock = mock_answer_message(mocker)

    await start(message, user_client, mock_session)
    answer_mock.assert_awaited_once_with(
        expected_message.format(message.from_user.first_name),
        reply_markup=expected_keyboard,
    )


@pytest.mark.asyncio
async def test_request(mocker, message, mock_bot, other_user_id):
    answer_mock = mock_answer_message(mocker)
    mock_bot.add_result_for(SendMessage, True, message)

    await request(message, other_user_id)

    answer_mock.assert_awaited_once_with(
        'Запрос отправлен верховному лидеру. Ждите его ответа.'
    )
    last_request = mock_bot.get_request()
    name = message.from_user.full_name
    id = message.from_user.id
    assert isinstance(last_request, SendMessage)
    assert last_request.chat_id == other_user_id
    assert (
        last_request.text
        == f'Пользователь [{name}](tg://user?id={id}) отправил вам запрос на право администратора\\.'
    )


@pytest.mark.parametrize('call', ['knight 1'], indirect=['call'])
@pytest.mark.asyncio
async def test_accept_knight(
    mocker, call, chat_full_info, user_client, mock_bot, mock_session, user, message
):
    mock_bot.add_result_for(SendMessage, True, message)
    mock_bot.add_result_for(GetChat, True, chat_full_info)
    answer_mock = mock_answer_message(mocker)
    mock_promote = mocker.patch.object(
        user_client, 'promote_to_admin', return_value=FailureReason.SUCCESS
    )

    await accept_knight(call, user_client, mock_session)

    sent_message = mock_bot.get_request()
    mock_promote.assert_called_once()
    answer_mock.assert_awaited_once_with(
        f'Вы успешно назначили {user.full_name} администратором!'
    )
    assert isinstance(sent_message, SendMessage)
    assert sent_message.text == '👑 Верховный лидер назначил вас администратором!'
    assert sent_message.chat_id == 1


@pytest.mark.parametrize('call', ['notknight 1'], indirect=['call'])
@pytest.mark.asyncio
async def test_refuse_knight(mocker, call, chat_full_info, mock_bot, user, message):
    mock_bot.add_result_for(SendMessage, True, message)
    mock_bot.add_result_for(GetChat, True, chat_full_info)
    answer_mock = mock_answer_message(mocker)

    await refuse_knight(call)

    sent_message = mock_bot.get_request()
    answer_mock.assert_awaited_once_with(f'Вы отказали пользователю {user.full_name}.')
    assert isinstance(sent_message, SendMessage)
    assert (
        sent_message.text
        == 'Верховный лидер посчитал вас недостойным статуса администратора.'
    )
    assert sent_message.chat_id == 1


@pytest.mark.parametrize('user_game_id', (None, lf('game_id')))
@pytest.mark.asyncio
async def test_fire_admin(
    message, user_client, mock_session, chat_full_info, mock_bot, mocker, user_game_id
):
    command = CommandObject(command='fire', args='@nyekitka')
    if user_game_id is not None:
        mock_bot.add_result_for(SendMessage, True, message)
    mock_bot.add_result_for(SendMessage, True, message)
    mock_bot.add_result_for(GetChat, True, chat_full_info)

    answer_mock = mock_answer_message(mocker)
    mock_promote = mocker.patch.object(
        user_client,
        'get_user',
        return_value=AdminDto(tg_id=chat_full_info.id, game_id=user_game_id),
    )
    mock_fire = mocker.patch.object(
        user_client, 'fire_admin', return_value=FailureReason.SUCCESS
    )

    await fire_admin(message, command, user_client, mock_session)

    last_message = mock_bot.get_request()
    if user_game_id is not None:
        assert (
            last_message.text
            == 'Вы были выкинуты из игры, поскольку теперь вы не являетесь администратором.'
        )
        last_message = mock_bot.get_request()

    assert last_message.text == '👎 Верховный лидер лишил вас статуса администратора.'
    answer_mock.assert_awaited_once_with(
        f'Вы сняли полномочия администратора с {chat_full_info.first_name}.'
    )
    mock_fire.assert_called_once()
    mock_promote.assert_called_once()
