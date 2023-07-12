from functools import reduce
from typing import List


class City:
    def __init__(self, name):
        self.__rate_of_life = 100
        self.__shield = 0
        self.__name = name
        
    def build_shield(self): # построение щита
        self.__shield += 1

    def attacked(self):
        if self.__shield != 0:
            self.__shield -= 1
        else:
            self.__rate_of_life = 0
    
    def develop_rate(self):
        self.__rate_of_life += 25
    
    def rate_of_life(self):
        return self.__rate_of_life
        

class Planet:
    def __init__(self, name, cities: List[City] = []):
        self.__name = name
        self.__city = cities
        self.sanctions = []
        self.__balance = 1000
        self.__eco_rate = 100
        self.__metiorites = 0
        self.__is_invented = False
    
    def name(self):
        return self.__name
    
    def invent(self):
        if self.__balance >= 1000:
            self.__is_invented = True
            self.__balance -= 1000
        
    def create_meteorite(self): # обработка, если не изобретено
        if self.__is_invited and self.balance >= 150: 
            self.__meteorites += 1
            self.__balance -= 150
            
    def cancel_meteorite(self):
        self.__meteorites -= 1
        self.__balance += 150
        
    def eco(self):
        if self.__balance >= 200:
            self.__balance -= 200
            # self.__eco = ... что делаем с экологией

    def stats(self): # та, стата, которая должна показываться всем
        rate_of_life_in_cities = {}
        for i in range(len(self.__city)):
            rate_of_life_in_cities[self.__city[i].name()] = self.__city[i].rate_of_life()
        return {'cities': len(self.__city), 'rate_of_life_in_cities': rate_of_life_in_cities, 'total_rate_of_life': reduce(lambda x, y: x.rate_of_life() + y.rate_of_life(), self.__city), 'ecology_rate': self.__eco_rate}

class Game:
    def __init__(self, planets_quantity):
        self.planets_quantity = planets_quantity
        self.planet = []
        with open('preset.txt', "r") as file:
            lines = file.readlines()[:planets_quantity + 1]
            for line in lines:
                self.planet.append(Planet(line.split()[0]), line.split()[1:])
        self.raund = 0
        self.stats = {}
        self.total_eco_rate = [] # индекс == номер раунда
        self.total_eco_rate[0] = 100 
        for i in range(planets_quantity):
            self.stats[self.planet[i].name()] = self.planet[i].stats()
            