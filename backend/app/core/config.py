from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RaceQuant"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://racequant:racequant@localhost:5432/racequant"
    hkjc_structured_db_path: str = "data/processed/hkjc_structured.sqlite"
    legacy_odds_db_path: str = "data/processed/legacy_horse_odds.sqlite"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
