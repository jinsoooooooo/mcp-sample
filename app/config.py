from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = ".env"

class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(env_file=env_file, env_file_encoding="utf-8")
    
    CLIENT_ID: str
    TENANT_ID: str


settings = Settings()
    