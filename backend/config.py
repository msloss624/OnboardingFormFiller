"""
Configuration — extends the base config with database and Azure settings.
"""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Key Vault secret name → env var name
_KV_SECRET_MAP: Dict[str, str] = {
    "hubspot-api-key": "HUBSPOT_API_KEY",
    "fireflies-api-key": "FIREFLIES_API_KEY",
    "anthropic-api-key": "ANTHROPIC_API_KEY",
    "blob-connection-string": "BLOB_CONNECTION_STRING",
    "graph-client-secret": "GRAPH_CLIENT_SECRET",
}


def _load_keyvault_secrets() -> Dict[str, str]:
    """Fetch secrets from Azure Key Vault if KEY_VAULT_URL is set.

    Returns a dict mapping env var names to secret values.
    Falls back to empty dict if Key Vault is not configured.
    """
    vault_url = os.environ.get("KEY_VAULT_URL")
    if not vault_url:
        logger.info("Key Vault not configured — using environment variables only")
        return {}

    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
    secrets: Dict[str, str] = {}
    for kv_name, env_name in _KV_SECRET_MAP.items():
        try:
            secret = client.get_secret(kv_name)
            if secret.value:
                secrets[env_name] = secret.value
        except Exception:
            logger.warning("Failed to load Key Vault secret: %s", kv_name)

    logger.info("Loaded %d secret(s) from Key Vault", len(secrets))
    return secrets


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
    # Graph API — email sending
    graph_client_id: Optional[str] = None
    graph_tenant_id: Optional[str] = None
    graph_client_secret: Optional[str] = None
    graph_send_from_email: Optional[str] = None
    onboarding_team_email: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        kv = _load_keyvault_secrets()

        def _get(env_name: str, default: Optional[str] = None) -> Optional[str]:
            return kv.get(env_name) or os.environ.get(env_name, default)

        def _require(env_name: str) -> str:
            val = kv.get(env_name) or os.environ.get(env_name)
            if not val:
                raise RuntimeError(f"Missing required config: {env_name}")
            return val

        return cls(
            hubspot_api_key=_require("HUBSPOT_API_KEY"),
            fireflies_api_key=_require("FIREFLIES_API_KEY"),
            anthropic_api_key=_require("ANTHROPIC_API_KEY"),
            database_url=os.environ.get(
                "DATABASE_URL",
                "sqlite+aiosqlite:///./onboarding.db",
            ),
            blob_connection_string=_get("BLOB_CONNECTION_STRING"),
            azure_ad_tenant_id=os.environ.get("AZURE_AD_TENANT_ID"),
            azure_ad_client_id=os.environ.get("AZURE_AD_CLIENT_ID"),
            azure_ad_audience=os.environ.get("AZURE_AD_AUDIENCE"),
            graph_client_id=os.environ.get("GRAPH_CLIENT_ID"),
            graph_tenant_id=os.environ.get("GRAPH_TENANT_ID"),
            graph_client_secret=_get("GRAPH_CLIENT_SECRET"),
            graph_send_from_email=os.environ.get("GRAPH_SEND_FROM_EMAIL"),
            onboarding_team_email=os.environ.get("ONBOARDING_TEAM_EMAIL"),
        )


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
