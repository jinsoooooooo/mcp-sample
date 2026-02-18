from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = ".env"

class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=env_file, env_file_encoding="utf-8")

    AZURE_CLIENT_ID: str
    AZURE_TENANT_ID: str
    AZURE_CLIENT_SECRET: str
    DEFAULT_USER_EMAIL: str
    LOG_LEVEL: str



settings = Settings()
