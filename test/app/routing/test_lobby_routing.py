import pytest
from pytest_lazy_fixtures import lf

from app.filters.state import BotStates
from app.handlers.lobby import (
    chosen_lobby,
    chosen_lobby_admin,
    create_game,
    enter_game_player,
    leave_lobby,
    lobby_router,
    set_number_of_planets,
    set_pack,
)


@pytest.mark.parametrize(
    ('message_update', 'is_admin'),
    [('Создать лобби', True), ('Создать лобби', False)],
    indirect=['message_update'],
)
@pytest.mark.asyncio
async def test_create_game_routing(
    message_update,
    dispatcher,
    mocker,
    mock_bot,
    user_client,
    fsm_context,
    patch_handler,
    is_admin,
    mock_session,
):
    mocker.patch.object(user_client, 'is_user_admin', return_value=is_admin)
    handler_mock = patch_handler(lobby_router, create_game)

    await dispatcher.feed_update(
        mock_bot,
        message_update,
        state=fsm_context,
        user_client=user_client,
        session=mock_session,
    )

    if is_admin:
        handler_mock.assert_awaited_once()
    else:
        handler_mock.assert_not_awaited()


@pytest.mark.parametrize(
    ('call_update', 'state'),
    [
        ('solar', None),
        ('solar', BotStates.choose_pack),
        ('solar', BotStates.planets_numbers),
    ],
    indirect=['call_update'],
)
@pytest.mark.asyncio
async def test_set_pack_routing(
    call_update, fsm_context, state, patch_handler, dispatcher, mock_bot
):
    handler_mock = patch_handler(lobby_router, set_pack, 'callback_query')
    patch_handler(lobby_router, set_number_of_planets, 'callback_query')
    await dispatcher.fsm.storage.set_state(fsm_context.key, state)

    await dispatcher.feed_update(
        mock_bot,
        call_update,
    )

    if state == BotStates.choose_pack:
        handler_mock.assert_awaited_once()
    else:
        handler_mock.assert_not_awaited()

    await dispatcher.fsm.storage.set_state(fsm_context.key, None)


@pytest.mark.parametrize(
    ('call_update', 'state'),
    [
        ('5,solar', None),
        ('5,solar', BotStates.choose_pack),
        ('5,solar', BotStates.planets_numbers),
    ],
    indirect=['call_update'],
)
@pytest.mark.asyncio
async def test_set_number_of_planets_routing(
    call_update, fsm_context, state, patch_handler, dispatcher, mock_bot
):
    handler_mock = patch_handler(lobby_router, set_number_of_planets, 'callback_query')
    patch_handler(lobby_router, set_pack, 'callback_query')
    await dispatcher.fsm.storage.set_state(fsm_context.key, state)

    await dispatcher.feed_update(
        mock_bot,
        call_update,
    )

    if state == BotStates.planets_numbers:
        handler_mock.assert_awaited_once()
    else:
        handler_mock.assert_not_awaited()

    await dispatcher.fsm.storage.set_state(fsm_context.key, None)


@pytest.mark.parametrize(
    'message_update', ['Войти в лобби'], indirect=['message_update']
)
@pytest.mark.asyncio
async def test_enter_game_player_routing(
    message_update,
    dispatcher,
    mock_bot,
    user_client,
    patch_handler,
    game_client,
    mock_session,
):
    handler_mock = patch_handler(lobby_router, enter_game_player)

    await dispatcher.feed_update(
        mock_bot,
        message_update,
        user_client=user_client,
        game_client=game_client,
        session=mock_session,
    )

    handler_mock.assert_awaited_once()


@pytest.mark.parametrize(
    'message_update', ['Выйти из лобби'], indirect=['message_update']
)
@pytest.mark.asyncio
async def test_leave_lobby_routing(
    message_update,
    dispatcher,
    mock_bot,
    user_client,
    messages_client,
    patch_handler,
    game_client,
    mock_session,
):
    handler_mock = patch_handler(lobby_router, leave_lobby)

    await dispatcher.feed_update(
        mock_bot,
        message_update,
        messages_client=messages_client,
        user_client=user_client,
        game_client=game_client,
        session=mock_session,
    )

    handler_mock.assert_awaited_once()


@pytest.mark.parametrize(
    ('call_update', 'state'),
    [
        ('5', None),
        ('5', BotStates.choose_lobby_admin),
        ('5', BotStates.choose_lobby),
    ],
    indirect=['call_update'],
)
@pytest.mark.asyncio
async def test_chosen_lobby_admin_routing(
    call_update, fsm_context, state, patch_handler, dispatcher, mock_bot
):
    handler_mock = patch_handler(lobby_router, chosen_lobby_admin, 'callback_query')
    patch_handler(lobby_router, chosen_lobby, 'callback_query')
    await dispatcher.fsm.storage.set_state(fsm_context.key, state)

    await dispatcher.feed_update(
        mock_bot,
        call_update,
    )

    if state == BotStates.choose_lobby_admin:
        handler_mock.assert_awaited_once()
    else:
        handler_mock.assert_not_awaited()

    await dispatcher.fsm.storage.set_state(fsm_context.key, None)


@pytest.mark.parametrize(
    ('call_update', 'state'),
    [
        ('5', None),
        ('5', BotStates.choose_lobby_admin),
        ('5', BotStates.choose_lobby),
    ],
    indirect=['call_update'],
)
@pytest.mark.asyncio
async def test_chosen_lobby_routing(
    call_update, fsm_context, state, patch_handler, dispatcher, mock_bot
):
    handler_mock = patch_handler(lobby_router, chosen_lobby, 'callback_query')
    patch_handler(lobby_router, chosen_lobby_admin, 'callback_query')
    await dispatcher.fsm.storage.set_state(fsm_context.key, state)

    await dispatcher.feed_update(
        mock_bot,
        call_update,
    )

    if state == BotStates.choose_lobby:
        handler_mock.assert_awaited_once()
    else:
        handler_mock.assert_not_awaited()

    await dispatcher.fsm.storage.set_state(fsm_context.key, None)
