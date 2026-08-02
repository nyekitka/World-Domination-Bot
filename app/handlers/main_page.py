import logging

from aiogram import Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.admin import AdminFilter, OwnerFilter
from app.filters.buttons import InlineButtonFilter
from app.utils import tag_person, method_executor_call, method_executor_msg
from database.clients import UserClient
from database.schemas import (
    AdminDto, UserDto
)
from keyboards import keyboards as kb
from messages import messager


main_page_router = Router()
logger = logging.getLogger(__name__)


@main_page_router.message(Command('help'))
async def help(message: types.Message):
    with open('./presets/help.txt', 'r', encoding='UTF-8') as file:
        text = ''.join(file.readlines())
        await message.answer(text=text, parse_mode=ParseMode.MARKDOWN_V2)


@main_page_router.message(CommandStart())
async def start(
    message: types.Message,
    user_client: UserClient,
    session: AsyncSession,
):
    logger.info(
        'main_page_router.start: User id=%s is starting the bot',
        message.from_user.id
    )
    tg_id = message.from_user.id
    user: UserDto | None = await user_client.get_user(session, tg_id)
    if user is None:
        await user_client.make_new_user(session, tg_id, False)
        await message.answer(
            messager.start_msg(False, False, message.from_user.first_name),
            reply_markup=kb.start_keyboard(False),
        )
    else:
        is_admin = isinstance(user, AdminDto)
        keyboard = (
            kb.start_keyboard(is_admin)
            if user.game_id is None
            else kb.ingame_keyboard(is_admin)
        )
        await message.answer(
            messager.start_msg(
                is_admin, user.game_id is not None,
                message.from_user.first_name
            ),
            reply_markup=keyboard,
        )


@main_page_router.message(
    Command('request'),
    ~AdminFilter()
)
async def request(
    message: types.Message,
    owner_id: int,
):
    logger.info(
        'main_page_router.request: User id=%s is requesting to become an admin',
        message.from_user.id
    )
    user_id = message.from_user.id
    await message.answer(messager.request_for_user())
    await message.bot.send_message(
        owner_id,
        messager.request_for_leader(tag_person(message.from_user.full_name, user_id)),
        reply_markup=kb.request_keyboard(user_id),
        parse_mode=ParseMode.MARKDOWN_V2,
    )


@main_page_router.callback_query(
    InlineButtonFilter('accept_knight'),
    OwnerFilter()
)
async def accept_knight(
    call: types.CallbackQuery,
    user_client: UserClient,
    session: AsyncSession,
):
    logger.info(
        'main_page_router.accept_knight: Owner id=%s is accepting an admin request from user id=%s',
        call.from_user.id, call.data.split()[1]
    )
    id = int(call.data.split()[1])
    user = await call.bot.get_chat(id)
    res = await method_executor_call(user_client.promote_to_admin, call, session, id)
    if res:
        await call.message.answer(messager.knighting_for_leader(user.full_name))
        await call.bot.send_message(id, messager.knight())


@main_page_router.callback_query(
    InlineButtonFilter('refuse_knight'),
    OwnerFilter()
)
async def refuse_knight(
    call: types.CallbackQuery,
):
    logger.info(
        'main_page_router.refuse_knight: Owner id=%s is refusing an admin request from user id=%s',
        call.from_user.id, call.data.split()[1]
    )
    await call.answer()
    id = int(call.data.split()[1])
    user = await call.bot.get_chat(id)
    await call.message.answer(messager.notknight_for_leader(user.full_name))
    await call.bot.send_message(id, messager.notknight())


@main_page_router.message(
    Command('fire'),
    OwnerFilter()
)
async def fire_admin(
    message: types.Message,
    command: CommandObject,
    user_client: UserClient,
    session: AsyncSession,
):
    username = command.args.strip()
    if not username.startswith('@'):
        return
    logger.info(
        'main_page_router.fire_admin: Owner id=%s is firing an admin with username=%s',
        message.from_user.id, username
    )
    user = await message.bot.get_chat(username)
    db_user = await user_client.get_user(session, user.id)
    was_in_game = db_user.game_id is not None
    res = await method_executor_msg(
        message.bot, user_client.fire_admin,
        message.from_user.id, session, user.id
    )
    if not res:
        return
    
    await message.bot.send_message(user.id, messager.unknight())
    if was_in_game:
        await message.bot.send_message(user.id, messager.kick_due_to_not_admin())
    await message.answer(messager.unknighting_for_leader(user.first_name))
