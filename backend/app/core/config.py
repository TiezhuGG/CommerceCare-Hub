from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment, never committed secrets."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="COMMERCECARE_")

    environment: str = "development"
    database_url: str = "sqlite:///./commercecare.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    cors_origins: str = "http://localhost:3000"
    seed_on_start: bool = False
    demo_password: str = "demo-password-change-me"
    structured_provider: str = "deterministic_mock"
    structured_provider_timeout_seconds: float = 15
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = ""
    coze_webhook_secret: str = "development-only-coze-webhook-secret"

    def model_post_init(self, __context: object) -> None:
        if (
            self.environment != "development"
            and self.jwt_secret == "development-only-secret-change-me"
        ):
            raise ValueError("COMMERCECARE_JWT_SECRET must be set outside development")
        if (
            self.environment != "development"
            and self.coze_webhook_secret == "development-only-coze-webhook-secret"
        ):
            raise ValueError("COMMERCECARE_COZE_WEBHOOK_SECRET must be set outside development")


@lru_cache
def get_settings() -> Settings:
    return Settings()
