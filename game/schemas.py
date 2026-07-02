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


FAILURE_INTERPRETATIONS = {
    FailureReason.UNTIMELY_NEGOTIATIONS: 'Сейчас нельзя находиться на переговорах',
    FailureReason.PLANET_IS_BUSY: 'Данная планета уже находится на переговорах',
    FailureReason.BILATERAL_NEGOTIATIONS: 'Вы уже переговариваете с данной планетой',
    FailureReason.ALREADY_NEGOTIATING: 'Вы уже принимаете одну планету на переговоры',
    FailureReason.OBJECT_NOT_FOUND: 'Такого объекта нет',
    FailureReason.ALREADY_INVENTED: 'У вас уже изобретена технология отправки метеоритов',
    FailureReason.NOT_ENOUGH_MONEY: 'Недостаточно денег для операции.',
    FailureReason.NOT_ENOUGH_PLAYERS: 'Недостаточно игроков для того, чтобы начать игру.',
    FailureReason.NOT_ENOUGH_METEORITES: 'Недостаточно метеоритов для операции.',
    FailureReason.NOT_IN_GAME: 'Вы не находитесь в лобби, чтобы из него выходить.',
    FailureReason.NEGATIVE_AMOUNT: 'Нельзя переводить неположительную сумму',
    FailureReason.IS_NOT_INVENTED: 'Вы не можете покупать метеориты поскольку у вас ещё не разработана технология их отправки.',
    FailureReason.SELF_ATTACK: 'Отправлять метеорит на свой город невозможно.',
    FailureReason.ROUND_IS_NOT_GOING: 'Нельзя закончить раунд, потому что сейчас никакого раунда не идёт.',
    FailureReason.ALREADY_IN_GAME: 'Вы уже находитесь в игре.',
    FailureReason.GAME_ENDED: 'Игра уже закончена.',
    FailureReason.GAME_IS_FULL: 'В данной игре нет свободных планет. Зайдите в другую игру.',
    FailureReason.CANNOT_START_ROUND: 'Нельзя начать новый раунд',
    FailureReason.DIFFERENT_GAMES: 'Нельзя перевести планете из другой игры',
    FailureReason.WAIT_TILL_GAME_ENDS: 'Нельзя выполнить эту операцию, поскольку игрок находится в игре. Подождите пока она закончится.'
}