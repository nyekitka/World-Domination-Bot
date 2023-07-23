from functools import reduce
from typing import List


class City: # могут ли накладываться санкции на отдельные города?
    def __init__(self, name):
        self.__development = 60   # развитие города
        self.__shield = False     # наличие щита
        self.__name = name        # название города
        
    def build_shield(self): # постановка щита
        self.__shield = True

    def name(self): 
        return self.__name
    
    def attacked(self): # если на город нападут
        if self.__shield:
            self.__shield = False
        else:
            self.__development -= 20
    
    def develop(self): # развитие города
        self.__development += 20
    
    def is_under_shield(self):
        return self.__shield
    
    def rate_of_life(self, eco_rate: int):
        return int(self.__development * eco_rate / 100) 
        

class Planet:
    eco_rate = 95
    
    def __init__(self, name, cities: List[City]):
        self.__name = name     
        self.__city = cities        # список городов на планете
        self.__sanctions = set()    # сет санкций на планете
        self.__balance = 1000       # баланс планеты
        self.__meteorites = 0       # количество имеющихся метеоритов
        self.__is_invented = False  # наличие технологии по разработке метеоритов (aka ядерная разработка)
    
    def name(self):
        return self.__name
    
    def invent(self):  # изобретение ядерной разработки
        if self.__balance >= 500 and not self.__is_invented:
            self.__is_invented = True
            self.__balance -= 500
            Planet.eco_rate -= 2
    
    def is_invented(self):
        return self.__is_invented
        
    def create_meteorite(self): # обработка, если не изобретено
        if self.__is_invited and self.balance >= 150: 
            self.__meteorites += 1
            self.__balance -= 150
            Planet.eco_rate -= 2
            
    # def cancel_meteorite(self): # отменить действие предыдущей функции
    #     self.__meteorites -= 1
    #     self.__balance += 150
    #     Planet.eco_rate += 2
        
    def meteorites_count(self):  # колическтво имеющихся метеоритов
        return self.__meteorites
    
    def attacked(self, city_name: str):  # атака города на этой планете
        self.__meteorites -= 1
        Planet.eco_rate -= 2
        for city in self.__city:
            if city.name() == city_name:
                city.attacked()
                break
    
    def eco_boost(self):  # сброс бомбы на аномалию
        if self.__meteorites >= 1: # мы же прям метеорит скидываем???
            self.__meteorites -= 1
            Planet.eco_rate += 20

    def rate_of_life_in_cities(self):  # уроввень жизни во всех городах суммарно
            return reduce(lambda x, y: x.rate_of_life(Planet.eco_rate) + y.rate_of_life(Planet.eco_rate), self.__city) 

    def rate_of_life(self): # для вывода статистики
        res = dict()
        for city in self.__city:
            res[city.name()] = city.rate_of_life()
        return res       

    def income(self):  # доход
        sanc_coef = len(self.__sanctions) * 0.1
        res = 300 * self.rate_of_life_in_cities()
        if sanc_coef:
            res *= sanc_coef
        return int(res)
    
    def add_money(self, income: int):  # начислить доход
        self.__balance += income
    
    def get_sanctions(self, planet: str):  # прибавленение санкций, принимает название страны
        self.__sanctions.add(planet)
    
    def show_sanc_set(self):
        return self.__sanctions
    
    def free_sanc_set(self):  # опустошение санкционного сета (перед началом нового раунда)
        self.__sanctions.clear()
        
    def build_shield(self, city_name: str):  # построение щита
        if self.__balance >= 300:
            for city in self.__city:
                if city.name() == city_name:
                    # if city.is_under_shield():
                    #     raise Exception('Shield exists')
                    # else:
                    city.build_shield()
                    break
                
    def transfer(self, money: int):  # перевод денег
        if self.__balance >= money:
            self.__balance -= money
    
    def balance(self):
        return self.__balance
    
    def is_under_shield(self, city_name: str):
        for city in self.__city:
            if city.name() == city_name:
                return city.is_under_shield()
      
class Game:
    def __init__(self, planets_quantity: int):
        self.__planets_quantity = planets_quantity              # количество планет
        self.__planet = dict()                                  # список планет {'name': Planet1}
        with open('preset.txt', "r") as file:                   # заполнение списка планет
            lines = file.readlines()[:planets_quantity + 1]
            for line in lines:
                cities = []
                for city_name in line.split()[1:]:
                    cities.append(City(city_name))
                self.__planet[line.split()[0]] = Planet(line.split()[0], cities)
        self.__round = 0                                        # номер раунда
    
    def show_round(self):
        return self.__round
    
    def start_new_round(self):
        self.__round += 1
        for planet in self.__planet:
            planet.free_sanc_set()
            planet.add_money(planet.income())
    
    def balance(self, planet_name: str):
        return self.__planet[planet_name].balance()
    
    def __transfer(self, from_planet: str, to_planet: str, money: int):
            self.__planet[from_planet].transfer(money)
            self.__planet[to_planet].add_money(money)
    
    def __get_sanctions(self, from_planet: str, planets_list: List(str)):
        for planet in planets_list:
            self.__planet[planet].get_sanctions(from_planet)
    
    def show_sanc_set(self, planet_name: str):
        self.__planet[planet_name].show_sanc_set()    
    
    def __build_shield(self, planet_name: str, cities_list: List(str)):
        for city in cities_list:
            self.__planet[planet_name].build_shield(city)
    
    def __attack(self, attack_list: dict):
        for planet in attack_list:
            for city in attack_list[planet]:
                self.__planet[planet].attacked(city)
    
    def is_under_shield(self, planet_name: str, city_name: str):
        return self.__planet[planet_name].is_under_shield(city_name)
    
    def get_order(self, planet_name: str, order: dict):
        # Структура order:
        # {
        # 'transfer' : ( <кому> , <сколько> ),
        # 'sanctions' : [ <планета1>, ... , <планетаN> ],    ''' список стран, на которые planet_name накладывает санкции '''
        # 'build_shield' : [ <город1>, ... , <городN> ],
        # 'attack' :  { <планета> : [ <город> ], ... },
        # 'eco_boost' : True/False,
        # 'invent' : True/False,
        # 'create_meteorite' : N
        # }
        if order['transfer']:
            self.__transfer(planet_name, order['transfer'][0], order['transfer'][1])
        if order['sanctions']:
            self.__get_sanctions(planet_name, order['sanctions'])
        if order['build_shield']:
            self.__build_shield(planet_name, order['build_shield'])
        if order['attack']:
            self.__attack(order['attack'])
        if order['eco_boost']:
            self.__planet[planet_name].eco_boost()
        if order['invent']:
            self.__planet[planet_name].invent()
        if order['create_meteorite']:
            self.__create_meteorite()
            
    def info(self, planet_name: str):
        info = dict()
        info['meteorites_coun'] = self.__planet[planet_name].meteorites_count()
        info['is_invented'] = self.__planet[planet_name].is_invented()
        info['rate_of_life'] = self.__planet[planet_name].rate_of_life()
        info['balance'] = self.__planet[planet_name].balance()
        info['eco_rate'] = Planet.eco_rate
    
    def info(self):
        info = dict()
        for planet in self.__planet:
            info[planet] = self.__planet[planet].rate_of_life()
        info['eco_rate'] = Planet.eco_rate
                    
            

        
        
    