"""
Configuration — extends the base config with database and Azure settings.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


@dataclass
class Config:
    hubspot_api_key: str
    fireflies_api_key: str
    anthropic_api_key: str
    # Database
    database_url: str  # SQLAlchemy connection string
    # Azure Blob Storage (Phase 2)
    blob_connection_string: Optional[str] = None
    # Azure AD (Phase 3)
    azure_ad_tenant_id: Optional[str] = None
    azure_ad_client_id: Optional[str] = None
    azure_ad_audience: Optional[str] = None
    # Graph API (future)
    graph_client_id: Optional[str] = None
    graph_tenant_id: Optional[str] = None
    graph_client_secret: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            hubspot_api_key=os.environ["HUBSPOT_API_KEY"],
            fireflies_api_key=os.environ["FIREFLIES_API_KEY"],
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            database_url=os.environ.get(
                "DATABASE_URL",
                "sqlite+aiosqlite:///./onboarding.db",
            ),
            blob_connection_string=os.environ.get("BLOB_CONNECTION_STRING"),
            azure_ad_tenant_id=os.environ.get("AZURE_AD_TENANT_ID"),
            azure_ad_client_id=os.environ.get("AZURE_AD_CLIENT_ID"),
            azure_ad_audience=os.environ.get("AZURE_AD_AUDIENCE"),
            graph_client_id=os.environ.get("GRAPH_CLIENT_ID"),
            graph_tenant_id=os.environ.get("GRAPH_TENANT_ID"),
            graph_client_secret=os.environ.get("GRAPH_CLIENT_SECRET"),
        )


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
