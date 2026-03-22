from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Companies House
    ch_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://kyc:kyc_secret@localhost:5432/kyc"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Admin seed
    admin_email: str = "admin@example.com"
    admin_password: str = "changeme"

    @property
    def mock_mode(self) -> bool:
        return not self.ch_api_key


settings = Settings()
