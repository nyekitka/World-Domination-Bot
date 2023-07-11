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
        

class Planet:
    def __init__(self, cities = []):
        self.__city = cities
        self.sanctions = []
        self.__balance = 1000
        self.__eco_rate = 100
        self.__metiorites = 0
        self.__is_invented = False
    
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
            