from datetime import timedelta

import pytest

from database.schemas import PlanetDto
from game.config import game_config



def test_render_on_start_for_player_without_game(
    renderer_ru, renderer_en, user_ru, user_en, user_dto_without_game
):
    assert renderer_ru.render(
        'on_start',
        is_admin=False,
        user=user_dto_without_game,
        name=user_ru.first_name,
    ) == {
        'text': (
            'Привет, Иван 👋.\n'
            'Ты не находишься ни в одном из лобби.\n'
            'Чтобы войти в лобби нажми кнопку "Войти в лобби".'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render(
        'on_start',
        is_admin=False,
        user=user_dto_without_game,
        name=user_en.first_name,
    ) == {
        'text': (
            'Hi, Alice 👋.\n'
            "You're not in any lobby.\n"
            'To enter a lobby, press the "Enter lobby" button.'
        ),
        'parse_mode': None,
    }

@pytest.mark.parametrize(
    'is_admin',
    (True, False)
)
def test_render_on_start_for_user_in_game(
    renderer_ru, renderer_en,
    user_ru, user_en,
    user_dto, is_admin
):
    assert renderer_ru.render(
        'on_start',
        name=user_ru.first_name,
        user=user_dto,
        is_admin=is_admin,
    ) == {
        'text': 'С возвращением, Иван!',
        'parse_mode': None,
    }
    assert renderer_en.render(
        'on_start',
        name=user_en.first_name,
        user=user_dto,
        is_admin=is_admin,
    ) == {
        'text': 'Welcome back, Alice!',
        'parse_mode': None,
    }


def test_render_on_start_for_admin_without_game(
    renderer_ru, renderer_en, user_ru, user_en,
    user_dto_without_game
):
    assert renderer_ru.render(
        'on_start',
        name=user_ru.first_name,
        user=user_dto_without_game,
        is_admin=True,
    ) == {
        'text': (
            'Приветствую, Иван 👋.\n'
            'Ты не администрируешь ни одну из игр.\n'
            'Чтобы войти в игру как администратор нажмите кнопку "Войти в лобби".'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render(
            'on_start',
            name=user_en.first_name,
            user=user_dto_without_game,
            is_admin=True,
        ) == {
        'text': (
            'Greetings, Alice 👋.\n'
            'You are not administering any games.\n'
            'To enter a game as an administrator, press the "Enter lobby" button.'
        ),
        'parse_mode': None,
    }


def test_render_on_choose_lobby(renderer_ru, renderer_en):
    assert renderer_ru.render('on_choose_lobby') == {
        'text': 'Выберите игру, в которую вы хотите зайти.',
        'parse_mode': None,
    }
    assert renderer_en.render('on_choose_lobby') == {
        'text': 'Choose the game you want to join.',
        'parse_mode': None,
    }


def test_render_choose_number_of_planets(renderer_ru, renderer_en):
    assert renderer_ru.render('choose_number_of_planets') == {
        'text': 'Выберите количество планет в игре.',
        'parse_mode': None,
    }
    assert renderer_en.render('choose_number_of_planets') == {
        'text': 'Choose the number of planets in the game.',
        'parse_mode': None,
    }


def test_render_no_games_available(renderer_ru, renderer_en):
    assert renderer_ru.render('no_games_available') == {
        'text': 'На данный момент нет ни одной доступной игры.',
        'parse_mode': None,
    }
    assert renderer_en.render('no_games_available') == {
        'text': 'There are no available games at the moment.',
        'parse_mode': None,
    }


def test_render_on_game_created(renderer_ru, renderer_en, game):
    assert renderer_ru.render('on_game_created', game=game) == {
        'text': 'Игра 1 на 4 человек успешно создана.',
        'parse_mode': None,
    }
    assert renderer_en.render('on_game_created', game=game) == {
        'text': 'Game 1 for 4 players has been successfully created.',
        'parse_mode': None,
    }


def test_render_on_success_enter_player(renderer_ru, renderer_en, game, planet):
    assert renderer_ru.render('on_success_enter_player', game=game, planet=planet) == {
        'text': (
            'Вы вошли в игру 1!\n'
            'Ваша планета - Земля.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('on_success_enter_player', game=game, planet=planet) == {
        'text': (
            'You have joined game 1!\n'
            'Your planet is Земля.'
        ),
        'parse_mode': None,
    }


def test_render_on_success_enter_admin(renderer_ru, renderer_en, game):
    assert renderer_ru.render('on_success_enter_admin', game=game) == {
        'text': (
            'Вы присоединились к игре 1.\n'
            'Теперь вам доступна панель администрации игры, а также вся информация о ней.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('on_success_enter_admin', game=game) == {
        'text': (
            'You have joined game 1.\n'
            "You now have access to the game's admin panel and all information about it."
        ),
        'parse_mode': None,
    }


def test_render_player_enter_notification(renderer_ru, renderer_en, planet, game):
    assert renderer_ru.render('player_enter_notification', planet=planet, game=game, current_players=2) == {
        'text': (
            'Команда от планеты Земля присоединилась к нам!\n'
            'В игре: 2/4 👤'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('player_enter_notification', planet=planet, game=game, current_players=2) == {
        'text': (
            'The team from planet Земля has joined us!\n'
            'Players in game: 2/4 👤'
        ),
        'parse_mode': None,
    }


def test_render_player_leave_notification(renderer_ru, renderer_en, planet, game):
    assert renderer_ru.render('player_leave_notification', planet=planet, game=game, current_players=2) == {
        'text': (
            'Команда от планеты Земля вышла из лобби.\n'
            'В игре: 2/4 👤'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('player_leave_notification', planet=planet, game=game, current_players=2) == {
        'text': (
            'The team from planet Земля has left the lobby.\n'
            'Players in game: 2/4 👤'
        ),
        'parse_mode': None,
    }


def test_render_on_leave_lobby(renderer_ru, renderer_en):
    assert renderer_ru.render('on_leave_lobby') == {'text': 'Вы вышли из игры.', 'parse_mode': None}
    assert renderer_en.render('on_leave_lobby') == {'text': 'You have left the game.', 'parse_mode': None}


def test_render_starting_game_not_being_in(renderer_ru, renderer_en):
    assert renderer_ru.render('starting_game_not_being_in') == {
        'text': (
            'Вы не неходитесь ни в какой в игре.\n'
            'Сначала войдите в игру!'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('starting_game_not_being_in') == {
        'text': (
            'You are not in any game.\n'
            'Enter a game first!'
        ),
        'parse_mode': None,
    }


def test_render_not_enough_players(renderer_ru, renderer_en, planet, game):
    assert renderer_ru.render('not_enough_players', planet=planet, game=game, current_players=1) == {
        'text': (
            'Недостаточно игроков в игре (1/4 👤 присоединилось).\n'
            'Подождите пока войдут все, а затем начинайте игру'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('not_enough_players', planet=planet, game=game, current_players=1) == {
        'text': (
            'Not enough players in the game (1/4 👤 joined).\n'
            'Wait until everyone joins, then start the game'
        ),
        'parse_mode': None,
    }


def test_render_half_time_passed(renderer_ru, renderer_en):
    assert renderer_ru.render('half_time_passed', time=timedelta(minutes=5)) == {
        'text': 'Внимание, до конца раунда осталось 5 минут ⏳. Не забывайте заполнить свои приказы.',
        'parse_mode': None,
    }
    assert renderer_en.render('half_time_passed', time=timedelta(minutes=5)) == {
        'text': "Attention, 5 minutes left until the end of the round ⏳. Don't forget to fill in your orders.",
        'parse_mode': None,
    }


def test_render_hurry_up(renderer_ru, renderer_en):
    assert renderer_ru.render('hurry_up', time=timedelta(minutes=2)) == {
        'text': 'Внимание, до конца раунда осталась 2 минуты ⌛. Если ещё не заполнили свои приказы, то самое время это сделать, иначе приказы отправятся пустыми.',
        'parse_mode': None,
    }
    assert renderer_en.render('hurry_up', time=timedelta(minutes=2)) == {
        'text': "Attention, 2 minutes left until the end of the round ⌛. If you haven't filled in your orders yet, now is the time to do it, otherwise they will be submitted empty.",
        'parse_mode': None,
    }


@pytest.mark.parametrize(
    ('round', 'ordinal_ru', 'ordinal_en'),
    [
        (1, 'Первый', 'First'),
        (2, 'Второй', 'Second'),
    ]
)
def test_render_start_round_for_players(
    round, game, renderer_ru, renderer_en,
    ordinal_ru, ordinal_en
):
    game.round = round
    if round == 1:
        assert renderer_ru.render('start_round_for_players', game=game) == {
            'text': (
                f'*{ordinal_ru} раунд начался*\n'
                'В течение этого раунда вы должны обсудить в команде свою стратегию на игру\\.\n'
                'Также вы уже можете вложить деньги в разработку технологии отправки метеоритов для последующей атаки аномалии или чужих городов, либо же вложить их в развитие собственных городов \\(Развитие 📈\\)\\.'
            ),
            'parse_mode': 'MarkdownV2',
        }
        assert renderer_en.render('start_round_for_players', game=game) == {
            'text': (
                f'*{ordinal_en} round has begun*\n'
                "During this round you should discuss your team's strategy for the game\\.\n"
                'You can also invest money in developing meteorite launching technology to later attack the anomaly or other cities, or invest it in developing your own cities \\(Development 📈\\)\\.'
            ),
            'parse_mode': 'MarkdownV2',
        }
    else:
        assert renderer_ru.render('start_round_for_players', game=game,) == {
            'text': (
                f'*{ordinal_ru} раунд начался*\n'
                'У вас есть 10 минут, чтобы обсудить действия в этом раунде как внутри своей команды, так и с другими командами на переговорах\\. Не забывайте заполнять приказ\\!'
            ),
            'parse_mode': 'MarkdownV2',
        }
        assert renderer_en.render('start_round_for_players', game=game) == {
            'text': (
                f'*{ordinal_en} round has begun*\n'
                "You have 10 minutes to discuss your actions for this round, both within your team and with other teams during negotiations\\. Don't forget to fill in your orders\\!"
            ),
            'parse_mode': 'MarkdownV2',
        }

@pytest.mark.parametrize(
    ('round', 'ordinal_ru', 'ordinal_en'),
    [
        (1, 'Первый', 'First'),
        (2, 'Второй', 'Second'),
    ]
)
def test_render_start_round_for_admins(
    game, round, renderer_ru, renderer_en,
    ordinal_ru, ordinal_en
):
    game.round = round
    if round == 1:
        assert renderer_ru.render('start_round_for_admins', game=game) == {
            'text': f'*{ordinal_ru} раунд начался*',
            'parse_mode': 'MarkdownV2',
        }
        assert renderer_en.render('start_round_for_admins', game=game) == {
            'text': f'*{ordinal_en} round has begun*',
            'parse_mode': 'MarkdownV2',
        }
    else:
        assert renderer_ru.render('start_round_for_admins', game=game) == {
            'text': (
                f'*{ordinal_ru} раунд начался*\n\n'
                'Вам будут приходить запросы на переговоры от игроков\\.\n'
                'Как только придёт запрос, направляйтесь к команде, отправившей запрос и сопроводите дипломата до другой команды\\.'
            ),
            'parse_mode': 'MarkdownV2',
        }
        assert renderer_en.render('start_round_for_admins', game=game) == {
            'text': (
                f'*{ordinal_en} round has begun*\n\n'
                'You will receive negotiation requests from players\\.\n'
                'As soon as a request comes in, head to the team that sent it and escort the diplomat to the other team\\.'
            ),
            'parse_mode': 'MarkdownV2',
        }


def test_render_common_planet_info(renderer_ru, renderer_en, planet, cities):
    assert renderer_ru.render('common_planet_info', planet=planet, cities=cities) == {
        'text': (
            '__*Земля*__\n\n'
            '*Доступный бюджет:* _1000_ 💵\n'
            '*Сред\\. ур\\. жизни на планете:* _45\\.5%_\n\n'
            '*Москва* ❌:\n'
            'Развитие 0%, Ур\\. жизни 50\\.0%, Доход 150\\.0 💵\n\n'
            '*Питер* 🛡️:\n'
            'Развитие 70%, Ур\\. жизни 80\\.0%, Доход 240\\.0 💵\n\n'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('common_planet_info', planet=planet, cities=cities) == {
        'text': (
            '__*Земля*__\n\n'
            '*Available budget:* _1000_ 💵\n'
            '*Avg\\. life rate on the planet:* _45\\.5%_\n\n'
            '*Москва* ❌:\n'
            'Development 0%, Life rate 50\\.0%, Income 150\\.0 💵\n\n'
            '*Питер* 🛡️:\n'
            'Development 70%, Life rate 80\\.0%, Income 240\\.0 💵\n\n'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_sanctions_info_with_sanctions(renderer_ru, renderer_en):
    assert renderer_ru.render('sanctions_info', sanctioned_planets=['Марс', 'Юпитер']) == {
        'text': (
            '*Санкции:*\n'
            '_На вас наложили санкции: Марс, Юпитер_'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('sanctions_info', sanctioned_planets=['Mars', 'Jupiter']) == {
        'text': (
            '*Sanctions:*\n'
            '_Sanctions have been imposed on you by: Mars, Jupiter_'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_sanctions_info_without_sanctions(renderer_ru, renderer_en):
    assert renderer_ru.render('sanctions_info', sanctioned_planets=[]) == {
        'text': (
            '*Санкции:*\n'
            '_Ни одна из планет не наложила на вас санкции_'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('sanctions_info', sanctioned_planets=[]) == {
        'text': (
            '*Sanctions:*\n'
            '_No planet has imposed sanctions on you_'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_meteorites_info_invented(renderer_ru, renderer_en, planet):
    assert renderer_ru.render('meteorites_info', planet=planet) == {
        'text': (
            '*Метеориты*\n'
            'У вас есть 3 метеорита  ☄️\\.'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('meteorites_info', planet=planet) == {
        'text': (
            '*Meteorites*\n'
            'You have 3 meteorites ☄️\\.'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_meteorites_info_singular_agreement_ru(renderer_ru):
    planet_one = PlanetDto(
        id=5,
        game_id=1,
        name='Венера',
        is_invented=True,
        meteorites=1,
    )
    assert renderer_ru.render('meteorites_info', planet=planet_one) == {
        'text': (
            '*Метеориты*\n'
            'У вас есть 1 метеорит  ☄️\\.'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_meteorites_info_not_invented(renderer_ru, renderer_en, planet_not_invented):
    assert renderer_ru.render('meteorites_info', planet=planet_not_invented) == {
        'text': (
            '*Метеориты*\n'
            '_У вас не разработана технология отправки метеоритов_'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('meteorites_info', planet=planet_not_invented) == {
        'text': (
            '*Meteorites*\n'
            "_You haven't developed meteorite launching technology_"
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_eco_info(renderer_ru, renderer_en, game):
    assert renderer_ru.render('eco_info', game=game) == {
        'text': (
            '*Аномалия*\n'
            'Уровень аномалии 💥: _33 %_'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('eco_info', game=game) == {
        'text': (
            '*Anomaly*\n'
            'Anomaly level 💥: _33 %_'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_other_planet_info(renderer_ru, renderer_en, planet, cities):
    assert renderer_ru.render('other_planet_info', planet=planet, cities=cities) == {
        'text': (
            '__*Земля*__\n\n'
            '*Москва*  ❌ \\(Развитие 0%\\)\n'
            '*Питер* \\(Развитие 70%\\)\n'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('other_planet_info', planet=planet, cities=cities) == {
        'text': (
            '__*Земля*__\n\n'
            '*Москва*  ❌ \\(Development 0%\\)\n'
            '*Питер* \\(Development 70%\\)\n'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_not_enough_money(renderer_ru, renderer_en):
    assert renderer_ru.render('not_enough_money') == {
        'text': (
            'У вас недостаточно средств для выполнения этого действия.\n'
            'Отмените предыдущие и попробуйте заново.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('not_enough_money') == {
        'text': (
            "You don't have enough funds to perform this action.\n"
            'Cancel the previous ones and try again.'
        ),
        'parse_mode': None,
    }


def test_render_not_enough_meteorites(renderer_ru, renderer_en):
    assert renderer_ru.render('not_enough_meteorites') == {
        'text': (
            'У вас недостаточно метеоритов для этого действия.\n'
            'Отмените предыдущие действия или закупите метеориты.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('not_enough_meteorites') == {
        'text': (
            "You don't have enough meteorites for this action.\n"
            'Cancel previous actions or purchase more meteorites.'
        ),
        'parse_mode': None,
    }


def test_render_not_enough_money_for_transaction(renderer_ru, renderer_en):
    assert renderer_ru.render('not_enough_money_for_transaction') == {
        'text': (
            'У вас недостаточно средств для перевода.\n'
            'Введите меньшую сумму для перевода или 0 для отмены перевода.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('not_enough_money_for_transaction') == {
        'text': (
            "You don't have enough funds for the transfer.\n"
            'Enter a smaller amount to transfer, or 0 to cancel the transfer.'
        ),
        'parse_mode': None,
    }


def test_render_wrong_answer(renderer_ru, renderer_en):
    assert renderer_ru.render('wrong_answer') == {
        'text': (
            'Неверный ввод.\n'
            'Введите неотрицательное число, обозначающее сумму, которую вы хотите перевести планете.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('wrong_answer') == {
        'text': (
            'Invalid input.\n'
            'Enter a non-negative number representing the amount you want to transfer to the planet.'
        ),
        'parse_mode': None,
    }


def test_render_successful_transaction(renderer_ru, renderer_en, to_planet):
    assert renderer_ru.render('successful_transaction', to_planet=to_planet) == {
        'text': 'Перевод планете Юпитер успешно выполнен!',
        'parse_mode': None,
    }
    assert renderer_en.render('successful_transaction', to_planet=to_planet) == {
        'text': 'The transfer to planet Юпитер was successful!',
        'parse_mode': None,
    }


def test_render_transaction_notification(renderer_ru, renderer_en, from_planet):
    assert renderer_ru.render('transaction_notification', from_planet=from_planet, amount=500) == {
        'text': 'Планета Сатурн перевела вам 500 💵!',
        'parse_mode': None,
    }
    assert renderer_en.render('transaction_notification', from_planet=from_planet, amount=500) == {
        'text': 'Planet Сатурн has transferred 500 💵 to you!',
        'parse_mode': None,
    }


def test_render_already_built(renderer_ru, renderer_en):
    assert renderer_ru.render('already_built') == {
        'text': 'Вы не можете поставить щит на этот город, т.к. щит на этом городе уже поставлен.',
        'parse_mode': None,
    }
    assert renderer_en.render('already_built') == {
        'text': "You can't put a shield on this city, because it already has one.",
        'parse_mode': None,
    }


def test_render_round_end_for_admin(renderer_ru, renderer_en, game):
    assert renderer_ru.render('round_end_for_admin', game=game) == {
        'text': (
            '_*второй раунд закончен\\!*_\n'
            'Перейдите в приложение для просмотра результатов раунда\\!'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('round_end_for_admin', game=game) == {
        'text': (
            '_*The second round has ended\\!*_\n'
            'Go to the app to view the round results\\!'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_game_results(renderer_ru, renderer_en):
    assert renderer_ru.render('game_results') == {'text': 'Статистика всей игры', 'parse_mode': None}
    assert renderer_en.render('game_results') == {'text': 'Full game statistics', 'parse_mode': None}


def test_render_round_end_for_players(renderer_ru, renderer_en, game):
    assert renderer_ru.render('round_end_for_players', game=game) == {
        'text': (
            '_*второй раунд закончен\\!*_\n'
            'Отправляйтесь на межпланетные переговоры, чтобы увидеть результаты раунда и обсудить их\\.'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('round_end_for_players', game=game) == {
        'text': (
            '_*The second round has ended\\!*_\n'
            'Head to interplanetary negotiations to see the round results and discuss them\\.'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_how_much_money(renderer_ru, renderer_en, to_planet):
    assert renderer_ru.render('how_much_money', to_planet=to_planet) == {
        'text': 'Напишите сколько вы готовы перевести планете Юпитер.',
        'parse_mode': None,
    }
    assert renderer_en.render('how_much_money', to_planet=to_planet) == {
        'text': "Write how much you're willing to transfer to planet Юпитер.",
        'parse_mode': None,
    }


def test_render_negotiations_offer(renderer_ru, renderer_en, from_planet):
    assert renderer_ru.render('negotiations_offer', from_planet=from_planet) == {
        'text': 'Планета Сатурн предлагает принять их дипломата для переговоров.',
        'parse_mode': None,
    }
    assert renderer_en.render('negotiations_offer', from_planet=from_planet) == {
        'text': 'Planet Сатурн offers to send their diplomat for negotiations.',
        'parse_mode': None,
    }


def test_render_negotiations_accepted(renderer_ru, renderer_en, to_planet):
    assert renderer_ru.render('negotiations_accepted', to_planet=to_planet) == {
        'text': (
            'Планета Юпитер приняла ваше предложение о переговорах!\n'
            'Ждите организатора, который подойдёт к вам для того, чтобы сопроводить дипломата.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('negotiations_accepted', to_planet=to_planet) == {
        'text': (
            'Planet Юпитер has accepted your negotiation offer!\n'
            'Wait for the organizer, who will come to escort the diplomat.'
        ),
        'parse_mode': None,
    }


def test_render_negotiations_refused(renderer_ru, renderer_en, to_planet):
    assert renderer_ru.render('negotiations_refused', to_planet=to_planet) == {
        'text': 'Планета Юпитер отказалась от вашего предложения о переговорах.',
        'parse_mode': None,
    }
    assert renderer_en.render('negotiations_refused', to_planet=to_planet) == {
        'text': 'Planet Юпитер has declined your negotiation offer.',
        'parse_mode': None,
    }


def test_render_waiting_for_diplomatist(renderer_ru, renderer_en, from_planet):
    assert renderer_ru.render('waiting_for_diplomatist', from_planet=from_planet) == {
        'text': (
            'Вы приняли предложение о переговорах с Сатурн.\n'
            'Ожидайте дипломата.\n'
            'Как только закончите переговоры, нажмите кнопку снизу.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('waiting_for_diplomatist', from_planet=from_planet) == {
        'text': (
            'You have accepted the negotiation offer from Сатурн.\n'
            'Wait for the diplomat.\n'
            'Once you finish negotiating, press the button below.'
        ),
        'parse_mode': None,
    }


def test_render_negotiations_for_admin(renderer_ru, renderer_en, to_planet, from_planet):
    assert renderer_ru.render('negotiations_for_admin', to_planet=to_planet, from_planet=from_planet) == {
        'text': 'Планета Юпитер хочет принять дипломата от планеты Сатурн',
        'parse_mode': None,
    }
    assert renderer_en.render('negotiations_for_admin', to_planet=to_planet, from_planet=from_planet) == {
        'text': 'Planet Юпитер wants to receive a diplomat from planet Сатурн',
        'parse_mode': None,
    }


def test_render_negotiations_outside_the_round(renderer_ru, renderer_en):
    assert renderer_ru.render('negotiations_outside_the_round') == {
        'text': 'Вы не можете принять дипломата, т.к. находитесь на галактических переговорах.',
        'parse_mode': None,
    }
    assert renderer_en.render('negotiations_outside_the_round') == {
        'text': "You can't receive a diplomat, because you are at galactic negotiations.",
        'parse_mode': None,
    }


def test_render_negotiations_ended(renderer_ru, renderer_en):
    assert renderer_ru.render('negotiations_ended') == {
        'text': (
            'Переговоры закончены.\n'
            'Ожидайте организатора, который сопроводит дипломата до его планеты.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('negotiations_ended') == {
        'text': (
            'Negotiations have ended.\n'
            'Wait for the organizer, who will escort the diplomat back to their planet.'
        ),
        'parse_mode': None,
    }


def test_render_negotiations_ended_for_admin(renderer_ru, renderer_en, to_planet):
    assert renderer_ru.render('negotiations_ended_for_admin', to_planet=to_planet) == {
        'text': 'Планета Юпитер закончила переговоры. Сопроводите дипломата до его планеты.',
        'parse_mode': None,
    }
    assert renderer_en.render('negotiations_ended_for_admin', to_planet=to_planet) == {
        'text': 'Planet Юпитер has finished negotiations. Escort the diplomat back to their planet.',
        'parse_mode': None,
    }


def test_render_busy_at_the_moment(renderer_ru, renderer_en):
    assert renderer_ru.render('busy_at_the_moment') == {
        'text': 'Вы не можете принять к себе дипломата, т.к. на вашей планете уже ведутся переговоры.',
        'parse_mode': None,
    }
    assert renderer_en.render('busy_at_the_moment') == {
        'text': "You can't receive a diplomat, because negotiations are already underway on your planet.",
        'parse_mode': None,
    }


def test_render_bilateral_negotiations(renderer_ru, renderer_en):
    assert renderer_ru.render('bilateral_negotiations') == {
        'text': 'Вы не можете принять к себе эту планету, т.к. дипломат от вашей планеты уже переговаривает с ней',
        'parse_mode': None,
    }
    assert renderer_en.render('bilateral_negotiations') == {
        'text': "You can't receive this planet, because a diplomat from your planet is already negotiating with them",
        'parse_mode': None,
    }


def test_render_wait_for_acception(renderer_ru, renderer_en, to_planet):
    assert renderer_ru.render('wait_for_acception', to_planet=to_planet) == {
        'text': (
            'Запрос на переговоры отправлен!\n'
            'Как только Юпитер примет решение, вам придёт сообщение.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('wait_for_acception', to_planet=to_planet) == {
        'text': (
            'Negotiation request sent!\n'
            "You'll receive a message as soon as Юпитер makes a decision."
        ),
        'parse_mode': None,
    }


def test_render_negotiator_offline(renderer_ru, renderer_en, to_planet):
    assert renderer_ru.render('negotiator_offline', to_planet=to_planet) == {
        'text': (
            'К сожалению, владелец планеты Юпитер не в игре.\n'
            'Попробуйте снова или обратитесь к администратору.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('negotiator_offline', to_planet=to_planet) == {
        'text': (
            'Unfortunately, the owner of planet Юпитер is not in the game.\n'
            'Try again or contact an administrator.'
        ),
        'parse_mode': None,
    }


def test_render_end_of_the_game(renderer_ru, renderer_en):
    assert renderer_ru.render('end_of_the_game') == {
        'text': (
            '*Игра закончена\\!*\n'
            'Отправляйтесь на собрание, чтобы увидеть результаты игры\\.\n'
            'Создатель бота: [Клинов Никита](https://vk.com/nyekitka)\\.\n'
            'Поддержать создателя: [тык](https://www.donationalerts.com/r/nyekitkaa)'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('end_of_the_game') == {
        'text': (
            '*The game has ended\\!*\n'
            'Head to the assembly to see the game results\\.\n'
            'Bot creator: [Nikita Klinov](https://vk.com/nyekitka)\\.\n'
            'Support the creator: [here](https://www.donationalerts.com/r/nyekitkaa)'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_goodbye(renderer_ru, renderer_en):
    assert renderer_ru.render('goodbye') == {
        'text': 'Вы автоматически вышли, т.к. ваша игра закончилась.',
        'parse_mode': None,
    }
    assert renderer_en.render('goodbye') == {
        'text': 'You have been automatically logged out, because your game has ended.',
        'parse_mode': None,
    }


def test_render_ending_outside(renderer_ru, renderer_en):
    assert renderer_ru.render('ending_outside') == {
        'text': 'Вы не можете закончить никакую игру, т.к. не находитесь ни в одной из них.',
        'parse_mode': None,
    }
    assert renderer_en.render('ending_outside') == {
        'text': "You can't end any game, because you are not in one.",
        'parse_mode': None,
    }


def test_render_ending_when_not_started(renderer_ru, renderer_en):
    assert renderer_ru.render('ending_when_not_started') == {
        'text': 'Вы не можете закончить неначавшуюся игру.',
        'parse_mode': None,
    }
    assert renderer_en.render('ending_when_not_started') == {
        'text': "You can't end a game that hasn't started.",
        'parse_mode': None,
    }


def test_render_game_interrupted_report(renderer_ru, renderer_en):
    assert renderer_ru.render('game_interrupted_report') == {
        'text': 'Игра была прервана. Вы автоматически вышли из игры.',
        'parse_mode': None,
    }
    assert renderer_en.render('game_interrupted_report') == {
        'text': 'The game was interrupted. You have automatically left the game.',
        'parse_mode': None,
    }


def test_render_game_interrupted_message(renderer_ru, renderer_en):
    assert renderer_ru.render('game_interrupted_message') == {
        'text': 'Игра была прервана администратором. О подробностях узнавайте у организаторов.',
        'parse_mode': None,
    }
    assert renderer_en.render('game_interrupted_message') == {
        'text': 'The game was interrupted by an administrator. Ask the organizers for details.',
        'parse_mode': None,
    }


def test_render_waiting_time_expired(renderer_ru, renderer_en):
    assert renderer_ru.render('waiting_time_expired') == {
        'text': 'Время ожидания ответа превышено. Перевод отменён.',
        'parse_mode': None,
    }
    assert renderer_en.render('waiting_time_expired') == {
        'text': 'The response waiting time has expired. The transfer has been cancelled.',
        'parse_mode': None,
    }


def test_render_already_started(renderer_ru, renderer_en):
    assert renderer_ru.render('already_started') == {
        'text': 'Вы не можете начать игру, т.к. игра уже в процессе.',
        'parse_mode': None,
    }
    assert renderer_en.render('already_started') == {
        'text': "You can't start the game, because it's already in progress.",
        'parse_mode': None,
    }


def test_render_skipping_round(renderer_ru, renderer_en):
    assert renderer_ru.render('skipping_round') == {
        'text': 'Вы не можете начать новый раунд, т.к. не закончился старый.',
        'parse_mode': None,
    }
    assert renderer_en.render('skipping_round') == {
        'text': "You can't start a new round, because the previous one hasn't ended.",
        'parse_mode': None,
    }


def test_render_start_game_before(renderer_ru, renderer_en):
    assert renderer_ru.render('start_game_before') == {
        'text': (
            'Вы не можете использовать эту команду, т.к. игра не запущена.\n'
            'Сначала начните игру, нажав на соответсвующую кнопку.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('start_game_before') == {
        'text': (
            "You can't use this command, because the game hasn't started.\n"
            'Start the game first by pressing the corresponding button.'
        ),
        'parse_mode': None,
    }


def test_render_promote_notification_for_user(renderer_ru, renderer_en):
    assert renderer_ru.render('promote_notification_for_user') == {
        'text': '👑 Верховный лидер назначил вас администратором!',
        'parse_mode': None,
    }
    assert renderer_en.render('promote_notification_for_user') == {
        'text': '👑 The Supreme Leader has appointed you as administrator!',
        'parse_mode': None,
    }


def test_render_refuse_request_notification_for_user(renderer_ru, renderer_en):
    assert renderer_ru.render('refuse_request_notification_for_user') == {
        'text': '👎 Верховный лидер лишил вас статуса администратора.',
        'parse_mode': None,
    }
    assert renderer_en.render('refuse_request_notification_for_user') == {
        'text': '👎 The Supreme Leader has stripped you of administrator status.',
        'parse_mode': None,
    }


def test_render_refuse_request_notification_for_leader(renderer_ru, renderer_en, user_ru, user_en):
    assert renderer_ru.render('refuse_request_notification_for_leader', user=user_ru) == {
        'text': 'Вы отказали пользователю Иван.',
        'parse_mode': None,
    }
    assert renderer_en.render('refuse_request_notification_for_leader', user=user_en) == {
        'text': 'You have declined user Alice.',
        'parse_mode': None,
    }


def test_render_fire_admin_notification_for_user(renderer_ru, renderer_en):
    assert renderer_ru.render('fire_admin_notification_for_user') == {
        'text': 'Верховный лидер посчитал вас недостойным статуса администратора.',
        'parse_mode': None,
    }
    assert renderer_en.render('fire_admin_notification_for_user') == {
        'text': 'The Supreme Leader has deemed you unworthy of administrator status.',
        'parse_mode': None,
    }


def test_render_promote_notification_for_leader(renderer_ru, renderer_en, user_ru, user_en):
    assert renderer_ru.render('promote_notification_for_leader', user=user_ru) == {
        'text': 'Вы успешно назначили Иван администратором!',
        'parse_mode': None,
    }
    assert renderer_en.render('promote_notification_for_leader', user=user_en) == {
        'text': 'You have successfully appointed Alice as administrator!',
        'parse_mode': None,
    }


def test_render_fire_admin_notification_for_leader(renderer_ru, renderer_en, user_ru, user_en):
    assert renderer_ru.render('fire_admin_notification_for_leader', user=user_ru) == {
        'text': 'Вы сняли полномочия администратора с Иван.',
        'parse_mode': None,
    }
    assert renderer_en.render('fire_admin_notification_for_leader', user=user_en) == {
        'text': 'You have removed administrator privileges from Alice.',
        'parse_mode': None,
    }


def test_render_request_notification_for_leader(renderer_ru, renderer_en, user_ru, user_en):
    assert renderer_ru.render('request_notification_for_leader', user=user_ru) == {
        'text': 'Пользователь [Иван Попов](tg://user?id=1) отправил вам запрос на право администратора\\.',
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('request_notification_for_leader', user=user_en) == {
        'text': 'User [Alice Smith](tg://user?id=2) has sent you a request for administrator rights\\.',
        'parse_mode': 'MarkdownV2',
    }


def test_render_request_notification_for_user(renderer_ru, renderer_en):
    assert renderer_ru.render('request_notification_for_user') == {
        'text': (
            'Запрос отправлен верховному лидеру.\n'
            'Ждите его ответа.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('request_notification_for_user') == {
        'text': (
            'Request sent to the Supreme Leader.\n'
            'Wait for their response.'
        ),
        'parse_mode': None,
    }


def test_render_kick_due_to_admin(renderer_ru, renderer_en):
    assert renderer_ru.render('kick_due_to_admin') == {
        'text': 'Вы были выкинуты из игры, поскольку теперь вы являетесь администратором.',
        'parse_mode': None,
    }
    assert renderer_en.render('kick_due_to_admin') == {
        'text': 'You have been kicked from the game, because you are now an administrator.',
        'parse_mode': None,
    }


def test_render_kick_due_to_not_admin(renderer_ru, renderer_en):
    assert renderer_ru.render('kick_due_to_not_admin') == {
        'text': 'Вы были выкинуты из игры, поскольку теперь вы не являетесь администратором.',
        'parse_mode': None,
    }
    assert renderer_en.render('kick_due_to_not_admin') == {
        'text': 'You have been kicked from the game, because you are no longer an administrator.',
        'parse_mode': None,
    }


def test_render_action_out_of_game(renderer_ru, renderer_en):
    assert renderer_ru.render('action_out_of_game') == {
        'text': 'Вы не можете выполнить данное действие, т.к. находитесь вне игры.',
        'parse_mode': None,
    }
    assert renderer_en.render('action_out_of_game') == {
        'text': "You can't perform this action, because you are outside the game.",
        'parse_mode': None,
    }


def test_render_unexpected_error(renderer_ru, renderer_en):
    assert renderer_ru.render('unexpected_error') == {
        'text': 'Произошла непредвиденная ошибка.',
        'parse_mode': None,
    }
    assert renderer_en.render('unexpected_error') == {
        'text': 'An unexpected error occurred.',
        'parse_mode': None,
    }


def test_render_choose_pack(renderer_ru, renderer_en):
    assert renderer_ru.render('choose_pack') == {
        'text': 'Выберите набор планет и городов для игры.',
        'parse_mode': None,
    }
    assert renderer_en.render('choose_pack') == {
        'text': 'Choose a set of planets and cities for the game.',
        'parse_mode': None,
    }



def test_render_already_in_game(renderer_ru, renderer_en):
    assert renderer_ru.render('already_in_game') == {
        'text': (
            'Вы уже находитесь в лобби.\n'
            'Сначала выйдите из текущего лобби, а затем войдите в другое.'
        ),
        'parse_mode': None,
    }
    assert renderer_en.render('already_in_game') == {
        'text': (
            'You are already in a lobby.\n'
            'Leave the current lobby first, then join another one.'
        ),
        'parse_mode': None,
    }


def test_render_help(renderer_ru, renderer_en):
    assert renderer_ru.render('help', game_config=game_config) == {
        'text': (
            'В данной игре 6 раундов по 10 минут, после каждого из которых идут общие обсуждения, которые не ограничены по времени\\. '
            'По окончании 6 раундов побеждает та планета, средний уровень развития которой является наибольшим, если уровень аномалии не достиг 100%\\. '
            'Если активность аномалии достигла этой отметки, то проигрывают все\\.\n\n'
            'У каждой планеты есть по 4 города, каждый из которых изначально имеет одинаковое развитие и уровень жизни\\. '
            'Уровень жизни города зависит от развития и активности аномалии\\. '
            'От уровня жизни города зависит его доход за раунд\\. '
            'Если город разрушен, то его уровни развития и жизни равны нулю\\. '
            'Если все города на планете разрушены, то вы проигрываете, но у вас ещё есть возможность выполнять действия\\.\n\n'
            'В каждом из раундов вы формируете приказ \\- список действий, которые вы хотите сделать после этого раунда\\. '
            'Все действия, которые вы выберете, применятся только после конца этого раунда, а результат действий всех планет будет обсуждаться на общем\\. '
            'В приказе вам доступно несколько действий:\n\n'
            '📈 *Развитие города* \\- вы вкладываете в деньги в развитие одного из своих городов, тем самым повышая уровень его развития и соответственно уровень жизни\\. '
            'Разрушенный город не подлежит развитию\\. _Стоимость: 150 💵_\n\n'
            '🛡️ *Защита города* \\- вы ставите щит над своим городом, защищая его от прилетающих метеоритов\\. '
            'Щит может защитить город только от одного метеорита\\. '
            'Если метеорит прилетает в город, защищённый щитом, щит разрушается, но город остаётся в целости\\. '
            'На один город нельзя поставить два или более щита\\. '
            'Щит стоит на городе до тех пор, пока его не разрушат\\. '
            'Действие доступно со 2 раунда\\. _Стоимость: 300 💵_\n\n'
            '🛠️ *Разработка технологии отправки метеоритов* \\- вы разрабатываете технологии разработки метеоритов, тем самым разблокируете возможность отправлять метеориты в чужие города или в аномалию\\. '
            'Увеличивает активность аномалии\\. Делается один раз за игру\\. _Стоимость: 500 💵_\n\n'
            '☄️ *Отправка метеоритов в города* \\- вы отправляете метеорит во вражеский город, пытаясь его разрушить\\. '
            'Один метеорит разрушает город без щита либо же разрушает щит над городом\\. '
            'На каждый город за раунд можно отправить только один метеорит, поэтому если вы хотите наверняка разрушить его, то вам нужно скооперироваться с другими планетами\\. '
            'Планета, на которую вы отправляете метеорит не знает о том, кто его отправил\\. '
            'Увеличивает активность аномалии\\. Доступно после разработки технологии отправки\\.\n\n'
            '💥 *Отправка метеорита в аномалию* \\- вы отправляете метеорит в аномалию, тем самым уменьшаете её активность на 20%\\. '
            'За раунд можно сбросить только один метеорит в аномалию\\.\n\n'
            '🧾 *Санкции* \\- вы отправляете пакет санкций на планету, тем самым уменьшая её доход за этот раунд\\. '
            'Отправка санкций бесплатна, но планеты знают, кто им их отправил\\.\n\n'
            'Помимо всех этих действий также доступны действия, которые не входят в приказ и происходят мгновенно\\.\n\n'
            '📞 *Переговоры* \\- вы отправляете запрос другой планете на переговоры\\. '
            'Если вас примут, то вы отправляете одного дипломата на эту планету\\. '
            'Планета так же в праве отказать, либо удержать ваше предложение\\. '
            'Вы можете принимать не более одной планеты на территории своей одновременно, но можете отправить своих дипломатов сразу в несколько планет \\(кроме той, с которой уже переговариваете\\)\\.\n\n'
            '💸 *Перевод денег* \\- вы переводите определённую сумму другой планете\\. Перевод мгновенный и безвозвратный\\.'
        ),
        'parse_mode': 'MarkdownV2',
    }
    assert renderer_en.render('help', game_config=game_config) == {
        'text': (
            'This game consists of 6 rounds, each lasting 10 minutes, followed by a general discussion with no time limit\\. '
            'After all 6 rounds have ended, the planet with the highest average development level wins, provided the anomaly activity has not reached 100%\\. '
            'If the anomaly activity reaches this threshold, all planets lose\\.\n\n'
            'Each planet has 4 cities, all of which start with the same development level and quality of life\\. '
            'A city\'s quality of life depends on its development level and the anomaly activity\\. '
            'A city\'s income each round depends on its quality of life\\. '
            'If a city is destroyed, both its development level and quality of life become zero\\. '
            'If all cities on your planet are destroyed, you lose, but you may still perform actions\\.\n\n'
            'During each round, you create an order \\- a list of actions you want to perform after the round ends\\. '
            'All selected actions are applied only after the end of the current round, and the results of every planet\'s actions are announced during the general discussion\\. '
            'The following actions are available in your order:\n\n'
            '📈 *Develop city* \\- invest money into developing one of your cities, increasing its development level and, consequently, its quality of life\\. '
            'Destroyed cities cannot be developed\\. _Cost: 150 💵_\n\n'
            '🛡️ *Protect city* \\- place a shield over one of your cities, protecting it from incoming meteors\\. '
            'A shield can protect a city from only one meteor\\. '
            'If a meteorite strikes a shielded city, the shield is destroyed, but the city remains intact\\. '
            'A city cannot have more than one shield at the same time\\. '
            'A shield remains in place until it is destroyed\\. '
            'This action becomes available starting from Round 2\\. _Cost: 300 💵_\n\n'
            '🛠️ *Research meteorite launch technology* \\- develop the technology required to launch meteors, unlocking the ability to send meteorites to enemy cities or into the anomaly\\. '
            'Increases anomaly activity\\. Can only be performed once per game\\. _Cost: 500 💵_\n\n'
            '☄️ *Launch meteorites at cities* \\- send a meteorite toward an enemy city in an attempt to destroy it\\. '
            'A single meteorite destroys an unshielded city or destroys the shield protecting it\\. '
            'Only one meteorite may be sent to each city per round, so if you want to guarantee its destruction, you will need to coordinate with other planets\\. '
            'The target planet does not know who launched the meteor\\. '
            'Increases anomaly activity\\. Available after researching the launch technology\\.\n\n'
            '💥 *Launch a meteorite into the anomaly* \\- send a meteorite into the anomaly, reducing its activity by 20%\\. '
            'Only one meteorite can be launched into the anomaly per round\\.\n\n'
            '🧾 *Sanctions* \\- send a package of sanctions to another planet, reducing its income for the current round\\. '
            'Sending sanctions is free, but the target planet knows who imposed them\\.\n\n'
            'In addition to these actions, there are also instant actions that are not included in your order\\.\n\n'
            '📞 *Negotiations* \\- send a negotiation request to another planet\\. '
            'If they accept, you send one diplomat to their planet\\. '
            'They may also decline or leave your request pending\\. '
            'You may host only one foreign planet on your territory at a time, but you may send your diplomats to multiple planets simultaneously \\(except for a planet with which you are already conducting negotiations\\)\\.\n\n'
            '💸 *Transfer money* \\- transfer a specified amount of money to another planet\\. '
            'Transfers are instant and irreversible\\.'
        ),
        'parse_mode': 'MarkdownV2',
    }


def test_render_untimely_negotiations(renderer_ru, renderer_en):
    assert renderer_ru.render('untimely_negotiations') == {
        'text': 'Сейчас нельзя находиться на переговорах',
        'parse_mode': None,
    }
    assert renderer_en.render('untimely_negotiations') == {
        'text': 'Now is not the time for negotiations!',
        'parse_mode': None,
    }


def test_render_planet_is_busy(renderer_ru, renderer_en):
    assert renderer_ru.render('planet_is_busy') == {
        'text': 'Данная планета уже находится на переговорах',
        'parse_mode': None,
    }
    assert renderer_en.render('planet_is_busy') == {
        'text': 'This planet is already negotiating.',
        'parse_mode': None,
    }


def test_render_already_negotiating(renderer_ru, renderer_en):
    assert renderer_ru.render('already_negotiating') == {
        'text': 'Вы уже принимаете одну планету на переговорах',
        'parse_mode': None,
    }
    assert renderer_en.render('already_negotiating') == {
        'text': 'You are already negotiating with this planet.',
        'parse_mode': None,
    }


def test_render_object_not_found(renderer_ru, renderer_en):
    assert renderer_ru.render('object_not_found') == {
        'text': 'Запрашиваемый объект не найден.',
        'parse_mode': None,
    }
    assert renderer_en.render('object_not_found') == {
        'text': 'Requested object is not found.',
        'parse_mode': None,
    }


def test_render_already_invented(renderer_ru, renderer_en):
    assert renderer_ru.render('already_invented') == {
        'text': 'У вас уже изобретена технология отправки метеоритов',
        'parse_mode': None,
    }
    assert renderer_en.render('already_invented') == {
        'text': 'You have already invented meteorite launch technology',
        'parse_mode': None,
    }


def test_render_not_enough_players_short(renderer_ru, renderer_en):
    assert renderer_ru.render('not_enough_players_short') == {
        'text': 'Недостаточно игроков для того, чтобы начать игру.',
        'parse_mode': None,
    }
    assert renderer_en.render('not_enough_players_short') == {
        'text': "There's not enough players to start the game.",
        'parse_mode': None,
    }


def test_render_not_in_game(renderer_ru, renderer_en):
    assert renderer_ru.render('not_in_game') == {
        'text': 'Вы не находитесь в лобби, чтобы из него выходить.',
        'parse_mode': None,
    }
    assert renderer_en.render('not_in_game') == {
        'text': "You are currently not in a lobby, so you can't leave any.",
        'parse_mode': None,
    }


def test_render_negative_amount(renderer_ru, renderer_en):
    assert renderer_ru.render('negative_amount') == {
        'text': 'Нельзя переводить неположительную сумму',
        'parse_mode': None,
    }
    assert renderer_en.render('negative_amount') == {
        'text': 'You cannot transfer non-positive amount of money.',
        'parse_mode': None,
    }


def test_render_is_not_invented(renderer_ru, renderer_en):
    assert renderer_ru.render('is_not_invented') == {
        'text': 'Вы не можете покупать метеориты поскольку у вас ещё не разработана технология их отправки.',
        'parse_mode': None,
    }
    assert renderer_en.render('is_not_invented') == {
        'text': "You cannot buy meteorites because you haven't invented the launch technology yet.",
        'parse_mode': None,
    }


def test_render_self_attack(renderer_ru, renderer_en):
    assert renderer_ru.render('self_attack') == {
        'text': 'Отправлять метеорит на свой город невозможно.',
        'parse_mode': None,
    }
    assert renderer_en.render('self_attack') == {
        'text': "It's impossible to attack your city.",
        'parse_mode': None,
    }


def test_render_round_is_not_going(renderer_ru, renderer_en):
    assert renderer_ru.render('round_is_not_going') == {
        'text': 'Нельзя закончить раунд, потому что сейчас никакого раунда не идёт.',
        'parse_mode': None,
    }
    assert renderer_en.render('round_is_not_going') == {
        'text': "You can't finish the round because there's no round going on right now.",
        'parse_mode': None,
    }


def test_render_game_ended(renderer_ru, renderer_en):
    assert renderer_ru.render('game_ended') == {
        'text': 'Игра уже закончена.',
        'parse_mode': None,
    }
    assert renderer_en.render('game_ended') == {
        'text': 'Game has already ended.',
        'parse_mode': None,
    }


def test_render_game_is_full(renderer_ru, renderer_en):
    assert renderer_ru.render('game_is_full') == {
        'text': 'В данной игре нет свободных планет. Зайдите в другую игру.',
        'parse_mode': None,
    }
    assert renderer_en.render('game_is_full') == {
        'text': 'There are no free planets in this game. Log into another game.',
        'parse_mode': None,
    }


def test_render_cannot_start_round(renderer_ru, renderer_en):
    assert renderer_ru.render('cannot_start_round') == {
        'text': 'Нельзя начать новый раунд',
        'parse_mode': None,
    }
    assert renderer_en.render('cannot_start_round') == {
        'text': 'You cannot start a new round.',
        'parse_mode': None,
    }


def test_render_different_games(renderer_ru, renderer_en):
    assert renderer_ru.render('different_games') == {
        'text': 'Нельзя перевести планете из другой игры',
        'parse_mode': None,
    }
    assert renderer_en.render('different_games') == {
        'text': 'You cannot transfer to a planet from other lobbies.',
        'parse_mode': None,
    }


def test_render_wait_till_game_ends(renderer_ru, renderer_en):
    assert renderer_ru.render('wait_till_game_ends') == {
        'text': 'Нельзя выполнить эту операцию, поскольку игрок находится в игре. Подождите пока она закончится.',
        'parse_mode': None,
    }
    assert renderer_en.render('wait_till_game_ends') == {
        'text': "This operation cannot be performed because the player is in the game. Wait until it's over.",
        'parse_mode': None,
    }
