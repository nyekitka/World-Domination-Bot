from unittest.mock import ANY

from aiogram.methods import DeleteMessages, SendMessage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
import pytest
from pytest_lazy_fixtures import lf

from app.handlers.lobby import chosen_lobby, chosen_lobby_admin, create_game, enter_game_player, leave_lobby, notify_lobby_on_join_leave, set_number_of_planets, set_pack
from app.filters.state import BotStates
from database.schemas import AdminDto, GameDto, GameStatus, PlanetDto, PlayerDto
from game.schemas import FailureReason
from test.app.mock_utils import mock_answer_message


@pytest.mark.asyncio
async def test_create_game_handler(
    mocker, message, fsm_context
):
    answer_mock = mock_answer_message(mocker)
    await create_game(message, fsm_context)

    state = await fsm_context.get_state()

    answer_mock.assert_awaited_once_with(
        'Выберите набор планет и городов для игры.',
        reply_markup=ANY,
    )
    assert state == BotStates.choose_pack.state


@pytest.mark.parametrize(
    'call',
    ['Solar System Pack'],
    indirect=['call']
)
@pytest.mark.asyncio
async def test_set_pack(
    mocker, call, fsm_context
):
    answer_mock = mock_answer_message(mocker)
    call_answer_mock = mocker.patch.object(CallbackQuery, 'answer')
    await set_pack(call, fsm_context)

    state = await fsm_context.get_state()
    
    answer_mock.assert_awaited_once_with(
        'Выберите количество планет в игре.',
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=str(i), callback_data=f'{i},Solar System Pack')
                    for i in range(2, 6)
                ],
                [
                    InlineKeyboardButton(text=str(i), callback_data=f'{i},Solar System Pack')
                    for i in range(6, 10)
                ],
            ]
        ),
    )
    call_answer_mock.assert_called_once_with()
    assert state == BotStates.planets_numbers.state



@pytest.mark.parametrize(
    'call',
    ['5,Solar System Pack'],
    indirect=['call']
)
@pytest.mark.asyncio
async def test_set_number_of_planets(
    mocker, call, fsm_context,
    game_client, mock_session,
):
    answer_mock = mock_answer_message(mocker)
    call_answer_mock = mocker.patch.object(CallbackQuery, 'answer')
    mocker.patch.object(game_client, 'create_game', return_value=GameDto(id=34, num_planets=5))
    await set_number_of_planets(
        call, fsm_context, game_client, mock_session,
    )

    state = await fsm_context.get_state()
    
    answer_mock.assert_awaited_once_with(
        'Игра 34 на 5 человек успешно создана.',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Создать лобби')],
                [KeyboardButton(text='Войти в лобби')],
            ]
        ),
    )
    call_answer_mock.assert_called_once_with()
    assert state is None


@pytest.mark.parametrize(
    ('is_admin', 'games'),
    [
        (True, [GameDto(id=1, num_planets=3)]),
        (False, [GameDto(id=1, num_planets=3)]),
        (True, []),
    ]
)
@pytest.mark.asyncio
async def test_enter_game_player(
    mocker, message, fsm_context,
    game_client, user_client, mock_session,
    is_admin, games,
):
    mocker.patch.object(user_client, 'is_user_admin', return_value=is_admin)
    make_user_mock = mocker.patch.object(user_client, 'make_new_user_if_not_exists')
    mocker.patch.object(game_client, 'get_all_games', return_value=games)
    mock_answer = mock_answer_message(mocker)

    await enter_game_player(message, fsm_context, game_client, user_client, mock_session)
    state = await fsm_context.get_state()

    if len(games) == 0 and is_admin:
        mock_answer.assert_awaited_once_with(
            'На данный момент нет ни одной доступной игры.',
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text='Создать лобби')],
                    [KeyboardButton(text='Войти в лобби')],
                ]
            )
        )
        assert state is None
    elif len(games) == 0:
        mock_answer.assert_awaited_once_with(
            'На данный момент нет ни одной доступной игры.',
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text='Войти в лобби')],
                ]
            )
        )
        assert state is None
    else:
        mock_answer.assert_awaited_once_with(
            'Выберите игру, в которую вы хотите зайти.',
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text='1', callback_data='1')]
                ]
            )
        )
        if is_admin:
            assert state == BotStates.choose_lobby_admin.state
        else:
            assert state == BotStates.choose_lobby.state
    
    if not is_admin:
        make_user_mock.assert_awaited_once()
    else:
        make_user_mock.assert_not_awaited()


@pytest.mark.parametrize(
    'is_admin',
    (True, False),
)
@pytest.mark.asyncio
async def test_leave_lobby(
    mocker, message, user_client, game_client,
    messages_client, mock_session, mock_bot,
    other_user, is_admin, user_id, game_id
):
    if is_admin:
        user_called = AdminDto(tg_id=user_id, game_id=game_id)
    else:
        user_called = PlayerDto(tg_id=user_id, game_id=game_id)
    
    mock_asnwer = mock_answer_message(mocker)
    mocker.patch.object(user_client, 'get_user', return_value=user_called)
    mocker.patch.object(user_client, 'kick_user', return_value=FailureReason.SUCCESS)
    mocker.patch.object(messages_client, 'find_all_messages', return_value=[69])
    mocker.patch.object(messages_client, 'delete_all_messages')
    mocker.patch.object(
        game_client, 
        'get_all_active_admins',
        return_value=[AdminDto(tg_id=other_user.id, game_id=game_id)]
    )
    notify_mock = mocker.patch('app.handlers.lobby.notify_lobby_on_join_leave')
    mocker.patch.object(user_client, 'get_game', return_value=GameDto(id=game_id, num_planets=3))
    mocker.patch.object(game_client, 'get_player_planet', return_value=PlanetDto(id=1, name='planet', game_id=game_id))

    mock_bot.add_result_for(DeleteMessages, True, True)

    await leave_lobby(message, user_client, game_client, messages_client, mock_session)
    mock_asnwer.assert_awaited_once_with('Вы вышли из игры.', reply_markup=ANY)

    if is_admin:
        with pytest.raises(IndexError):
            mock_bot.get_request()

    else:
        delete_req = mock_bot.get_request()

        notify_mock.assert_awaited_once()

        assert isinstance(delete_req, DeleteMessages)
        assert delete_req.message_ids == [69]


@pytest.mark.parametrize(
    'call',
    ['5'],
    indirect=['call']
)
@pytest.mark.asyncio
async def test_chosen_lobby_admin(
    mocker, fsm_context, call,
    user_client, mock_session,
    game_id,
):
    mocker.patch.object(user_client, 'get_game', return_value=GameDto(id=game_id, num_planets=3))
    mocker.patch.object(user_client, 'join_user', return_value=FailureReason.SUCCESS)
    answer_mock = mock_answer_message(mocker)
    await fsm_context.set_state(BotStates.choose_lobby_admin)

    await chosen_lobby_admin(call, fsm_context, user_client, mock_session)
    state = await fsm_context.get_state()

    assert state is None
    answer_mock.assert_awaited_once_with(
        f'Вы присоединились к игре {game_id}. Теперь вам доступна панель администрации игры, а также вся информация о ней.',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Начать игру')],
                [KeyboardButton(text='Выйти из лобби')],
            ]
        )
    )
    user_client.get_game.assert_awaited_once_with(mock_session, 5)


@pytest.mark.parametrize(
    ('call', 'game_status'),
    [
        ('5', GameStatus.WAITING),
        ('5', GameStatus.ROUND),
    ],
    indirect=['call']
)
@pytest.mark.asyncio
async def test_chosen_lobby(
    mocker, fsm_context, call,
    user_client, game_client, mock_session,
    game_id, game_status, actions_client,
    messages_client,
):
    mocker.patch.object(game_client, 'get_game', return_value=GameDto(id=game_id, num_planets=3, status=game_status))
    mocker.patch.object(user_client, 'join_user', return_value=FailureReason.SUCCESS)
    mocker.patch.object(game_client, 'get_player_planet', return_value=PlanetDto(id=1, name='planet', game_id=game_id))
    mocker.patch.object(game_client, 'get_all_planets_in_game', return_value=[])
    mocker.patch.object(actions_client, 'get_order_info')
    notify_mock = mocker.patch('app.handlers.lobby.notify_lobby_on_join_leave')
    send_all_info_mock = mocker.patch('app.handlers.lobby.send_all_info')
    answer_mock = mock_answer_message(mocker)

    await fsm_context.set_state(BotStates.choose_lobby)

    await chosen_lobby(
        call, fsm_context, user_client,
        game_client, actions_client, messages_client,
        mock_session
    )
    state = await fsm_context.get_state()

    assert state is None
    answer_mock.assert_awaited_once_with(
        f'Вы вошли в игру {game_id}!\nВаша планета - planet.',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text='Выйти из лобби')],
            ]
        )
    )
    game_client.get_game.assert_awaited_once_with(mock_session, 5)
    if game_status == GameStatus.WAITING:
        notify_mock.assert_awaited_once()
        send_all_info_mock.assert_not_awaited()
    else:
        notify_mock.assert_not_awaited()
        send_all_info_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_lobby_on_join_leave(
    mocker, mock_bot, game_id,
    message, game_client, mock_session,
    user_id, other_user_id,
):
    mocker.patch.object(
        game_client,
        'get_all_active_players',
        return_value=[PlayerDto(tg_id=user_id, game_id=game_id)]
    )
    mocker.patch.object(
        game_client,
        'get_all_active_admins',
        return_value=[AdminDto(tg_id=other_user_id, game_id=game_id)]
    )

    for _ in range(2):
        mock_bot.add_result_for(SendMessage, True, message)

    await notify_lobby_on_join_leave(
        mock_bot,
        GameDto(id=game_id, num_planets=3),
        PlanetDto(id=1, name='name', game_id=game_id),
        game_client,
        mock_session,
        lambda name, online, all: f'Имя планеты - {name}. В игре: {online}/{all}'
    )

    for _ in range(2):
        request = mock_bot.get_request()
        assert isinstance(request, SendMessage)
        assert request.chat_id in (user_id, other_user_id)
        assert request.text == 'Имя планеты - name. В игре: 1/3'
