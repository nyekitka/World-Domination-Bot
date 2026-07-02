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


database_config = DatabaseConfig()
