import psycopg2
import json
from typing import Optional
import pandas as pd

__exceptions_file = open('presets/exception codes.json', encoding='utf-8')
errors = json.load(__exceptions_file)

class CDException(Exception):
    """
    Special exception for the game.
    """
    def __init__(self, code: str) -> None:
        super().__init__()
        self.code = code
    
    def __str__(self) -> str:
        return errors[self.code]

class User:
    """
    Representation of user and admin in game. Works like a wrapper of sql queries.
    """

    def __init__(self, id: int, conn: psycopg2.extensions.connection):
        self.id = id
        self.__conn = conn
        self.__cursor = self.__conn.cursor()
    
    @classmethod
    def init_with_check(cls, id : int, conn: psycopg2.extensions.connection):
        cursor = conn.cursor()
        cursor.execute("""SELECT EXISTS(SELECT * FROM "User" WHERE tgid=%s)""", (id,))
        if cursor.fetchone()[0]:
            return cls(id, conn)
        else:
            cursor.execute("""SELECT EXISTS(SELECT * FROM Admins WHERE tgid=%s)""", (id,))
            if cursor.fetchone()[0]:
                return cls(id, conn)
            else:
                return None
    
    @classmethod
    def make_new_user(cls, id: int, isadmin: bool, conn: psycopg2.extensions.connection):
        cursor = conn.cursor()
        if isadmin:
            cursor.execute("""INSERT INTO Admins(tgid) VALUES (%s)""", (id,))
        else:
            cursor.execute("""INSERT INTO "User"(tgid) VALUES (%s)""", (id,))
        conn.commit()
        return cls(id, conn)
    
    def is_admin(self) -> bool:
        """
        Checks whether the user is admin.
        """
        self.__cursor.execute("""SELECT EXISTS(SELECT * FROM Admins WHERE tgid=%s)""", (self.id,))
        return self.__cursor.fetchone()[0]
    
    def game(self):
        """
        Returns a game that user is in.
        """
        if self.is_admin():
            self.__cursor.execute("""SELECT gameid FROM Admins WHERE tgid=%s""", (self.id, ))
        else:
            self.__cursor.execute("""SELECT gameid FROM "User" WHERE tgid=%s""", (self.id, ))
        gameid = self.__cursor.fetchone()[0]
        return gameid if gameid is None else Game(gameid, self.__conn)

    def kick_user(self) -> None:
        """
        Kicks user from the lobby
        """
        isadmin = self.is_admin()
        try:
            if isadmin:
                self.__cursor.execute("CALL Kick_admin(%s::BIGINT)", (self.id,))
            else:
                self.__cursor.execute("CALL Kick_user(%s::BIGINT)", (self.id,))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex
    

class City:
    """
    Representation of city in game. Works like a wrapper of sql queries.
    """

    def __init__(self, id: int, conn: psycopg2.extensions.connection):
        self.id = id
        self.__conn = conn
        self.__cursor = conn.cursor()

    @classmethod
    def init_with_check(cls, id : int, conn: psycopg2.extensions.connection):
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS(SELECT * FROM City WHERE id=%s)", (id,))
        if cursor.fetchone()[0]:
            return cls(id, conn)
        else:
            return None

    @classmethod
    def make_new_city(cls, name: str, planetid: int, conn: psycopg2.extensions.connection):
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM City")
        id = cursor.fetchone()[0] + 1
        cursor.execute("INSERT INTO City(id, name, planetid) VALUES (%s, %s, %s)", (id, name, planetid))
        conn.commit()
        return cls(id, conn)

    def __eq__(self, other):
        return self.id == other.id

    def build_shield(self) -> None:
        """
        Building a shield under the city if it doesn't exists.
        """
        self.__cursor.execute("UPDATE city SET isshielded=TRUE WHERE id=%s", (self.id,))
        self.__conn.commit()
    
    def name(self) -> str:
        """
        Returns name of the city.
        """

        self.__cursor.execute("SELECT name FROM city WHERE id=%s", (self.id,))
        return self.__cursor.fetchone()[0]

    def planet(self):
        """
        Returns the planet where the city is located.
        """

        self.__cursor.execute("SELECT planetid FROM city WHERE id=%s", (self.id, ))
        return Planet(self.__cursor.fetchone()[0], self.__conn)
    
    def develop(self) -> None:
        """
        Develops the city
        """

        self.__cursor.execute("UPDATE city SET development=development+20 WHERE id=%s", (self.id,))
        self.__conn.commit()
    
    def is_under_shield(self) -> bool:
        """
        Returns whether the city is shielded
        """

        self.__cursor.execute("SELECT isshielded FROM city WHERE id=%s", (self.id,))
        return self.__cursor.fetchone()[0]
    
    def rate_of_life(self) -> int:
        """
        Returns its rate of life
        """

        self.__cursor.execute("""SELECT Rate_of_life_in_city(%s)""", (self.id, ))
        return int(self.__cursor.fetchone()[0])
        
    def development(self) -> int:
        """
        Returns its development
        """

        self.__cursor.execute("SELECT development FROM city WHERE id = %s", (self.id, ))
        return int(self.__cursor.fetchone()[0])
    
    def income(self) -> None:
        """
        Returns its income in the round
        """

        return 3*self.rate_of_life()


class Planet:
    """
    Representation of the planet in game. Works like a wrapper of sql queries.
    """

    def __init__(self, planetid: int, conn: psycopg2.extensions.connection):
        self.id = planetid
        self.__conn = conn
        self.__cursor = conn.cursor()

    @classmethod
    def init_with_check(cls, id : int, conn: psycopg2.extensions.connection):
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS(SELECT * FROM Planet WHERE id=%s)", (id,))
        if cursor.fetchone()[0]:
            return cls(id, conn)
        else:
            return None

    @classmethod
    def make_new_planet(cls, name: str, gameid: int, conn: psycopg2.extensions.connection):
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM Planet");
        id = cursor.fetchone()[0] + 1
        cursor.execute("INSERT INTO Planet(id, name, gameid) VALUES (%s, %s, %s)", (id, name, gameid))
        conn.commit()
        return cls(id, conn)

    def __eq__(self, other):
        return self.id == other.id

    def name(self) -> str:
        """
        Returns name of the planet.
        """

        self.__cursor.execute("SELECT name FROM planet WHERE id=%s", (self.id,))
        return self.__cursor.fetchone()[0]
    
    def user_id(self) -> int:
        """
        Returns id of the owner of the planet.
        """

        self.__cursor.execute("SELECT ownerid FROM planet WHERE id=%s", (self.id,))
        return self.__cursor.fetchone()[0]
    
    def game_id(self) -> int:
        """
        Returns id of the game which this planet belongs to.
        """

        self.__cursor.execute("SELECT gameid FROM planet WHERE id=%s", (self.id,))
        return self.__cursor.fetchone()[0]

    def cities(self, nondestroyed:bool = True) -> list[City]:
        """
        Returns the list of non-destroyed cities on the planet
        """
        if nondestroyed:  
            self.__cursor.execute("SELECT id FROM city WHERE planetid=%s AND development > 0", (self.id,))
        else:
            self.__cursor.execute("SELECT id FROM city WHERE planetid=%s", (self.id, ))
        ls = self.__cursor.fetchall()
        if ls is None:
            ls = []
        return list(map(lambda x: City(x[0], self.__conn), ls))
    
    def balance(self) -> int:
        """
        Returns balance of the planet
        """

        self.__cursor.execute("SELECT balance FROM Planet WHERE id=%s", (self.id,))
        return int(self.__cursor.fetchone()[0])
    
    def game(self):
        """
        Returns a game that the planet belongs to
        """
        self.__cursor.execute("SELECT gameid FROM Planet WHERE id=%s", (self.id, ))
        gameid = self.__cursor.fetchone()[0]
        return Game(gameid, self.__conn)

    def is_invented(self) -> bool:
        """
        Returns balance of the planet
        """

        self.__cursor.execute("SELECT isinvented FROM Planet WHERE id=%s", (self.id,))
        return self.__cursor.fetchone()[0]

    def accept_diplomatist_from(self, planet) -> None:
        """
        Checks if it's possible for the planet to accept diplomatists from provided planet.
        If it's not then an exception is raised. Else state of the planet changes.
        """
        game_id = self.game_id()
        try:
            self.__cursor.execute("INSERT INTO Negotiations(GameID, PlanetFrom, PlanetTo) VALUES (%s, %s, %s)",
                              (game_id, planet.id, self.id))
            self.__conn.commit()
        except psycopg2.DatabaseError as err:
            self.__conn.rollback()
            if 'gamestatechecker' in err.pgerror:
                raise CDException('NEO') from err
            elif 'bilateralconstraint' in err.pgerror:
                raise CDException('BLN') from err
            elif 'business' in err.pgerror:
                raise CDException('BAM') from err
    
    def end_negotiations(self) -> None:
        """
        Ends negotiations that are taking place in this planet.
        """
        self.__cursor.execute("DELETE FROM Negotiations WHERE PlanetTo = %s", (self.id, ))
        self.__cursor.execute("DELETE FROM PlanetMessages WHERE ownerid=%s AND mtype=%s", (self.id, 'Negotiations'))
        self.__conn.commit()

    def invent(self) -> None:
        """
        Adding to order of the planet invention of nuclear development
        """
        try:
            self.__cursor.execute("CALL INVENT(%s)", (self.id, ))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex

    def is_invent_in_order(self) -> bool:
        """
        Checks whether invention of meteorites is in the order.
        """
        self.__cursor.execute("SELECT EXISTS(SELECT * FROM Orders WHERE action='Invent' AND planetid=%s AND round=%s)", (self.id, self.game().show_round()))
        return self.__cursor.fetchone()[0]

    def meteorites(self) -> int:
        """
        Returns the number of meteorites that the planet has.
        """

        self.__cursor.execute("SELECT meteorites FROM Planet WHERE id=%s", (self.id,))
        return int(self.__cursor.fetchone()[0])

    def create_meteorites(self, n: int) -> None:
        """
        Adds creation of n meteorites to the order if it's possible
        """
        try:
            self.__cursor.execute("CALL Create_Meteorites(%s, %s)", (self.id, n))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex
    
    def number_of_ordered_meteorites(self) -> int:
        """
        Returns a number of ordered meteorites.
        """
        nround = self.game().show_round()
        self.__cursor.execute("SELECT COALESCE((SELECT argument FROM Orders o WHERE planetid=%s AND action='Create Meteorites' AND o.round=%s), 0)", 
                              (self.id, nround))
        return int(self.__cursor.fetchone()[0])
    
    def attack(self, city_id: int) -> None:
        """
        Adds to the order attack on the provided city
        """
        try:
            self.__cursor.execute("CALL Attack(%s, %s)", (self.id, city_id))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex
    
    def ordered_attack_cities(self, other_planet) -> list[City]:
        """
        Returns a list of all cities of provided planet that are in order for attack.
        """
        nround = self.game().show_round()
        self.__cursor.execute("""SELECT c.id FROM City c
                              JOIN Orders o ON o.argument=c.id
                              WHERE o.action='Attack' AND o.planetid=%s AND c.planetid=%s AND o.round=%s""", 
                              (self.id, other_planet.id, nround))
        result = self.__cursor.fetchall()
        if result is None:
            return []
        else:
            return list(map(lambda x: City(x[0], self.__conn), result))
    
    def ordered_attack_all_cities(self) -> list[City]:
        """
        Returns a list of all cities that are in order for attack.
        """
        nround = self.game().show_round()
        self.__cursor.execute("""SELECT c.id FROM City c
                              JOIN Orders o ON o.argument=c.id
                              WHERE o.action='Attack' AND o.planetid=%s AND o.round=%s""", 
                              (self.id, nround))
        result = self.__cursor.fetchall()
        if result is None:
            return []
        else:
            return list(map(lambda x: City(x[0], self.__conn), result))

    def ordered_shield_cities(self) -> list[City]:
        nround = self.game().show_round()
        self.__cursor.execute("SELECT c.id FROM City c JOIN Orders o ON c.id = o.argument WHERE o.action = 'Shield' AND o.round = %s", (nround,))
        results = self.__cursor.fetchall()
        if results is None:
            return []
        else:
            return list(map(lambda x: City(x[0], self.__conn), results))

    def develop_city(self, city_id: int):
        """
        Adding development of the provided city to the order
        """
        try:
            self.__cursor.execute("CALL Develop(%s, %s)", (self.id, city_id))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex

    def developed_cities(self) -> list[City]:
        """
        Returns a list of cities that are ordered to develop
        """
        nround = self.game().show_round()
        self.__cursor.execute("SELECT c.id FROM City c JOIN Orders o ON c.id = o.argument WHERE o.action = 'Develop' AND o.round=%s", (nround, ))
        results = self.__cursor.fetchall()
        if results is None:
            return []
        else:
            return list(map(lambda x: City(x[0], self.__conn), results))
    
    def eco_boost(self):
        """
        Adds to the order sending a meteorite to the anomaly.
        """
        try:
            self.__cursor.execute("CALL EcoBoost(%s)", (self.id,))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex
    
    def is_planned_eco_boost(self):
        """
        Checks whether the eco boost is ordered.
        """
        self.__cursor.execute("SELECT EXISTS(SELECT * FROM Orders WHERE action='Eco boost' AND planetid=%s AND round=%s)", (self.id, self.game().show_round()))
        return self.__cursor.fetchone()[0]

    def rate_of_life(self) -> int:
        """
        Returns the rate of life on the planet which is average of rates of life in cities of the planet.
        """
        self.__cursor.execute("SELECT Rate_of_life_in_planet(%s)", (self.id,))
        return int(self.__cursor.fetchone()[0])

    def income(self) -> int:  # доход
        """
        Returns the income of the planet for the round
        """
        self.__cursor.execute("SELECT Planet_income(%s)", (self.id,))
        return int(self.__cursor.fetchone()[0])
    
    def add_money(self, income: int) -> None:
        """
        Adding income to the planet's balance
        """
        self.__cursor.execute("UPDATE Planet SET balance = balance + %s WHERE id = %s", (income, self.id))
        self.__conn.commit()
    
    def send_sanctions(self, planet_id: int) -> None:
        """
        Sending sanctions from one planet to another.
        """
        try:
            self.__cursor.execute("CALL Send_Sanctions(%s, %s)", (self.id, planet_id))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex
    
    def get_sanc_set(self) -> list[str]:
        """
        Returns a list of all planets that applied sanctions to the planet in the previous round.
        """
        self.__cursor.execute("SELECT p.name FROM Sanctions s JOIN Planet p ON p.id=s.planetfrom WHERE s.PlanetTo = %s",
                              (self.id,))
        result = self.__cursor.fetchall()
        if result is None:
            return []
        else:
            return [x[0] for x in result]
    
    def ordered_sanctions_list(self):
        """
        Returns a list of all planets that will be sanctioned.
        """
        self.__cursor.execute("""SELECT argument FROM Orders WHERE action='Sanctions' AND
                              planetid=%s AND round=%s""", (self.id, self.game().show_round()))
        results = self.__cursor.fetchall()
        if results is None:
            return []
        else:
            return list(map(lambda x: City(x[0], self.__conn), results))

    def build_shield(self, city_id: int) -> None:
        """
        Adds to order building a shield under the city if it's possible
        """
        try:
            self.__cursor.execute("CALL Build_Shield(%s, %s)", (self.id, city_id))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex
    
    def shielded_cities(self) -> list[City]:
        """
        Returns a list of all shielded cities.
        """
        self.__cursor.execute("SELECT id FROM City WHERE planetid=%s AND isshielded", (self.id, ))
        result = self.__cursor.fetchall()
        if result is None:
            return []
        else:
            return list(map(lambda x: City(x[0], self.__conn), result))
                
    def transfer(self, planet_id : int, money: int) -> None:
        """
        Transfers provided amount of money from the planet to given
        """
        try:
            self.__cursor.execute("CALL Transfer(%s, %s, %s)", (self.id, planet_id, money))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex


class Game:
    """
    Representation of the lobby in game. Works like a wrapper of sql queries.
    """

    def __init__(self, id: int, conn: psycopg2.extensions.connection):
        self.id = id
        self.__conn = conn
        self.__cursor = conn.cursor()
    
    @classmethod
    def init_with_check(cls, id : int, conn: psycopg2.extensions.connection):
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS(SELECT * FROM Game WHERE id=%s)", (id,))
        if cursor.fetchone()[0]:
            return cls(id, conn)
        else:
            return None
        
    @classmethod
    def make_new_game(cls, planets: int, conn: psycopg2.extensions.connection):
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM Game")
        id = cursor.fetchone()[0] + 1
        cursor.execute("INSERT INTO Game(id, planets) VALUES (%s, %s)", (id, planets))
        conn.commit()
        return cls(id, conn)

    @classmethod
    def all_games(cls, conn: psycopg2.extensions.connection):
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Game")
        result = cursor.fetchall()
        if result is None:
            return []
        else:
            return [Game(x[0], conn) for x in result]

    def __eq__(self, other):
        return self.id == other.id

    def join_user(self, user_id: int) -> None:
        """
        Adds given user to the game
        """
        try:
            self.__cursor.execute("CALL Join_User(%s, %s)", (user_id, self.id))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex
    
    def join_admin(self, user_id: int) -> None:
        """
        Adds given user to the game
        """
        try:
            self.__cursor.execute("CALL Join_Admin(%s, %s)", (self.id, user_id))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex

    def admins_list(self) -> list[User]:
        """
        Returns a list of all admins of the game.
        """
        self.__cursor.execute("""SELECT tgid FROM Admins WHERE gameid=%s""", (self.id, ))
        admins_list = self.__cursor.fetchall()
        if admins_list is None:
            return []
        else:
            return list(map(lambda x: User(x[0], self.__conn), admins_list))

    def planets(self) -> list[Planet]:
        """
        Returns a list of all planets in the game.
        """
        self.__cursor.execute("SELECT id FROM Planet WHERE gameid=%s", (self.id, ))
        result = self.__cursor.fetchall()
        return list(map(lambda x: Planet(x[0], self.__conn), result))
        
    def number_of_planets(self) -> int:
        """
        Returns the number of the planets in the game.
        """
        self.__cursor.execute("SELECT planets FROM Game WHERE id=%s", (self.id,))
        return self.__cursor.fetchone()[0]
    
    def active_users(self) -> list[User]:
        """
        Returns a list of users in the lobby.
        """
        self.__cursor.execute("""SELECT tgid FROM "User" WHERE gameid=%s""", (self.id,))
        res = self.__cursor.fetchall()
        if res is None:
            return []
        else:
            return [User(x[0], self.__conn) for x in res]

    def get_homeland(self, user_id: int) -> Optional[Planet]:
        """
        Returns a planet of the user
        """
        self.__cursor.execute("SELECT id FROM Planet WHERE ownerid = %s AND gameid=%s", (user_id, self.id))
        res = self.__cursor.fetchone()
        if res is None:
            return None
        else:
            return Planet(res[0], self.__conn)

    def is_all_active(self) -> bool:
        """
        Checks whether all planets have his owner online.
        """
        self.__cursor.execute("SELECT EXISTS(SELECT * FROM Planet WHERE gameid=%s AND ownerid IS NULL)", (self.id, ))
        return not self.__cursor.fetchone()[0]

    def exists(self) -> bool:
        self.__cursor.execute("SELECT EXISTS(SELECT * FROM Game WHERE id=%s)", (self.id, ))
        return self.__cursor.fetchone()[0]

    def show_round(self) -> Optional[int]:
        """
        Return a number of the round in the game if it's active and -1 if it's inactive.
        """
        self.__cursor.execute("SELECT COALESCE(round, -1) FROM Game WHERE id=%s", (self.id,))
        return self.__cursor.fetchone()[0]
    
    def start_new_round(self) -> None:
        """
        Starts a new round
        """
        try:
            self.__cursor.execute("CALL Start_new_round(%s)", (self.id, ))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex
    
    def end_this_round(self) -> None:
        """
        Ends this round
        """
        try:
            self.__cursor.execute("CALL End_this_round(%s)", (self.id, ))
            self.__conn.commit()
        except psycopg2.DatabaseError as ex:
            self.__conn.rollback()
            raise CDException(ex.pgcode) from ex
        
    def end_game(self) -> None:
        self.__cursor.execute("CALL end_game(%s)", (self.id,))
        self.__conn.commit()

    def eco_rate(self) -> int:
        """
        Returns an eco rate of the game.
        """
        self.__cursor.execute("SELECT ecorate FROM Game WHERE id=%s", (self.id, ))
        return self.__cursor.fetchone()[0]
    
    def status(self) -> str:
        """
        Returns status of the game.
        """
        self.__cursor.execute("SELECT status FROM Game WHERE id=%s", (self.id, ))
        return self.__cursor.fetchone()[0]
    
    def extract_orders_data(self, path: str) -> None:
        writer = pd.ExcelWriter(path)
        planets = self.planets()
        max_round = 6
        for nround in range(1, max_round + 1):
            df = pd.DataFrame(columns=list(map(lambda x: x.name(), planets)),
                          index=['Развить города', 
                                 'Построить щит над', 
                                 'Изобрести технологию отправки метеоритов', 
                                 'Закупить метеориты', 
                                 'Отправить метеорит в аномалию', 
                                 'Наложить санкции на', 
                                 'Атаковать'])
            for planet in planets:
                # adding develop info
                self.__cursor.execute("""SELECT c.name FROM Orders o
                                      JOIN City c ON c.id=o.argument
                                      WHERE action='Develop' AND o.planetid=%s AND o.round=%s""", (planet.id, nround))
                result = self.__cursor.fetchall()
                if result is None:
                    result = []
                developed_cities = list(map(lambda x: x[0], result))
                df.loc['Развить города', planet.name()] = ', '.join(developed_cities)

                # adding shield info
                self.__cursor.execute("""SELECT c.name FROM Orders o
                                      JOIN City c ON c.id=o.argument
                                      WHERE action='Shield' AND o.planetid=%s AND o.round=%s""", (planet.id, nround))
                result = self.__cursor.fetchall()
                if result is None:
                    result = []
                shielded_cities = list(map(lambda x: x[0], result))
                df.loc['Построить щит над', planet.name()] = ', '.join(shielded_cities)

                # adding invention info
                self.__cursor.execute("""SELECT o.round FROM Orders o WHERE o.action='Invent' AND o.planetid=%s""", (planet.id,))
                invention_round = self.__cursor.fetchone()
                if invention_round is None:
                    invention_round = max_round + 1
                else:
                    invention_round = invention_round[0]
                if invention_round < nround:
                    df.loc['Изобрести технологию отправки метеоритов', planet.name()] = 'Уже изобретена'
                elif invention_round == nround:
                    df.loc['Изобрести технологию отправки метеоритов', planet.name()] = 'Да'
                else:
                    df.loc['Изобрести технологию отправки метеоритов', planet.name()] = 'Нет'
                
                # adding creation info
                self.__cursor.execute("SELECT o.argument FROM Orders o WHERE o.round=%s AND o.planetid=%s AND o.action='Create Meteorites'",
                                      (nround, planet.id))
                num_created = self.__cursor.fetchone()
                if num_created is None:
                    num_created = 0
                else:
                    num_created = num_created[0]
                df.loc['Закупить метеориты', planet.name()] = str(num_created)

                # adding eco boost info
                self.__cursor.execute("SELECT EXISTS(SELECT * FROM Orders WHERE action='Eco boost' AND round=%s AND planetid=%s)",
                                      (nround, planet.id))
                is_boosted = self.__cursor.fetchone()[0]
                df.loc['Отправить метеорит в аномалию', planet.name()] = 'Да' if is_boosted else 'Нет'

                # sanctions info
                self.__cursor.execute("SELECT o.argument FROM Orders o WHERE o.action='Sanctions' AND o.planetid=%s AND o.round=%s",
                                      (planet.id, nround))
                sanctions_list = self.__cursor.fetchall()
                if sanctions_list is None:
                    sanctions_list = []
                else:
                    sanctions_list = [Planet(x[0], self.__conn).name() for x in sanctions_list]
                df.loc['Наложить санкции на', planet.name()] = ', '.join(sanctions_list)

                # attack cities
                self.__cursor.execute("SELECT o.argument FROM Orders o WHERE o.action='Attack' AND o.planetid=%s AND o.round=%s",
                                      (planet.id, nround))
                attacked_list = self.__cursor.fetchall()
                if attacked_list is None:
                    attacked_list = []
                else:
                    attacked_list = [City(x[0], self.__conn).name() for x in attacked_list]
                df.loc['Атаковать', planet.name()] = ', '.join(attacked_list)
            df.to_excel(writer, f'{nround} раунд')
        writer.close()

    def get_all_messages(self) -> list[tuple[int]]:
        """
        Returns all message ids with author ids that was sent to the users of the game.
        """
        self.__cursor.execute("""SELECT im.id, p.ownerid FROM InfoMessages im 
                              JOIN Planet p ON p.id=im.planetid
                              WHERE p.gameid=%s""", (self.id, ))
        res = self.__cursor.fetchall()
        if res is None:
            res = []
        self.__cursor.execute("""SELECT pm.messageid, p.ownerid FROM PlanetMessages pm
                              JOIN Planet p ON p.id = pm.ownerid WHERE p.gameid=%s""", (self.id, ))
        res1 = self.__cursor.fetchall()
        if res1 is None:
            res1 = []
        return res + res1
    
    def delete_all_messages(self) -> None:
        """
        Deletes all messages with information about this round.
        """
        self.__cursor.execute("""DELETE FROM InfoMessages WHERE planetid IN 
                              (SELECT id FROM Planet WHERE gameid=%s)""", (self.id, ))
        self.__cursor.execute("""DELETE FROM PlanetMessages WHERE planetid IN
                              (SELECT id FROM Planet WHERE gameid=%s)""", (self.id, ))
        self.__conn.commit()
        return
    
    def get_all_user_messages(self, user: User) -> list[int]:
        """
        Returns all ids of the messages of the user sent to him.
        """
        self.__cursor.execute("""SELECT im.id FROM InfoMessages im
                              JOIN Planet p ON p.id=im.planetid
                              WHERE p.ownerid=%s""", (user.id,))
        res = self.__cursor.fetchall()
        if res is None:
            res = []
        self.__cursor.execute("""SELECT pm.messageid FROM PlanetMessages pm
                              JOIN Planet p ON p.id = pm.ownerid WHERE p.ownerid=%s""", (user.id, ))
        res1 = self.__cursor.fetchall()
        if res1 is None:
            res1 = []
        result = res + res1
        return [x[0] for x in result]
    
    def delete_all_user_messages(self, user: User) -> None:
        """
        Deletes all messages with information about this round.
        """
        self.__cursor.execute("""DELETE FROM InfoMessages WHERE planetid IN 
                              (SELECT id FROM Planet WHERE ownerid=%s)""", (user.id, ))
        self.__cursor.execute("""DELETE FROM PlanetMessages WHERE planetid IN
                              (SELECT id FROM Planet WHERE ownerid=%s)""", (user.id, ))
        self.__conn.commit()
        return