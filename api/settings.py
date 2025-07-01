from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """프로젝트 공통 설정을 환경변수 + .env 로부터 읽어온다."""

    # Database
    db_host: str = Field("localhost", env="DB_HOST")
    db_user: str = Field("root", env="DB_USER")
    db_password: str = Field("password", env="DB_PASSWORD")
    db_name: str = Field("dashboard_db", env="DB_NAME")

    # Elasticsearch
    es_host: str = Field("localhost", env="ES_HOST")
    es_port: str = Field("9200", env="ES_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # Convenience properties
    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}" 