from aiogram import Bot
from aiogram.types import FSInputFile

from app.notifier import Notifier
from app.pivot_table import make_pivot_table
from database.clients.game import GameClient
from database.clients.info import InfoClient
from database.schemas import GameDto, PlanetDto
from game.config import game_config
from keyboards import keyboards as kb
from messages import messager
from storage.clients.actions import ActionsClient
from storage.clients.messages import MessagesClient


async def middle_handler(
    bot: Bot,
    game: GameDto,
    game_client: GameClient,
    message: str,
):
    active_players = await game_client.get_all_active_players(game.id)
    active_admins = await game_client.get_all_active_admins(game.id)
    for user in active_admins + active_players:
        await bot.send_message(user.tg_id, message)


async def end_handler(
    bot: Bot,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    info_client: InfoClient,
    messages_client: MessagesClient,
):
    all_planets: list[PlanetDto] = await game_client.get_all_planets_in_game(game.id)
    orders = {
        planet.id : actions_client.get_order_info(planet.id) 
        for planet in all_planets
    }

    all_players = await game_client.get_all_active_players(game.id)
    for player in all_players:
        messages = messages_client.find_all_messages(player.tg_id)
        await bot.delete_messages(player.tg_id, messages)
        messages_client.delete_all_messages(player.tg_id)
        await bot.send_message(
            player.tg_id,
            messager.round_end(game.round),
            parse_mode='MarkdownV2',
        )
    
    await game_client.end_current_round(game.id, orders)
    
    all_admins = await game_client.get_all_active_admins(game.id)
    for admin in all_admins:
        await bot.send_message(
            admin.tg_id,
            messager.admin_round_end(game.round),
            reply_markup=kb.round_stats_keyboard(game),
        )
    
    if game.round != game_config.ROUND_NUM:
        return
    
    all_cities = []
    for planet in all_planets:
        cities = await game_client.get_cities_of_planet(planet.id, False, False)
        all_cities.extend(cities)
    game_orders_info = await info_client.get_all_orders_in_game(game.id)
    make_pivot_table(
        f'tmp/excel/game_{game.id}_results.xlsx',
        all_planets,
        all_cities,
        game_orders_info,
    )

    for admin in all_admins:
        await bot.send_document(
            admin.tg_id,
            FSInputFile(
                f'tmp/excel/game_{game.id}_results.xlsx',
                filename='Результаты игры'
            ),
            caption=messager.game_results()
        )
    
    for player in all_players:
        await bot.send_message(
            player.tg_id,
            messager.end_of_the_game(),
            parse_mode='MarkdownV2'
        )

        await bot.send_message(player.tg_id, messager.goodbye())
    
    await game_client.end_game(game.id)

    
def get_round_notifier(
    bot: Bot,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    info_client: InfoClient,
    messages_client: MessagesClient,
) -> Notifier:
    return Notifier(
        checkpoints={
            game_config.ROUND_LENGTH // 2: 'middle_5',
            game_config.ROUND_LENGTH * 9 // 10: 'middle_9',
            game_config.ROUND_LENGTH: 'end',
        },
        handlers={
            'middle_5': middle_handler,
            'middle_9': middle_handler,
            'end': end_handler
        },
        handler_args={
            'middle_5': (bot, game, game_client, messager.fivemin()),
            'middle_9': (bot, game, game_client, messager.onemin()),
            'end': (bot, game, game_client, actions_client, info_client, messages_client)
        }
    )
