from enum import StrEnum, auto


class OrderType(StrEnum):
    ATTACK = auto()
    DEVELOP = auto()
    SHIELD = auto()
    CREATE = auto()
    ECO = auto()
    SANCTIONS = auto()
    INVENT = auto()
    NEGOTIATE = auto()

ORDER_TYPE_TRANSLATIONS = {
    OrderType.ATTACK: 'Атаковать',
    OrderType.DEVELOP: 'Развить',
    OrderType.SHIELD: 'Защитить',
    OrderType.CREATE: 'Создать метеориты',
    OrderType.ECO: 'Отправить метеорит в аномалию',
    OrderType.SANCTIONS: 'Наложить санкции',
    OrderType.INVENT: 'Изобрести технологию',
}

OrderInfo = dict[OrderType, list[int] | int | bool]


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
    WAIT_TILL_GAME_ENDS = auto()
    STARTING_GAME_WITHOUT_BEING_IN = auto()


FAILURE_INTERPRETATIONS = {
    FailureReason.UNTIMELY_NEGOTIATIONS: 'untimely_negotiations',
    FailureReason.PLANET_IS_BUSY: 'planet_is_busy',
    FailureReason.BILATERAL_NEGOTIATIONS: 'bilateral_negotiations',
    FailureReason.ALREADY_NEGOTIATING: 'already_negotiating',
    FailureReason.OBJECT_NOT_FOUND: 'object_not_found',
    FailureReason.ALREADY_INVENTED: 'already_invented',
    FailureReason.NOT_ENOUGH_MONEY: 'not_enough_money',
    FailureReason.NOT_ENOUGH_PLAYERS: 'not_enough_players_short',
    FailureReason.NOT_ENOUGH_METEORITES: 'not_enough_meteorites',
    FailureReason.NOT_IN_GAME: 'not_in_game',
    FailureReason.NEGATIVE_AMOUNT: 'negative_amount',
    FailureReason.IS_NOT_INVENTED: 'is_not_invented',
    FailureReason.SELF_ATTACK: 'self_attack',
    FailureReason.ROUND_IS_NOT_GOING: 'round_is_not_going',
    FailureReason.ALREADY_IN_GAME: 'already_in_game',
    FailureReason.GAME_ENDED: 'game_ended',
    FailureReason.GAME_IS_FULL: 'game_is_full',
    FailureReason.CANNOT_START_ROUND: 'cannot_start_round',
    FailureReason.DIFFERENT_GAMES: 'different_games',
    FailureReason.WAIT_TILL_GAME_ENDS: 'wait_till_game_ends',
}