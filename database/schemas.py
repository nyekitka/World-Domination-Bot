from enum import StrEnum, auto
from typing import Union

from pydantic import BaseModel, ConfigDict

from game.schemas import OrderType


class GameStatus(StrEnum):
    WAITING = auto()
    MEETING = auto()
    ROUND = auto()
    ENDED = auto()



class BaseDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GameDto(BaseDto):
    id: int
    status: GameStatus = GameStatus.WAITING
    ecorate: int = 95
    round: int | None = None
    num_planets: int


class PlayerDto(BaseDto):
    tg_id: int
    game_id: int | None = None


class AdminDto(BaseDto):
    tg_id: int
    game_id: int | None = None


class PlanetDto(BaseDto):
    id: int
    name: str
    game_id: int
    owner_id: int | None = None
    balance: int = 1000
    meteorites: int = 0
    is_invented: bool = False
    development: float | None = None


class CityDto(BaseDto):
    id: int
    name: str
    planet_id: int
    is_shielded: bool = False
    development: int = 60


class OrderDto(BaseDto):
    action: OrderType
    planet_id: int
    argument: int | None
    round: int


class SanctionDto(BaseDto):
    planet_from: int
    planet_to: int


class NegotiationDto(BaseDto):
    planet_from: int
    planet_to: int


UserDto = Union[PlayerDto, AdminDto]

