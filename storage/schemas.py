from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict


class BaseDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageType(StrEnum):
    CITY = auto()
    METEORITES = auto()
    SANCTIONS = auto()
    ECO = auto()
    NEGOTIATIONS = auto()
    ATTACK = auto()


class OrderInfo(BaseModel):
    shielded: list[int]
    developed: list[int]
    sanctions: list[int]
    created: int
    is_invented: bool
    eco_boost: bool
    attacked: list[int]


INFO_MESSAGE_TYPES = (
    MessageType.CITY,
    MessageType.METEORITES,
    MessageType.SANCTIONS,
    MessageType.ECO
)

PLANET_MESSAGE_TYPES = (
    MessageType.NEGOTIATIONS,
    MessageType.ATTACK
)
