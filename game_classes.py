from functools import reduce
from typing import List


class City:
    def __init__(self, name):
        #self.__rate_of_life = 57  # уровень жизни, в начале игры у каждого города по 57%
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
    
    def rate_of_life(self, eco_rate: int):
        return self.__development * eco_rate 
        

class Planet:
    def __init__(self, name, cities: List[City]):
        self.__name = name
        self.__city = cities
        self.__sanctions = []
        self.__balance = 1000
        self.__eco_rate = 100 # должна быть статичной
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
        total_rate_of_life = reduce(lambda x, y: x.rate_of_life() + y.rate_of_life(), self.__city) # здесь ошибка, неправильно видимо использую reduce
        for i in range(len(self.__city)):
            rate_of_life_in_cities[self.__city[i]] = self.__city[i].rate_of_life()
        return {'cities': len(self.__city), 'rate_of_life_in_cities': rate_of_life_in_cities, 'total_rate_of_life': total_rate_of_life, 'ecology_rate': self.__eco_rate}

    def info(self):
        pass
  
      
class Game:
    def __init__(self, planets_quantity: int):
        self.planets_quantity = planets_quantity
        self.planets = []
        with open('preset.txt', "r") as file:
            lines = file.readlines()[:planets_quantity + 1]
            for line in lines:
                cities = []
                for i in range(4):
                    cities.append(City(line.split()[i]))
                self.planets.append(Planet(line.split()[0], cities))
        self.round = 0
        self.total_eco_rate = [100] # индекс == номер раунда
        # self.total_eco_rate[0] = 100 
        self.stats = {}
        for i in range(planets_quantity):
            self.stats[self.planets[i]] = self.planets[i].stats()
    