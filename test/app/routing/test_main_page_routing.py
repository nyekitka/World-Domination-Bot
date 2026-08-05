import asyncio
from unittest.mock import AsyncMock

import pytest
from pytest_lazy_fixtures import lf

from app.handlers.main_page import (
    accept_knight,
    fire_admin,
    refuse_knight,
    request,
    start,
    main_page_router,
)


@pytest.mark.parametrize('message_update', ['/start'], indirect=['message_update'])
@pytest.mark.asyncio
async def test_start_routing(
    message_update, dispatcher, mock_bot, user_client, mock_session, patch_handler
):
    handler_mock = patch_handler(main_page_router, start)

    await dispatcher.feed_update(
        mock_bot,
        message_update,
        user_client=user_client,
        session=mock_session,
    )

    handler_mock.assert_awaited_once()


@pytest.mark.parametrize(
    ('message_update', 'is_admin'),
    [('/request', True), ('/request', False)],
    indirect=['message_update'],
)
@pytest.mark.asyncio
async def test_request_routing(
    message_update,
    dispatcher,
    mocker,
    mock_bot,
    user_client,
    mock_session,
    is_admin,
    user_id,
    patch_handler,
):
    mocker.patch.object(user_client, 'is_user_admin', return_value=is_admin)

    handler_mock = patch_handler(main_page_router, request)

    await dispatcher.feed_update(
        mock_bot,
        message_update,
        user_client=user_client,
        session=mock_session,
        owner_id=user_id,
    )

    if is_admin:
        handler_mock.assert_not_awaited()
    else:
        handler_mock.assert_awaited_once()


@pytest.mark.parametrize(
    ('call_update', 'owner_id'),
    [
        ('accept_knight 1', lf('user_id')),
        ('accept_knight 1', lf('other_user_id')),
        ('acc 1', lf('user_id')),
    ],
    indirect=['call_update'],
)
@pytest.mark.asyncio
async def test_accept_knight_routing(
    call_update,
    dispatcher,
    mock_bot,
    user_client,
    mock_session,
    owner_id,
    patch_handler,
):

    handler_mock = patch_handler(main_page_router, accept_knight, 'callback_query')

    await dispatcher.feed_update(
        mock_bot,
        call_update,
        user_client=user_client,
        session=mock_session,
        owner_id=owner_id,
    )

    if (
        call_update.callback_query.from_user.id == owner_id
        and call_update.callback_query.data.startswith('accept_knight')
    ):
        handler_mock.assert_awaited_once()
    else:
        handler_mock.assert_not_awaited()


@pytest.mark.parametrize(
    ('call_update', 'owner_id'),
    [
        ('refuse_knight 1', lf('user_id')),
        ('refuse_knight 1', lf('other_user_id')),
        ('ref 1', lf('user_id')),
    ],
    indirect=['call_update'],
)
@pytest.mark.asyncio
async def test_refuse_knight_routing(
    call_update,
    dispatcher,
    mock_bot,
    user_client,
    mock_session,
    owner_id,
    patch_handler,
):

    handler_mock = patch_handler(main_page_router, refuse_knight, 'callback_query')

    await dispatcher.feed_update(
        mock_bot,
        call_update,
        user_client=user_client,
        session=mock_session,
        owner_id=owner_id,
    )

    if (
        call_update.callback_query.from_user.id == owner_id
        and call_update.callback_query.data.startswith('refuse_knight')
    ):
        handler_mock.assert_awaited_once()
    else:
        handler_mock.assert_not_awaited()


@pytest.mark.parametrize(
    ('message_update', 'owner_id'),
    [
        ('/fire @nyekitka', lf('user_id')),
        ('/fire @nyekitka', lf('other_user_id')),
        ('/fir', lf('user_id')),
    ],
    indirect=['message_update'],
)
@pytest.mark.asyncio
async def test_fire_admin_routing(
    message_update,
    dispatcher,
    mock_bot,
    user_client,
    mock_session,
    owner_id,
    patch_handler,
):

    handler_mock = patch_handler(main_page_router, fire_admin)

    await dispatcher.feed_update(
        mock_bot,
        message_update,
        user_client=user_client,
        session=mock_session,
        owner_id=owner_id,
    )

    if (
        message_update.message.from_user.id == owner_id
        and message_update.message.text.startswith('/fire')
    ):
        handler_mock.assert_awaited_once()
    else:
        handler_mock.assert_not_awaited()
