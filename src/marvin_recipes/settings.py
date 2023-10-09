from typing import Any

from marvin.settings import MarvinBaseSettings
from pydantic import Field, SecretStr


class ChromaSettings(MarvinBaseSettings):
    """Provider-specific settings. Only some of these will be relevant to users."""

    chroma_db_impl: str | None = Field(None)
    chroma_server_host: str = Field("localhost")
    chroma_server_http_port: int = Field(8000)
    is_persistent: bool = Field(True)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class Settings(MarvinBaseSettings):
    """Marvin integration settings"""

    chroma: ChromaSettings = ChromaSettings()
    google_api_key: SecretStr | None = None


settings = Settings()
