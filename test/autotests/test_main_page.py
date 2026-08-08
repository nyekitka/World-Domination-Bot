from aiogram.methods import AnswerCallbackQuery, GetChat, SendMessage
from aiogram.types import ChatFullInfo
import pytest
import pytest_asyncio
from pytest_lazy_fixtures import lf
from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import bot_config
from database.models import Admin, Game, ModelBase, Player
from database.schemas import GameStatus
from keyboards import keyboards as kb


@pytest_asyncio.fixture
async def session(
    admin_user, owner_user,
    user1, user2,
    test_db_config
):
    with DatabaseJanitor(
        user=test_db_config['user'],
        dbname=test_db_config['name'],
        host=test_db_config['host'],
        port=test_db_config['port'],
        password=test_db_config['password'],
        version=test_db_config['version'],
    ) as j:
        engine = create_async_engine(
            f'postgresql+asyncpg://{j.user}:{j.password}@{j.host}:{j.port}/{j.dbname}',
        )
        session = async_sessionmaker(engine)
        async with engine.begin() as conn:
            await conn.run_sync(ModelBase.metadata.drop_all)
            await conn.run_sync(ModelBase.metadata.create_all)

        admin = Admin(tg_id=admin_user.id)
        owner = Admin(tg_id=owner_user.id)
        player1 = Player(tg_id=user1.id)
        player2 = Player(tg_id=user2.id)

        async with session() as s:
            s.add_all((
                admin, owner,
                player1, player2,
            ))
            await s.commit()

        async with session() as s:
            yield s


@pytest.mark.parametrize(
    ('is_logged', 'user', 'chat', 'is_admin'),
    [
        (False, lf('user1'), lf('chat1'), False),
        (True, lf('user1'), lf('chat1'), False),
        (True, lf('admin_user'), lf('admin_chat'), True),
    ]
)
@pytest.mark.asyncio
async def test_start_player(
    chat, user, is_logged, session, dispatcher,
    mock_bot, get_message, get_message_update,
    renderer, user_client, is_admin
):
    if not is_logged:
        await session.execute(
            delete(Player)
            .where(Player.tg_id == chat.id)
        )
        await session.commit()

    message = get_message(message_text='/start', chat=chat, user=user)
    await dispatcher.feed_update(
        mock_bot,
        get_message_update(message),
        renderer=renderer,
        user_client=user_client,
        session=session,
    )

    request = mock_bot.get_request()

    assert isinstance(request, SendMessage)
    assert request.text == renderer.render(
        'on_start',
        is_admin=is_admin,
        user={'game_id': None, 'tg_id': chat.id},
        name=chat.first_name,
    )['text']
    assert request.reply_markup == kb.get_reply_markup_keyboard(is_admin, False)
    assert request.chat_id == chat.id

    if not is_admin:
        player = await session.get(Player, chat.id)
        assert player is not None
    else:
        admin = await session.get(Admin, chat.id)
        assert admin is not None


@pytest.mark.parametrize(
    ('user', 'handler_called'),
    [
        (lf('user1'), True),
        (lf('admin_user'), False)
    ]
)
@pytest.mark.asyncio
async def test_request(
    user, handler_called, dispatcher,
    mock_bot, get_message, get_message_update,
    renderer, session, user_client,
):
    message = get_message(
        message_text='/request',
        user=user,
    )
    await dispatcher.feed_update(
        mock_bot,
        get_message_update(message),
        renderer=renderer,
        owner_id=bot_config.OWNER,
        session=session,
        user_client=user_client,
    )
    if handler_called:
        mock_bot.assert_method_called(
            SendMessage,
            text=renderer.render(
                'request_notification_for_user',
            )['text'],
            chat_id=user.id,
        )
        mock_bot.assert_method_called(
            SendMessage,
            text=renderer.render(
                'request_notification_for_leader',
                user=user,
            )['text'],
            chat_id=bot_config.OWNER,
        )
    else:
        mock_bot.assert_method_not_called(SendMessage)


@pytest.mark.parametrize(
    ('game', 'user', 'chat', 'is_admin', 'message_key', 'success'),
    [
        (
            Game(id=1, status=GameStatus.WAITING),
            lf('user1'), lf('chat1'), False, 'promote_notification_for_leader', True,
        ),
        (
            Game(id=1, status=GameStatus.ROUND, round=1), lf('user1'),
            lf('chat1'), False, 'wait_till_game_ends', False,
        ),
        (
            Game(id=1), lf('admin_user'), lf('admin_chat'),
            True, 'object_not_found', False,
        )
    ]
)
@pytest.mark.asyncio
async def test_accept_knight(
    user, owner_user, owner_chat,
    dispatcher, game, success,
    mock_bot, get_call, get_call_update,
    is_admin, renderer, session, user_client,
    message_key, chat, get_chat_full_info_for_chat,
):
    session.add(game)
    db_user = await session.get(
        Admin if is_admin else Player,
        user.id,
    )
    db_user.game_id = game.id
    await session.commit()

    mock_bot.add_result_for(
        GetChat,
        get_chat_full_info_for_chat(chat),
    )
    call = get_call(
        user=owner_user,
        call_data=f'accept_request {user.id}',
        chat=owner_chat,
        
    )
    await dispatcher.feed_update(
        mock_bot, get_call_update(call),
        user_client=user_client,
        session=session,
        renderer=renderer,
        owner_id=int(bot_config.OWNER),
    )

    
    if success:
        mock_bot.assert_method_called(
            SendMessage,
            chat_id=user.id,
            text=renderer.render('promote_notification_for_user')['text']
        )
        mock_bot.assert_method_called(
            SendMessage,
            chat_id=owner_chat.id,
            text=renderer.render(message_key, user=user)['text'],
        )
    else:
        mock_bot.assert_method_called(
            AnswerCallbackQuery,
            text=renderer.render(message_key, user=user)['text'],
            callback_query_id=call.id,
        )
