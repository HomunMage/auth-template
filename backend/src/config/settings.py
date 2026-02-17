# config/settings.py

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleOAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOOGLE_")

    client_id: str = ""
    client_secret: str = ""
    token_url: str = "https://oauth2.googleapis.com/token"
    userinfo_url: str = "https://www.googleapis.com/oauth2/v3/userinfo"


class AuthentikSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTHENTIK_")

    url: str = ""
    client_id: str = ""

    @property
    def token_url(self) -> str:
        return f"{self.url}/application/o/token/"

    @property
    def userinfo_url(self) -> str:
        return f"{self.url}/application/o/userinfo/"


class AppSettings(BaseSettings):
    debug_mode: bool = Field(default=False, alias="DEBUG_MODE")
    backend_port: int = Field(default=5000, alias="BACKEND_PORT")

    google: GoogleOAuthSettings = GoogleOAuthSettings()
    authentik: AuthentikSettings = AuthentikSettings()

    @property
    def cors_origins(self) -> list[str]:
        if self.debug_mode:
            return ["*"]
        return ["*"]  # Customize for production


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()


settings = get_settings()
