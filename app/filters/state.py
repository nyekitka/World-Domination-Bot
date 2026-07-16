from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    """
    All possible state of the bot:
    - planets_numbers - admin is choosing a number of planets in the game;
    - choose_pack - admin chooses a pack of planets and cities;
    - transaction_state - state for the transaction process
    """

    planets_numbers = State()
    choose_pack = State()
    choose_lobby_admin = State()
    choose_lobby = State()
    transaction_state = State()
