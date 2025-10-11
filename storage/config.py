from pydantic_settings import BaseSettings, SettingsConfigDict

class RedisConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='REDIS_')

    USER: str
    HOST: str
    PORT: str
    PASSWORD: str
    EXPIRE_KEY_SECONDS: int = 600

redis_config = RedisConfig()
