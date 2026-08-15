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


def validate_action(action_data: str) -> bool:
    try:
        action_type, planet_id, argument = action_data.split(':')
        int(planet_id)
        if argument != 'None':
            int(argument)
        ActionType(action_type)
        return True
    except Exception: # noqa: BLE001
        return False

def get_action_data(action: Action) -> str:
    return f'{action.action_type}:{action.planet_id}:{action.argument}'

def get_action_from_data(action_data: str) -> Action:
    action_type, planet_id, argument = action_data.split(':')
    return Action(
        action_type=action_type,
        planet_id=int(planet_id),
        argument=None if argument == 'None' else int(argument),
    )
