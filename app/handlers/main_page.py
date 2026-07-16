from aiogram import Router, types
from aiogram.filters import Command, CommandStart, CommandObject

from app.utils import tag_person, method_executor_call, method_executor_msg
from database.clients import UserClient
from database.schemas import (
    AdminDto, UserDto
)
from filters.admin import AdminFilter, OwnerFilter
from filters.buttons import InlineButtonFilter
import keyboards as kb
from messages import messager


main_page_router = Router()


@main_page_router.message(Command('help'))
async def help(message: types.Message):
    with open('./presets/help.txt', 'r', encoding='UTF-8') as file:
        text = ''.join(file.readlines())
        await message.answer(text=text, parse_mode='MarkdownV2')


@main_page_router.message(CommandStart())
async def start(
    message: types.Message,
    user_client: UserClient,
):
    tg_id = message.from_user.id
    user: UserDto | None = await user_client.get_user(tg_id)
    if user is None:
        await user_client.make_new_user(tg_id, False)
        await message.answer(
            messager.start_msg(False, False, message.from_user.first_name),
            reply_markup=kb.start_keyboard(False),
        )
    else:
        is_admin = isinstance(user, AdminDto)
        await message.answer(
            messager.start_msg(
                is_admin, user.game_id is not None,
                message.from_user.first_name
            ),
            reply_markup=kb.start_keyboard(is_admin),
        )


@main_page_router.message(
    Command('request'),
    ~AdminFilter()
)
async def request(
    message: types.Message,
    owner_id: int,
):
    user_id = message.from_user.id
    await message.answer(messager.request_for_user())
    await message.bot.send_message(
        owner_id,
        messager.request_for_leader(tag_person(message.from_user.full_name, user_id)),
        reply_markup=kb.request_keyboard(user_id),
        parse_mode='MarkdownV2',
    )


@main_page_router.callback_query(
    InlineButtonFilter('accept_knight'),
    OwnerFilter()
)
async def accept_knight(
    call: types.CallbackQuery,
    user_client: UserClient,
):
    id = int(call.data.split()[1])
    user = await call.bot.get_chat(id)
    res = await method_executor_call(user_client.promote_to_admin, call, id)
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
    call.answer()
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
):
    username = command.args.strip()
    if not username.startswith('@'):
        return
    user = await message.bot.get_chat(username)
    db_user = await user_client.get_user(user.id)
    was_in_game = db_user.game_id is None
    res = await method_executor_msg(
        message.bot, user_client.fire_admin,
        message.from_user.id, user.id
    )
    if not res:
        return
    
    await message.bot.send_message(user.id, messager.unknight())
    if was_in_game:
        await message.bot.send_message(user.id, messager.kick_due_to_admin())
    await message.answer(messager.unknighting_for_leader(user.first_name))
