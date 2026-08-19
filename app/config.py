from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='BOT_')

    TOKEN: str
    OWNER: str
    THROTTLE: float
    THROTTLE_CACHE_MAXSIZE: int
    APSCHEDULER_STORE_INDEX: int

bot_config = BotConfig()
