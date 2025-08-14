from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    NAME: str
    USER: str
    PASSWORD: str
    HOST: str
    PORT: str
    POOL_SIZE: int = 5
    POOL_TIMEOUT: int = 20
    EXPIRE_CACHE: int = 60 * 60

    @property
    def database_url(self):
        return (
            f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}"
            f"@{self.HOST}:{self.PORT}/{self.NAME}"
        )


class GameConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GAME_")

    ROUND_LENGTH: int = 600
    INVENTION_COST: int = 500
    CREATE_COST: int = 150
    DEVELOPMENT_BOOST: int = 20
    DEVELOPMENT_COST: int = 150
    SHIELD_COST: int = 300
    ECO_BOOST_RATE: int = 20
    INCOME_COEFFICIENT: float = 3


database_config = DatabaseConfig()
game_config = GameConfig()
