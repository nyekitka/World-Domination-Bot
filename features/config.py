from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='feature/.env',
    )

    I18N: bool = False

feature_config = FeatureConfig()
