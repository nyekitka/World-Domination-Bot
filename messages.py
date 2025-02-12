import json
import psycopg2
import pymorphy3
from num2words import num2words
from game_classes import City, Planet, Game

_messages_file = open('./presets/messages.json', encoding='utf-8')
Messages = json.load(_messages_file)
morph = pymorphy3.MorphAnalyzer()

class Messager:
    """
    Class that contains all info messages
    """
    def __init__(self, connection : psycopg2.extensions.connection):
        self.__conn = connection

    def start_msg(self, isadmin: bool, ingame: bool, name: str):
        if isadmin and ingame:
            return Messages['start_admin_wgame'].format(name)
        elif isadmin and not ingame:
            return Messages['start_admin_wogame'].format(name)
        elif not isadmin and ingame:
            return Messages['start_user_wgame'].format(name)
        else:
            return Messages['start_user_wogame'].format(name)
    
    def admin_enters(self):
        return Messages['admin_enters_game']
    
    def na_command(self):
        return Messages['not_accessible_command']
    
    def invalid_code(self):
        return Messages['invalid_code']
    
    def incorrect_code(self):
        return Messages['incorrect_code']
    
    def welcome(self, name: str):
        return Messages['login'].format(name)

    def already_logged(self):
        return Messages['already_logged']
    
    def success_enter(self, id, planetname):
        return Messages['success_enter'].format(id, planetname)
    
    def success_admin_enter(self, id):
        return Messages['success_admin_enter'].format(id)
    
    def success_enter_for_others(self, planetname : str, active_num : int, all_num : int):
        return Messages['success_enter_for_others'].format(planetname, active_num, all_num)
    
    def leave_for_others(self, planetname: str, active_num: int, all_num: int):
        return Messages['leave_for_others'].format(planetname, active_num, all_num)
    
    def leaving_msg(self):
        return Messages['leaving_msg']
    
    def starting_game_not_being_in(self):
        return Messages['starting_game_not_being_in']
    
    def game_created(self, gameid, n):
        return Messages['game_created'].format(gameid, n)

    def round_message(self, n: int):
        if n == 1:
            return Messages['first_round']
        else:
            return Messages['common_round'].format(num2words(n, lang='ru', to='ordinal').capitalize())
    
    def round_admins(self, n: int):
        if n == 1:
            return Messages['first_round_for_admins']
        else:
            return Messages['round_for_admins'].format(num2words(n, lang='ru', to='ordinal').capitalize())


    def city_stats_message(self, planet: Planet) -> str:
        all_info = [planet.name(),
                    planet.balance(),
                    planet.rate_of_life()]
        cities = planet.cities()
        for city in cities:
            addition = ''
            if city.is_under_shield():
                addition = ' 🛡️'
            elif city.development() == 0:
                addition = ' ❌'
            all_info.extend([city.name() + addition, city.development(), city.rate_of_life(), city.income()])
        return Messages['city_info'].format(*all_info)
    
    def sanctions_message(self, planet: Planet) -> str:
        sanctions = planet.get_sanc_set()
        if len(sanctions) == 0:
            return Messages['sanctions_info'].format('Ни одна из планет не наложила на вас санкции')
        else:
            return Messages['sanctions_info'].format('На вас наложили санкции: ' + ', '.join(sanctions))

    def meteorites_message(self, planet: Planet) -> str:
        if planet.is_invented():
            word = morph.parse('метеорит')[0]
            meteorites_count = planet.meteorites()
            word = word.make_agree_with_number(meteorites_count).word
            return f'*Метеориты:*\n_У вас {meteorites_count} {word}_ ☄️'
        else:
            return '*Метеориты:*\n_У вас не разработана технология отправки метеоритов_'
    
    def eco_message(self, game: Game) -> str:
        return Messages['eco_info'].format(100 - game.eco_rate())

    def other_planets_message(self, planet: Planet) -> str:
        args = [planet.name()]
        for city in planet.cities():
            args.extend([city.name() + (' ❌' if city.development() == 0 else ''), city.development()])
        return Messages['other_planet'].format(*args)
    
    def already_started(self):
        return Messages['already_started']
    
    def not_enough_players(self, n1: int, n2: int):
        return Messages['not_enough_players'].format(n1, n2)
    
    def choose_lobby(self):
        return Messages['choose_lobby']
    
    def no_games(self):
        return Messages['no games']

    def fivemin(self):
        return Messages['5 minutes left']
    
    def onemin(self):
        return Messages['1 minute left']
    
    def admin_round_end(self, nround: int):
        return Messages['round_results'].format(nround)
    
    def round_end(self, nround: int):
        return Messages['end_of_round'].format(nround)
    
    def game_results(self):
        return Messages['game_results']
    
    def end_of_the_game(self):
        return Messages['end_of_the_game']

    def goodbye(self):
        return Messages['goodbye']

    def negotiations_ended(self):
        return Messages['negotiations_ended']

    def negotiations_ended_admin(self, planetname):
        return Messages['negotiations_ended_for_admin'].format(planetname)
    
    def wait_for_diplomatist(self, planetname):
        return Messages['waiting_for_diplomatist'].format(planetname)
    
    def neg_accept_for_admin(self, planet1, planet2):
        return Messages['negotiations_for_admin'].format(planet1, planet2)
    
    def negotiations_accepted(self, planet):
        return Messages['negotiations_accepted'].format(planet)
    
    def negotiations_denied(self, planet):
        return Messages['negotiations_denied'].format(planet)
    
    def wait_for_acception(self, planet):
        return Messages['wait_for_acception'].format(planet)
    
    def nobody_online(self, planet):
        return Messages['nobody_online'].format(planet)
    
    def negotiations_offer(self, planet):
        return Messages['negotiations_offer'].format(planet)
    
    def how_much_money(self, planet):
        return Messages['how_much_money'].format(planet)
    
    def waiting_time_expired(self):
        return Messages['waiting_time_expired']
    
    def successful_transaction(self, planet):
        return Messages['successful_transaction'].format(planet)
    
    def transaction_notification(self, planet, amount):
        return Messages['transaction_notification'].format(planet, amount)

    def wrong_answer(self):
        return Messages['wrong_answer']
    
    def ending_outside(self):
        return Messages['ending_outside']
    
    def game_interrupted_report(self):
        return Messages['game_interrupted_report']
    
    def game_interrupted_message(self):
        return Messages['game_interrupted_message']
    
    def knight(self):
        return Messages['knight']
    
    def unknight(self):
        return Messages['unknight']
    
    def knighting_for_leader(self, name):
        return Messages['knighting_for_leader'].format(name)
    
    def unknighting_for_leader(self, name):
        return Messages['unknighting_for_leader'].format(name)