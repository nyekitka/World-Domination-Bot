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
        self.__sanctions = set()    # список санкций на планете
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

    def income(self):  # доход
        sanc_coef = len(self.__sanctions) * 0.1
        res = 300 * self.rate_of_life_in_citie()
        if sanc_coef:
            res *= sanc_coef
        return res
             
    def get_sanctions(self, planet: str):  # прибавленение санкций, принимает название страны
        self.__sanctions.add(planet)
    
    def free_sanc_list(self):  # опустошение санкционного списка (перед началом нового раунда)
        self.__sanctions.clear()
        
    def build_shield(self, city_name: str):  # построение щита
        if self.__balance >= 300:
            for city in self.__city:
                if city.name() == city_name:
                    if city.is_under_shield():
                        raise Exception('Shield exists')
                    else:
                        city.build_shield()
                    break
                
    def transfer(self, money: int):
        if self.__balance >= money:
            self.__balance -= money
      
class Game:
    def __init__(self, planets_quantity: int):
        self.planets_quantity = planets_quantity                # количество планет
        self.planets = []                                       # список планет
        with open('preset.txt', "r") as file:                   # заполнение списка планет
            lines = file.readlines()[:planets_quantity + 1]
            for line in lines:
                cities = []
                for city_name in line.split()[1:]:
                    cities.append(City(city_name))
                self.planets.append(Planet(line.split()[0], cities))
        self.round = 0                                          # номер раунда
        
    