from enum import StrEnum, auto

from pydantic import BaseModel


class ActionType(StrEnum):
    ATTACK = auto()
    DEVELOP = auto()
    SHIELD = auto()
    CREATE = auto()
    ECO = auto()
    SANCTIONS = auto()
    INVENT = auto()
    NEGOTIATE = auto()
    TRANSACTION = auto()
    ACCEPT_NEGOTIATIONS = auto()
    REFUSE_NEGOTIATIONS = auto()
    END_NEGOTIATIONS = auto()


class Action(BaseModel):
    action_type: ActionType
    planet_id: int
    argument: int | None = None


def validate_action_json(json: str) -> bool:
    try:
        Action.model_validate_json(json)
        return True
    except ValueError:
        return False
