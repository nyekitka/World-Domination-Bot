import logging

from aiogram import Router, types
from aiogram.filters import Command, CommandObject, CommandStart
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.admin import AdminFilter, OwnerFilter
from app.filters.buttons import InlineButtonFilter
from app.utils import method_executor_call, method_executor_msg
from database.clients import UserClient
from database.schemas import AdminDto, UserDto
from game.config import game_config
from keyboards import keyboards as kb
from messages.renderer import MessageRenderer

main_page_router = Router()
logger = logging.getLogger(__name__)


@main_page_router.message(Command('help'))
async def help(
    message: types.Message,
    renderer: MessageRenderer,
):
    await message.answer(
        **renderer.render('help', game_config=game_config),
    )


@main_page_router.message(CommandStart())
async def start(
    message: types.Message,
    user_client: UserClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    logger.info(
        'main_page_router.start: User id=%s is starting the bot', message.from_user.id
    )
    name = message.from_user.first_name
    tg_id = message.from_user.id
    user: UserDto | None = await user_client.get_user(session, tg_id)
    if user is None:
        user = await user_client.make_new_user(session, tg_id, False)

    is_admin = isinstance(user, AdminDto)

    await message.answer(
        **renderer.render('on_start', is_admin=is_admin, user=user, name=name),
        reply_markup=kb.get_reply_markup_keyboard(is_admin, user.game_id is not None),
    )


@main_page_router.message(Command('request'), ~AdminFilter())
async def request(
    message: types.Message,
    owner_id: int,
    renderer: MessageRenderer,
):
    logger.info(
        'main_page_router.request: User id=%s is requesting to become an admin',
        message.from_user.id,
    )
    user_id = message.from_user.id
    await message.answer(**renderer.render('request_notification_for_user'))
    await message.bot.send_message(
        owner_id,
        **renderer.render('request_notification_for_leader', user=message.from_user),
        reply_markup=kb.request_keyboard(user_id),
    )


@main_page_router.callback_query(InlineButtonFilter('accept_request'), OwnerFilter())
async def accept_knight(
    call: types.CallbackQuery,
    user_client: UserClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    logger.info(
        'main_page_router.accept_knight: Owner id=%s is accepting an admin request from user id=%s',
        call.from_user.id,
        call.data.split()[1],
    )
    id = int(call.data.split()[1])
    user = await call.bot.get_chat(id)
    res = await method_executor_call(
        user_client.promote_to_admin, call, renderer, session, id
    )
    if res:
        await call.message.answer(
            **renderer.render('promote_notification_for_leader', user=user)
        )
        await call.bot.send_message(
            id, **renderer.render('promote_notification_for_user'),
            reply_markup=kb.get_reply_markup_keyboard(True, False)
        )


@main_page_router.callback_query(InlineButtonFilter('refuse_request'), OwnerFilter())
async def refuse_knight(
    call: types.CallbackQuery,
    renderer: MessageRenderer,
):
    logger.info(
        'main_page_router.refuse_knight: Owner id=%s is refusing an admin request from user id=%s',
        call.from_user.id,
        call.data.split()[1],
    )
    await call.answer()
    id = int(call.data.split()[1])
    user = await call.bot.get_chat(id)
    await call.message.answer(
        **renderer.render('refuse_request_notification_for_leader', user=user)
    )
    await call.bot.send_message(
        id, **renderer.render('refuse_request_notification_for_user')
    )


@main_page_router.message(Command('fire'), OwnerFilter())
async def fire_admin(
    message: types.Message,
    command: CommandObject,
    user_client: UserClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    username = command.args.strip()
    if not username.startswith('@'):
        return
    logger.info(
        'main_page_router.fire_admin: Owner id=%s is firing an admin with username=%s',
        message.from_user.id,
        username,
    )
    admins = await user_client.get_all_admins(session)
    tg_admin = None
    db_admin = None
    for admin in admins:
        tg_user = await message.bot.get_chat(admin.tg_id)
        if tg_user.username == username[1:]:
            tg_admin = tg_user
            db_admin = admin
            break
    else:
        await message.answer(**renderer.render('object_not_found'))
        return
    
    was_in_game = db_admin.game_id is not None
    res = await method_executor_msg(
        message.bot,
        user_client.fire_admin,
        message.from_user.id,
        renderer,
        session,
        tg_admin.id,
    )
    if not res:
        return

    await message.bot.send_message(
        tg_admin.id, **renderer.render('fire_admin_notification_for_user'),
        reply_markup=kb.get_reply_markup_keyboard(False, False)
    )
    if was_in_game:
        await message.bot.send_message(
            tg_admin.id, **renderer.render('kick_due_to_not_admin')
        )
    await message.answer(
        **renderer.render('fire_admin_notification_for_leader', user=tg_admin)
    )
