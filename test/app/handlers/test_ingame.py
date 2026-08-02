from random import randint
from unittest.mock import AsyncMock

from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import ReplyKeyboardRemove
import pytest
from pytest_mock import MockFixture

from app.filters.state import BotStates
from app.handlers.ingame import (
    end_the_game, handle_accept_negotiations_action, handle_action, handle_eco_action, handle_end_negotiations_action, handle_invent_action, handle_negotiate_action, handle_refuse_negotiations_action, handle_sanctions_action, handle_transaction_action, set_amount_of_money, start_round,
    handle_attack_action,
    handle_city_action,
    handle_create_action
)
from database.schemas import AdminDto, GameDto, GameStatus, PlanetDto, PlayerDto
from game.schemas import FailureReason
from test.app.mock_utils import mock_answer_message

@pytest.mark.parametrize(
    ('round', 'expected_text'),
    [
        (1, '*Первый раунд начался*'),
        (2, '*Второй раунд начался*\n\nВам будут приходить запросы на переговоры от игроков\\. Как только придёт запрос, направляйтесь к команде, отправившей запрос и сопроводите дипломата до другой команды\\.')
    ]
)
@pytest.mark.asyncio
async def test_start_round(
    message, user_client, mock_bot,
    messages_client, game_client,
    actions_client, info_client,
    mock_session, mocker,
    user_id, other_user_id, game_id,
    expected_text, round
):
    mocker.patch.object(user_client, 'get_user', return_value=AdminDto(tg_id=user_id, game_id=game_id))
    mocker.patch.object(game_client, 'start_new_round', return_value=FailureReason.SUCCESS)
    mocker.patch.object(
        game_client, 'get_all_active_admins',
        return_value=[
            AdminDto(tg_id=user_id, game_id=game_id),
            AdminDto(tg_id=other_user_id, game_id=game_id),
        ]
    )
    mocker.patch.object(
        game_client, 'get_game',
        return_value=GameDto(id=game_id, status=GameStatus.ROUND, round=round, num_planets=3)
    )
    mocker.patch.object(
        game_client, 'get_all_planets_and_cities',
        return_value={1: (PlanetDto(id=1, name='planet', game_id=game_id, owner_id=other_user_id), [])}
    )
    send_all_info_mock = mocker.patch('app.handlers.ingame.send_all_info')
    mocker.patch('app.handlers.ingame.get_round_notifier', return_value=AsyncMock())

    mock_bot.add_result_for(SendMessage, True, message)
    mock_bot.add_result_for(SendMessage, True, message)
    await start_round(
        message, user_client, messages_client,
        game_client, actions_client, info_client,
        mock_session,
    )

    send_all_info_mock.assert_awaited_once()
    _, kwargs = send_all_info_mock.call_args
    assert kwargs['planet_id'] == 1
    assert kwargs['user_id'] == other_user_id

    request = mock_bot.get_request()
    assert isinstance(request, SendMessage)
    assert request.text == expected_text
    assert request.reply_markup == ReplyKeyboardRemove()


@pytest.mark.asyncio
async def test_end_the_game(
    message, user_client,
    game_client, mock_session,
    mocker, game_id,
    user_id, other_user_id, mock_bot
):
    mocker.patch.object(user_client, 'get_user', return_value=AdminDto(tg_id=user_id, game_id=game_id))
    mocker.patch.object(user_client, 'get_game', return_value=GameDto(id=game_id, num_planets=3))

    mocker.patch.object(
        game_client, 'get_all_active_admins',
        return_value=[AdminDto(tg_id=user_id, game_id=game_id)]
    )
    mocker.patch.object(
        game_client, 'get_all_active_players',
        return_value=[PlayerDto(tg_id=other_user_id, game_id=game_id)]
    )
    mocker.patch.object(game_client, 'end_game')

    for _ in range(2):
        mock_bot.add_result_for(SendMessage, True, message)

    await end_the_game(message, user_client, game_client, mock_session)

    player_request = mock_bot.get_request()
    admin_request = mock_bot.get_request()

    assert player_request.text == 'Игра была прервана администратором. О подробностях узнавайте у организаторов.'
    assert admin_request.text == 'Игра была прервана. Вы автоматически вышли из игры.'
    assert player_request.chat_id == other_user_id
    assert admin_request.chat_id == user_id
    game_client.end_game.assert_awaited_once_with(mock_session, game_id)


@pytest.mark.parametrize(
    ('call', 'handler'),
    [
        ('{"action_type": "attack", "planet_id": 1, "argument": 2}', 'handle_attack_action'),
        ('{"action_type": "develop", "planet_id": 1, "argument": 2}', 'handle_city_action'),
        ('{"action_type": "shield", "planet_id": 1, "argument": 2}', 'handle_city_action'),
        ('{"action_type": "create", "planet_id": 1, "argument": 2}', 'handle_create_action'),
        ('{"action_type": "eco", "planet_id": 1, "argument": null}', 'handle_eco_action'),
        ('{"action_type": "sanctions", "planet_id": 1, "argument": 2}', 'handle_sanctions_action'),
        ('{"action_type": "invent", "planet_id": 1, "argument": null}', 'handle_invent_action'),
        ('{"action_type": "negotiate", "planet_id": 1, "argument": 2}', 'handle_negotiate_action'),
        ('{"action_type": "transaction", "planet_id": 1, "argument": 2}', 'handle_transaction_action'),
        ('{"action_type": "accept_negotiations", "planet_id": 1, "argument": 2}', 'handle_accept_negotiations_action'),
        ('{"action_type": "refuse_negotiations", "planet_id": 1, "argument": 2}', 'handle_refuse_negotiations_action'),
        ('{"action_type": "end_negotiations", "planet_id": 1, "argument": 2}', 'handle_end_negotiations_action'),
    ],
    indirect=['call']
)
@pytest.mark.asyncio
async def test_handle_action_delegating(
    call, fsm_context, handler,
    mocker, user_client, game_client,
    messages_client, actions_client, mock_session,
    user_id, game_id
):
    mocker.patch.object(actions_client, 'get_balance', return_value=0)
    mocker.patch.object(user_client, 'get_user', return_value=AdminDto(tg_id=user_id, game_id=game_id))
    mocker.patch.object(game_client, 'get_game', return_value=GameDto(id=game_id, num_planets=3))
    mocker.patch.object(game_client, 'get_player_planet')
    mock_handler = mocker.patch(f'app.handlers.ingame.{handler}')
    await handle_action(
        call, fsm_context, user_client,
        game_client, messages_client,
        actions_client, mock_session
    )

    mock_handler.assert_awaited_once()


@pytest.mark.parametrize(
    ('call', 'meteorites_changed', 'money_changed'),
    [
        ('{"action_type": "eco", "planet_id": 1, "argument": 2}', False, False),
        ('{"action_type": "eco", "planet_id": 1, "argument": 2}', False, True),
        ('{"action_type": "eco", "planet_id": 1, "argument": 2}', True, False),
        ('{"action_type": "eco", "planet_id": 1, "argument": 2}', True, True),
    ],
    indirect=['call']
)
@pytest.mark.asyncio
async def test_handle_action_messages(
    call, fsm_context, message,
    mocker, user_client, game_client,
    messages_client, actions_client, mock_session,
    user_id, game_id, mock_bot,
    meteorites_changed, money_changed,
):
    side_effect = [1]*4
    if meteorites_changed:
        side_effect[3] = 2
    if money_changed:
        side_effect[2] = 2
    
    mocker.patch.object(actions_client, 'get_balance', return_value=0)
    mocker.patch.object(user_client, 'get_user', return_value=AdminDto(tg_id=user_id, game_id=game_id))
    mocker.patch.object(game_client, 'get_game', return_value=GameDto(id=game_id, num_planets=3))
    mocker.patch.object(game_client, 'get_player_planet', return_value=PlanetDto(id=1, name='name', game_id=game_id, owner_id=message.from_user.id))
    mocker.patch.object(game_client, 'get_cities_of_planet', return_value=[])
    mocker.patch.object(game_client, 'spend')
    mocker.patch(f'app.handlers.ingame.handle_eco_action')
    mocker.patch.object(actions_client, 'get_balance', side_effect=side_effect)
    mocker.patch.object(actions_client, 'get_shielded_cities', return_value=[])
    mocker.patch.object(actions_client, 'get_developed_cities', return_value=[])
    mocker.patch.object(actions_client, 'get_created_meteorites', return_value=0)
    mocker.patch.object(messages_client, 'get_info_message_id', return_value=message.message_id)

    for _ in range(int(meteorites_changed) + int(money_changed)):
        mock_bot.add_result_for(EditMessageText, True, True)

    await handle_action(
        call, fsm_context, user_client,
        game_client, messages_client,
        actions_client, mock_session
    )

    if money_changed or meteorites_changed:
        request = mock_bot.get_request()
    else:
        with pytest.raises(IndexError):
            mock_bot.get_request()
    if meteorites_changed:
        assert isinstance(request, EditMessageText)
        assert request.chat_id == message.from_user.id
        assert request.message_id == message.message_id

        messages_client.get_info_message_id.assert_any_call(
            message.from_user.id, 'meteorites'
        )
        if money_changed:
            request = mock_bot.get_request()
    if money_changed:
        assert isinstance(request, EditMessageText)
        assert request.chat_id == message.from_user.id
        assert request.message_id == message.message_id

        messages_client.get_info_message_id.assert_any_call(
            message.from_user.id, 'city'
        )


@pytest.mark.parametrize(
    ('message', 'current_balance', 'is_wrong_answer'),
    [
        ('20', 100, False),
        ('20', 10, False),
        ('0', 100, False),
        ('-20', 100, True),
        ('abc', 100, True)
    ],
    indirect=['message']
)
@pytest.mark.asyncio
async def test_set_amount_of_money(
    message, fsm_context, game_client,
    actions_client, messages_client, mock_session,
    game_id, is_wrong_answer, mocker, mock_bot,
    user_id, other_user_id, current_balance
):
    await fsm_context.set_data({
        'from_planet': PlanetDto(id=1, name='planet', game_id=game_id, owner_id=user_id),
        'to_planet': PlanetDto(id=2, name='other_planet', game_id=game_id, owner_id=other_user_id),
        'game': GameDto(id=game_id, num_planets=3),
    })
    await fsm_context.set_state(BotStates.transaction_state)
    mock_answer = mock_answer_message(mocker)
    
    mocker.patch.object(game_client, 'get_cities_of_planet')
    mocker.patch.object(game_client, 'transfer', return_value=FailureReason.SUCCESS)
    mocker.patch.object(messages_client, 'get_info_message_id', side_effect=[1, 2])
    mock_bot.add_result_for(SendMessage, True, message)
    mock_bot.add_result_for(EditMessageText, True, True)
    mock_bot.add_result_for(EditMessageText, True, True)
    mocker.patch.object(actions_client, 'get_shielded_cities', return_value=[])
    mocker.patch.object(actions_client, 'get_developed_cities', return_value=[])
    mocker.patch.object(actions_client, 'set_balance')
    mocker.patch.object(actions_client, 'get_balance', return_value=current_balance)
    

    await set_amount_of_money(
        message, fsm_context, game_client,
        actions_client, messages_client, mock_session,
    )

    if is_wrong_answer:
        mock_answer.assert_awaited_once_with(
            'Неверный ввод. Введите неотрицательное число, обозначающее сумму, которую вы хотите перевести планете.'
        )
        state = await fsm_context.get_state()
        assert state == BotStates.transaction_state.state
    elif current_balance < int(message.text):
        mock_answer.assert_awaited_once_with(
            'Недостаточно средств для перевода. Укажите сумму меньше.'
        )
        state = await fsm_context.get_state()
        assert state == BotStates.transaction_state.state
    elif message.text == '0':
        state = await fsm_context.get_state()
        assert state is None
        mock_answer.assert_not_awaited()
        with pytest.raises(IndexError):
            mock_bot.get_request()
    else:
        send_message_request = mock_bot.get_request()
        assert isinstance(send_message_request, SendMessage)
        assert send_message_request.chat_id == other_user_id
        assert send_message_request.text == f'Планета planet перевела вам {message.text} 💵!'

        edit_message_request = mock_bot.get_request()
        assert isinstance(edit_message_request, EditMessageText)
        assert edit_message_request.chat_id == other_user_id

        edit_message_request = mock_bot.get_request()
        assert isinstance(edit_message_request, EditMessageText)
        assert edit_message_request.chat_id == user_id

        mock_answer.assert_awaited_once_with('Перевод планете other_planet успешно выполнен!')

        state = await fsm_context.get_state()
        assert state is None
