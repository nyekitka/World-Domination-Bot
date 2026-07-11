from redis import Redis

from game.schemas import FailureReason, OrderType
from game.config import GameConfig
from storage.clients.base import BaseClient


class ActionsClient(BaseClient):
    MONEY_KEY = 'money_balance'
    METEORITES_KEY = 'meteorites_balance'

    def __init__(self, client: Redis, ex: int, game_config: GameConfig):
        super().__init__(client, ex)
        self.game_config = game_config

    def _edit_planet_binary_relation(
        self,
        relation: OrderType,
        balance_key: str,
        cost: int,
        planet_id: int,
        other_id: int,
    ) -> FailureReason:
        balance = self.get_balance(planet_id, balance_key)

        if self.sismember(other_id, relation, planet_id):
            self.set_balance(planet_id, balance + cost, balance_key)
            self.sdel([other_id], relation, planet_id)
        else:
            result = self.set_balance(planet_id, balance - cost, balance_key)
            if result != FailureReason.SUCCESS:
                return result
            self.sadd([other_id], relation, planet_id)
        
        return FailureReason.SUCCESS
    
    def _edit_planet_unary_relation(
        self,
        relation: OrderType,
        balance_key: str,
        cost: int,
        planet_id: int,
    ) -> FailureReason:
        record = self.get(relation, planet_id)
        balance = self.get_balance(planet_id, balance_key)
        if record is not None and int(record):
            result = self.set_balance(
                planet_id,
                balance + cost,
                balance_key
            )
            self.delete(relation, planet_id)
        else:
            result = self.set_balance(
                planet_id,
                balance - cost,
                balance_key
            )
            if result != FailureReason.SUCCESS:
                return result
            self.set(1, relation, planet_id)
        return result
    
    def _get_planet_binary_relation(
        self, relation: OrderType, planet_id: int
    ) -> list[int]:
        members = self.smembers(relation, planet_id)
        return list(map(int, members))
    
    def shield_city(self, planet_id: int, city_id: int) -> FailureReason:
        return self._edit_planet_binary_relation(
            relation=OrderType.SHIELD,
            balance_key=self.MONEY_KEY,
            cost=self.game_config.SHIELD_COST,
            planet_id=planet_id,
            other_id=city_id,
        )
    
    def get_shielded_cities(self, planet_id: int) -> list[int]:
        return self._get_planet_binary_relation(OrderType.SHIELD, planet_id)
    
    def develop_city(self, planet_id: int, city_id: int) -> FailureReason:
        return self._edit_planet_binary_relation(
            relation=OrderType.DEVELOP,
            balance_key=self.MONEY_KEY,
            cost=self.game_config.DEVELOPMENT_COST,
            planet_id=planet_id,
            other_id=city_id,
        )
    
    def get_developed_cities(self, planet_id: int) -> list[int]:
        return self._get_planet_binary_relation(OrderType.DEVELOP, planet_id)
    
    def attack_city(self, planet_id: int, city_id: int) -> FailureReason:
        return self._edit_planet_binary_relation(
            relation=OrderType.ATTACK,
            balance_key=self.METEORITES_KEY,
            cost=self.game_config.ATTACK_COST,
            planet_id=planet_id,
            other_id=city_id,
        )
    
    def get_attacked_cities(self, planet_id: int) -> list[int]:
        return self._get_planet_binary_relation(OrderType.ATTACK, planet_id)
    
    def sanction_planet(self, planet_id: int, other_planet_id: int) -> FailureReason:
        return self._edit_planet_binary_relation(
            relation=OrderType.SANCTIONS,
            balance_key=self.MONEY_KEY,
            cost=self.game_config.SANCTIONS_COST,
            planet_id=planet_id,
            other_id=other_planet_id,
        )
    
    def get_sanctioned_planets(self, planet_id: int) -> list[int]:
        return self._get_planet_binary_relation(OrderType.SANCTIONS, planet_id)
    
    def create_meteorites(self, planet_id: int, meteorites_num: int) -> FailureReason:
        balance = self.get_balance(planet_id, self.MONEY_KEY)
        chosen_meteorites = self.get(OrderType.CREATE, planet_id)
        if chosen_meteorites:
            chosen_meteorites = int(chosen_meteorites)
        else:
            chosen_meteorites = 0
        result = self.set_balance(
            planet_id,
            balance - (meteorites_num - chosen_meteorites) * self.game_config.CREATE_COST,
            self.MONEY_KEY
        )
        if result != FailureReason.SUCCESS:
            return result
        
        self.set(meteorites_num, OrderType.CREATE, planet_id)
        return result
    
    def get_created_meteorites(self, planet_id: int) -> int:
        result = self.get(OrderType.CREATE, planet_id)
        if result is None:
            return 0
        
        return int(result)

    def invent(self, planet_id: int) -> FailureReason:
        return self._edit_planet_unary_relation(
            OrderType.INVENT,
            self.MONEY_KEY,
            self.game_config.INVENTION_COST,
            planet_id
        )
    
    def get_invented(self, planet_id: int) -> bool:
        return self.get(OrderType.INVENT, planet_id) == '1'
    
    def eco_boost(self, planet_id: int) -> FailureReason:
        return self._edit_planet_unary_relation(
            OrderType.ECO,
            self.METEORITES_KEY,
            self.game_config.ECO_COST,
            planet_id
        )
    
    def get_eco_boost(self, planet_id: int) -> bool:
        return self.get(OrderType.ECO, planet_id) == '1'

    def make_negotiations(self, planet_from: int, planet_to: int) -> FailureReason:
        if self.exists(OrderType.NEGOTIATE, planet_from):
            return FailureReason.ALREADY_NEGOTIATING
        
        side_negotiator = self.get(OrderType.NEGOTIATE, planet_to)
        if side_negotiator is not None and int(side_negotiator) == planet_from:
            return FailureReason.BILATERAL_NEGOTIATIONS
        
        self.set(planet_to, OrderType.NEGOTIATE, planet_from)
        return FailureReason.SUCCESS
    
    def end_negotiations(self, planet_from: int) -> None:
        self.delete(OrderType.NEGOTIATE, planet_from)
    
    def get_balance(self, planet_id: int, balance_key: str) -> int:
        balance = self.get(balance_key, planet_id)
        return int(balance)
    
    def set_balance(
        self, planet_id: int, balance: int, balance_key: str
    ) -> FailureReason:
        if balance < 0:
            if balance_key == self.MONEY_KEY:
                return FailureReason.NOT_ENOUGH_MONEY
            else:
                return FailureReason.NOT_ENOUGH_METEORITES
        
        self.set(balance, balance_key, planet_id)
        return FailureReason.SUCCESS
