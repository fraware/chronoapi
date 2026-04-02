from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = "INFO"
    json_logs: bool = False
    worker_count: int = 4

    kafka_enabled: bool = False
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_input_topic: str = "forecast_requests"
    kafka_output_topic: str = "forecast_responses"

    api_key: SecretStr | None = None

    skip_model_load: bool = False
    finetune_async: bool = False


settings = Settings()
