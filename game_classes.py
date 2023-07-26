from functools import reduce
from typing import List, TypeVar, Optional

CityT = TypeVar('CityT', bound='City')
PlanetT = TypeVar('PlanetT', bound='Planet')
GameT = TypeVar('GameT', bound='Game')

class City: # могут ли накладываться санкции на отдельные города?
    def __init__(self, name : str, planet : Optional[PlanetT] = None):
        self.__development = 60                 # развитие города
        self.__shield = False                   # наличие щита
        self.__name = name                      # название города
        self.__planet = planet
        
    def build_shield(self): # постановка щита
        self.__shield = True

    def name(self): 
        return self.__name
    
    def set_planet(self, planet: PlanetT):
        self.__planet = planet
    
    def planet(self):
        return self.__planet
    
    def attacked(self): # если на город нападут
        if self.__shield:
            self.__shield = False
        else:
            self.__development = 0
    
    def develop(self): # развитие города
        self.__development += 20
    
    def is_under_shield(self):
        return self.__shield
    
    def rate_of_life(self, eco_rate: int):
        return int(self.__development * eco_rate / 100)
    
    def development(self):
        return self.__development
    
    def income(self) -> int:
        return int(300 * self.__development / 100)

class Planet:
    
    def __init__(self, name : str, login : str, game : GameT, cities: List[City]):
        self.__name = name
        self.__game = game
        self.__login = login        # логин владельца планеты
        self.__city = cities        # список городов на планете
        self.__sanctions = set()    # сет санкций на планете
        self.__balance = 1000       # баланс планеты
        self.__meteorites = 0       # количество имеющихся метеоритов
        self.__is_invented = False  # наличие технологии по разработке метеоритов (aka ядерная разработка)
        self.__order = dict()       # формирующийся приказ
        for city in cities:
            city.set_planet(self)
    
    def name(self):
        return self.__name
    
    def login(self):
        return self.__login
    
    def game(self) -> GameT :
        return self.__game
    
    def cities(self) -> list[City]:
        return self.__city
    
    def invent(self):  # изобретение ядерной разработки
        if self.__balance >= 500 and not self.__is_invented and not self.__order.get('invent'):
            self.__balance -= 500
            self.__order['invent'] = True
        elif self.__order.get('invent'):
            self.__order['invent'] = False
            self.__balance += 500
        elif self.__is_invented:
            raise ValueError
        elif self.balance < 500:
            raise ArithmeticError
        
    
    def complete_invention(self):
        self.__is_invented = True
        self.__game.eco_rate -= 2
    
    def is_invented(self):
        return self.__is_invented
        
    def create_meteorite(self, n: int): # обработка, если не изобретено
        if self.__is_invited and 'create_meteorite' in self.__order and self.balance + self.__order['create_meteorites']*150 >= 150*n: 
            # self.__meteorites += n
            self.__balance += 150*(self.__order['create_meteorites'] - n)
            self.__order['create_meteorite'] = n
        elif 'create_meteorite' not in self.__order.keys():
            self.__balance -= 150*n
            self.__order['create_meteorite'] = n
        elif not self.__is_invented:
            raise ValueError
        else:
            raise ArithmeticError
    
    def complete_creating(self, n: int):
        self.__meteorites += n
        self.__game.eco_rate -= 2*n
            
    # def cancel_meteorite(self): # отменить действие предыдущей функции
    #     self.__meteorites -= 1
    #     self.__balance += 150
    #     Planet.eco_rate += 2
        
    def meteorites_count(self):  # колическтво имеющихся метеоритов
        return self.__meteorites
    
    def attack(self, city: City):
        if 'attack' not in self.__order and self.__meteorites != 0:
            self.__order['attack'] = [city]
            self.__meteorites -= 1
        elif city in self.__order['attack']:
            self.__order.remove(city)
            self.__meteorites += 1
        elif self.__meteorites == 0:
            raise ArithmeticError
        else:
            self.__order.append(city)
            self.__meteorites -= 1
    
    def attacked(self, city_name: str):  # атака города на этой планете
        self.__game.eco_rate -= 2
        for city in self.__city:
            if city.name() == city_name:
                city.attacked()
                break
    
    def develop_city(self, city: City):
        if city in self.__city and self.__balance >= 150 and ('develop' not in self.__order.keys() or city not in self.__order['develop']):
            # city.develop()
            self.__balance -= 150
            if 'develop' not in self.__order.keys():
                self.__order['develop'] = [city]
            else:
                self.__order['develop'].append(city)
        elif city in self.__order['develop']:
            self.__order['develop'].remove(city)
            self.__balance += 150
        elif city not in self.__city:
            raise ValueError
        else:
            raise ArithmeticError
    
    def complete_development(self ,city: City):
        city.develop()
    
    def eco_boost(self):  # сброс бомбы на аномалию
        if self.__meteorites >= 1 and not self.__order['eco boost']:
            self.__meteorites -= 1
            self.__order['eco boost'] = True
        elif self.__order['eco boost']:
            self.__meteorites += 1
            self.__order['eco boost'] = False
        else:
            raise ArithmeticError
    
    def complete_eco_boost(self):
        self.__game.eco_rate += 20

    def rate_of_life(self): # для вывода статистики
        return int(sum((city.rate_of_life(self.__game.eco_rate()) for city in self.__city))/4)

    def income(self):  # доход
        sanc_coef = len(self.__sanctions) * 0.1
        cities_income = sum((city.income() for city in self.__city))
        return int(cities_income*(1 - sanc_coef))
    
    def add_money(self, income: int):  # начислить доход
        self.__balance += income
    
    def send_sactions(self, planets: list):
        if 'sanctions' not in self.__order.keys():
            self.__order['sanctions'] = []
        for planet in planets:
            if planet not in self.__order['sanctions']:
                self.__order['sanctions'].append(planet)
            else:
                self.__order['sanctions'].remove(planet)
    
    def get_sanctions(self, planet: str):  # прибавленение санкций, принимает название страны
        self.__sanctions.add(planet)
    
    def show_sanc_set(self):
        return self.__sanctions
    
    def free_sanc_set(self):  # опустошение санкционного сета (перед началом нового раунда)
        self.__sanctions.clear()
        
    def build_shield(self, city: City):  # построение щита
        if self.__balance >= 300 and city in self.__city and ('build_shield' not in self.__order.keys() or city not in self.__order['build_shield']) and city.development() > 0 and not city.is_under_shield():
            self.__balance -= 300
            if 'build_shield' not in self.__order.keys():
                self.__order['build_shield'] = [city]
            else:
                self.__order['build_shield'].append(city)
        elif city not in self.__city:
            raise ValueError
        elif city.is_under_shield():
            raise ValueError
        elif city in self.__order['build_shield']:
            self.__order['build_shield'].remove(city)
            self.__balance += 300
        elif city.development() == 0:
            raise ValueError
        else:
            raise ArithmeticError
        
    
    def complete_building(self, city: City):
        city.build_shield()
            
                
    def transfer(self, planet : PlanetT, money: int):  # перевод денег
        if self.__balance >= money:
            self.__balance -= money
            planet.__balance += money
        else:
            raise ArithmeticError
    
    def balance(self) -> int:
        return self.__balance
    
    def is_under_shield(self, city_name: str) -> bool:
        for city in self.__city:
            if city.name() == city_name:
                return city.is_under_shield()
    
    def clear_order(self):
        self.__order.clear()
        
    def order(self) -> dict:
        return self.__order
      
class Game:
    def __init__(self, planets_quantity: int, logins: list[str]):
        self.__eco_rate = 95
        self.__active_players = [None]*planets_quantity
        self.__state = 'inactive'                               # inactive/passive/active/conversations
        self.__planets_quantity = planets_quantity              # количество планет
        self.__planet = dict()                                  # список планет {'name': Planet1}
        with open('preset.txt', "r", encoding='UTF-8') as file: # заполнение списка планет
            lines = file.readlines()[:planets_quantity]
            i = 0
            for line in lines:
                cities = []
                for city_name in line.split()[1:]:
                    cities.append(City(city_name))
                self.__planet[line.split()[0]] = Planet(line.split()[0], logins[i], self, cities)
                i += 1
        self.__round = 0                                        # номер раунда
    
    def join_user(self, login : str):
        if None in self.__active_players and login not in self.__active_players:
            self.__active_players[self.__active_players.index(None)] = login
            
    def kick_user(self, login : str):
        if login in self.__active_players and login is not None:
            self.__active_players.remove(login)
            self.__active_players.append(None)
            
    def eco_rate(self):
        return self.__eco_rate
    
    def planets(self):
        return self.__planet
    
    def number_of_planets(self):
        return self.__planets_quantity
    
    def active_users(self):
        return [login for login in self.__active_players if login is not None]
    
    def users_online(self) -> int:
        return self.__planets_quantity - self.__active_players.count(None)
    
    def all_users(self):
        return [planet.login() for planet in self.__planet.values()]

    def get_homeland(self, login):
        for planet in self.__planet.values():
            if login == planet.login():
                return planet
    
    def show_round(self):
        return self.__round
    
    def start_new_round(self):
        self.__round += 1
        self.__state = 'passive' if self.__round == 1 else 'active'
        for planet in self.__planet.values():
            planet.free_sanc_set()
            if self.__round != 1:
                planet.add_money(planet.income())
    
    def end_this_round(self):
        orders = dict()
        for planet in self.__planet.values():
            orders[planet] = planet.order()
        self.get_orders(orders)
        for planet in orders.keys():
            planet.clear_order()
        self.__state = 'conversations'
        
        
    def end_this_game(self):
        self.__state = 'inactive'
    
    def state(self):
        return self.__state
    
    def balance(self, planet_name: str):
        return self.__planet[planet_name].balance()
    
    def __get_sanctions(self, from_planet: str, planets_list: List[str]):
        for planet in planets_list:
            self.__planet[planet].get_sanctions(from_planet)
    
    def show_sanc_set(self, planet_name: str):
        self.__planet[planet_name].show_sanc_set()    
    
    
    def __attack(self, attack_list: list[City]):
        for city in attack_list:
            city.planet.attacked(city.name())
    
    def is_under_shield(self, planet_name: str, city_name: str):
        return self.__planet[planet_name].is_under_shield(city_name)
    
    def get_orders(self, orders : dict[Planet, dict]):
        # Структура order:
        # {
        # 'develop' : [<город1>, ... ]
        # 'transfer' : ( <кому> , <сколько> ),
        # 'sanctions' : [ <планета1>, ... , <планетаN> ],    ''' список стран, на которые planet_name накладывает санкции '''
        # 'build_shield' : [ <город1>, ... , <городN> ],
        # 'attack' :  { <планета> : [ <город> ], ... },
        # 'eco_boost' : True/False,
        # 'invent' : True/False,
        # 'create_meteorite' : N
        # }
        #development
        for planet, order in orders.items():
            if 'develop' in order:
                for city in order['develop']:
                    planet.complete_development(city)
            if 'sanctions' in order:
                self.__get_sanctions(planet.name(), order['sanctions'])
            if 'build_shield' in order:
                for city in order['build_shield']:
                    planet.complete_building(city)
            if order.get('eco_boost'):
                planet.complete_eco_boost()
            if order.get('invent'):
                planet.complete_invention()
            if 'create_meteorite' in order:
                planet.complete_creating(order['create_meteorite'])
        
        for planet, order in orders.items():
            if 'attack' in order:
                self.__attack(order['attack'])
            
    def info(self, planet_name = None):
        if planet_name is None:
            info = dict()
            for planet in self.__planet:
                info[planet] = self.__planet[planet].rate_of_life()
            info['eco_rate'] = self.__eco_rate
            return info
        else:
            info = dict()
            info['login'] = self.__planet[planet_name].login()
            info['meteorites_count'] = self.__planet[planet_name].meteorites_count()
            info['is_invented'] = self.__planet[planet_name].is_invented()
            info['rate_of_life'] = self.__planet[planet_name].rate_of_life()
            info['balance'] = self.__planet[planet_name].balance()
            info['eco_rate'] = self.__eco_rate
            return info
