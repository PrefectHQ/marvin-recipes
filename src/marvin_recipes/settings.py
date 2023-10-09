from typing import Any

from marvin.settings import MarvinBaseSettings
from pydantic import SecretStr


class ChromaSettings(MarvinBaseSettings):
    """Provider-specific settings. Only some of these will be relevant to users."""

    chroma_db_impl: str | None = None
    chroma_server_host: str = "localhost"
    chroma_server_http_port: int = 8000
    is_persistent: bool = True

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class Settings(MarvinBaseSettings):
    """Marvin integration settings"""

    chroma: ChromaSettings = ChromaSettings()
    google_api_key: SecretStr | None = None


settings = Settings()
