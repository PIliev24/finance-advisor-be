from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "FA_", "env_file": ".env", "env_file_encoding": "utf-8"}

    api_key: str = Field(min_length=1)
    auth_username: str = Field(default="admin")
    auth_password: str = Field(min_length=1)
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = Field(default=1440)
    llm_provider: str = Field(default="openai", pattern=r"^(openai|anthropic)$")
    llm_model: str = Field(default="gpt-4o")
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    default_currency: str = Field(default="EUR")
    budget_alert_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    log_level: str = Field(default="INFO")
    db_path: str = Field(default="finance_advisor.db")
    cors_origins: str = Field(default="http://localhost:3000")

    # Phase 3
    alpha_vantage_api_key: str = Field(default="")
    twitter_bearer_token: str = Field(default="")


settings = Settings()
