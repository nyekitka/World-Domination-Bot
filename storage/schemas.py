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
