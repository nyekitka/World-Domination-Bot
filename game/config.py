from pydantic_settings import BaseSettings, SettingsConfigDict


class RoundInfo(BaseSettings):
    length: int


class GameConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GAME_")

    ROUND_LENGTH: int = 600
    ROUND_NUM: int = 6
    INVENTION_COST: int = 500
    CREATE_COST: int = 150
    DEVELOPMENT_BOOST: int = 20
    DEVELOPMENT_COST: int = 150
    SHIELD_COST: int = 300
    ATTACK_COST: int = 1
    ECO_COST: int = 1
    SANCTIONS_COST: int = 0
    DEFAULT_GAME_ECO_RATE: int = 95
    DEFAULT_BALANCE: int = 1000
    DEFAULT_DEVELOPMENT: int = 60
    ECO_BOOST_RATE: int = 20
    INCOME_COEFFICIENT: float = 3

game_config = GameConfig()
