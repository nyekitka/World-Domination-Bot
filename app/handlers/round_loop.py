from datetime import timedelta

from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifier import Notifier
from app.pivot_table import make_pivot_table
from database.clients.game import GameClient
from database.clients.info import InfoClient
from database.schemas import GameDto, PlanetDto
from game.config import game_config
from keyboards import keyboards as kb
from messages.renderer import MessageRenderer
from storage.clients.actions import ActionsClient
from storage.clients.messages import MessagesClient


async def middle_handler(
    bot: Bot,
    game: GameDto,
    game_client: GameClient,
    message: dict[str, str | None],
    session: AsyncSession,
):
    active_players = await game_client.get_all_active_players(session, game.id)
    active_admins = await game_client.get_all_active_admins(session, game.id)

    for user in active_admins + active_players:
        await bot.send_message(user.tg_id, **message)


async def end_handler(
    bot: Bot,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    info_client: InfoClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    renderer: MessageRenderer,
):
    all_planets: list[PlanetDto] = await game_client.get_planets_of_game(
        session, game.id
    )
    orders = {
        planet.id: actions_client.get_order_info(planet.id) for planet in all_planets
    }
    for planet in all_planets:
        actions_client.clear_order_info(planet.id)

    for planet in all_planets:
        current_money = actions_client.get_balance(planet.id, actions_client.MONEY_KEY)
        current_meteorites = actions_client.get_balance(
            planet.id, actions_client.METEORITES_KEY
        )
        await game_client.update_planet_balance(
            session, planet.id, current_money, current_meteorites
        )

    all_players = await game_client.get_all_active_players(session, game.id)
    for player in all_players:
        messages = messages_client.find_all_messages(player.tg_id)
        await bot.delete_messages(player.tg_id, messages)
        messages_client.delete_all_messages(player.tg_id)
        await bot.send_message(
            player.tg_id,
            **renderer.render(
                'round_end_for_players',
                game=game,
            ),
        )

    await game_client.end_current_round(session, game.id, orders)
    await game_client.save_round_info(session, game.id)

    all_admins = await game_client.get_all_active_admins(session, game.id)
    for admin in all_admins:
        await bot.send_message(
            admin.tg_id,
            **renderer.render(
                'round_end_for_admin',
                game=game,
            ),
            reply_markup=kb.round_stats_keyboard(game, admin),
        )

    await session.commit()
    if game.round != game_config.ROUND_NUM:
        await session.close()
        return

    all_cities = []
    for planet in all_planets:
        cities = await game_client.get_cities_of_planet(
            session, planet.id, False, False
        )
        all_cities.extend(cities)

    game_orders_info = await info_client.get_all_orders_in_game(session, game.id)

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
                f'tmp/excel/game_{game.id}_results.xlsx', filename='Результаты игры.xlsx'
            ),
            caption=renderer.render('game_results')['text'],
            reply_markup=kb.start_keyboard(True),
        )

    for player in all_players:
        await bot.send_message(
            player.tg_id,
            **renderer.render('end_of_the_game'),
        )
        await bot.send_message(
            player.tg_id,
            **renderer.render('goodbye'),
            reply_markup=kb.start_keyboard(False)
        )

    await game_client.end_game(session, game.id)
    await session.commit()


def get_round_notifier(
    bot: Bot,
    game: GameDto,
    game_client: GameClient,
    actions_client: ActionsClient,
    info_client: InfoClient,
    messages_client: MessagesClient,
    session: AsyncSession,
    renderer: MessageRenderer,
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
            'end': end_handler,
        },
        handler_args={
            'middle_5': (
                bot,
                game,
                game_client,
                renderer.render(
                    'half_time_passed',
                    time=timedelta(seconds=game_config.ROUND_LENGTH // 2),
                ),
                session,
            ),
            'middle_9': (
                bot,
                game,
                game_client,
                renderer.render(
                    'hurry_up', time=timedelta(seconds=game_config.ROUND_LENGTH // 10)
                ),
                session,
            ),
            'end': (
                bot,
                game,
                game_client,
                actions_client,
                info_client,
                messages_client,
                session,
                renderer,
            ),
        },
    )
