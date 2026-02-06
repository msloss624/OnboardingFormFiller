"""
Configuration — all secrets from environment variables.
No Azure Key Vault needed for a Streamlit app.
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    hubspot_api_key: str
    fireflies_api_key: str
    anthropic_api_key: str
    # Optional: Graph API for SharePoint/email (Phase 2)
    graph_client_id: str | None = None
    graph_tenant_id: str | None = None
    graph_client_secret: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            hubspot_api_key=os.environ["HUBSPOT_API_KEY"],
            fireflies_api_key=os.environ["FIREFLIES_API_KEY"],
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            graph_client_id=os.environ.get("GRAPH_CLIENT_ID"),
            graph_tenant_id=os.environ.get("GRAPH_TENANT_ID"),
            graph_client_secret=os.environ.get("GRAPH_CLIENT_SECRET"),
        )
