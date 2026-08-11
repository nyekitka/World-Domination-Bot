from pydantic_settings import BaseSettings, SettingsConfigDict


class BotConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='BOT_')

    TOKEN: str
    OWNER: str

bot_config = BotConfig()
