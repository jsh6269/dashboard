from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """프로젝트 공통 설정을 환경변수 + .env 로부터 읽어온다."""

    # Database
    db_host: str = Field("localhost", validation_alias="DB_HOST")
    db_user: str = Field("root", validation_alias="DB_USER")
    db_password: str = Field("password", validation_alias="DB_PASSWORD")
    db_name: str = Field("dashboard_db", validation_alias="DB_NAME")

    # Elasticsearch
    es_host: str = Field("localhost", validation_alias="ES_HOST")
    es_port: str = Field("9200", validation_alias="ES_PORT")

    # Redis
    redis_host: str = Field("localhost", validation_alias="REDIS_HOST")
    redis_port: str = Field("6379", validation_alias="REDIS_PORT")

    # Pydantic v2 config
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Convenience properties
    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}"

    @property
    def async_database_url(self) -> str:
        """Return async SQLAlchemy URL (using asyncmy driver)."""
        return f"mysql+aiomysql://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}"
