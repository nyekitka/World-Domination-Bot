from enum import StrEnum, auto
from typing import Union

from pydantic import BaseModel, ConfigDict


class GameStatus(StrEnum):
    WAITING = auto()
    MEETING = auto()
    ROUND = auto()
    ENDED = auto()


class MessageType(StrEnum):
    CITY = auto()
    METEORITES = auto()
    SANCTIONS = auto()
    ECO = auto()
    NEGOTIATIONS = auto()
    ATTACK = auto()


class OrderType(StrEnum):
    ATTACK = auto()
    DEVELOP = auto()
    SHIELD = auto()
    CREATE = auto()
    ECO = auto()
    SANCTIONS = auto()
    INVENT = auto()


class BaseDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GameDto(BaseDto):
    id: int
    status: GameStatus = GameStatus.WAITING
    ecorate: int = 95
    round: int | None = None


class PlayerDto(BaseDto):
    tg_id: int
    game_id: int


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


class CityDto(BaseDto):
    id: int
    name: str
    planet_id: int
    is_shielded: bool = False
    development: int = 60


class InfoMessageDto(BaseDto):
    id: int
    planet_id: int
    message_type: MessageType


class OrderDto(BaseDto):
    action: OrderType
    planet_id: int
    argument: int | None
    round: int


class PlanetMessageDto(BaseDto):
    owner_id: int
    planet_id: int
    message_id: int
    message_type: MessageType


class SanctionDto(BaseDto):
    planet_from: int
    planet_to: int


class NegotiationDto(BaseDto):
    planet_from: int
    planet_to: int


UserDto = Union[PlayerDto, AdminDto]


class FailureReason(StrEnum):
    SUCCESS = auto()
    UNTIMELY_NEGOTIATIONS = auto()
    PLANET_IS_BUSY = auto()
    BILATERAL_NEGOTIATIONS = auto()
    ALREADY_NEGOTIATING = auto()
    OBJECT_NOT_FOUND = auto()
    ALREADY_INVENTED = auto()
    NOT_ENOUGH_MONEY = auto()
    NOT_ENOUGH_PLAYERS = auto()
    NOT_ENOUGH_METEORITES = auto()
    NOT_IN_GAME = auto()
    NEGATIVE_AMOUNT = auto()
    IS_NOT_INVENTED = auto()
    SELF_ATTACK = auto()
    ROUND_IS_NOT_GOING = auto()
    ALREADY_IN_GAME = auto()
    GAME_ENDED = auto()
    GAME_IS_FULL = auto()
    CANNOT_START_ROUND = auto()
    DIFFERENT_GAMES = auto()
