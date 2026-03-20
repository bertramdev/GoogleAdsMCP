"""Pydantic Settings for Google Ads API configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GoogleAdsSettings(BaseSettings):
    """Loads Google Ads API credentials from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_ADS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    developer_token: str = Field(description="Google Ads API developer token")
    service_account_path: str = Field(description="Path to service account JSON key file")
    impersonated_email: str = Field(
        default="",
        description="Email of the Workspace user to impersonate (domain-wide delegation)",
    )
    login_customer_id: str = Field(
        default="",
        description="MCC customer ID (required for MCC-level access)",
    )
    customer_id: str = Field(
        default="",
        description="Default customer ID for operations",
    )

    def to_client_dict(self) -> dict:
        """Convert settings to a dict suitable for GoogleAdsClient.load_from_dict()."""
        config = {
            "developer_token": self.developer_token,
            "json_key_file_path": str(Path(self.service_account_path).expanduser()),
            "use_proto_plus": True,
        }
        if self.impersonated_email:
            config["impersonated_email"] = self.impersonated_email
        if self.login_customer_id:
            config["login_customer_id"] = self.login_customer_id.replace("-", "")
        return config
