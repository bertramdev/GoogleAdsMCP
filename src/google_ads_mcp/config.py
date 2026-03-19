"""Pydantic Settings for Google Ads API configuration."""

from __future__ import annotations

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
    client_id: str = Field(description="OAuth2 client ID")
    client_secret: str = Field(description="OAuth2 client secret")
    refresh_token: str = Field(description="OAuth2 refresh token")
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
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "use_proto_plus": True,
        }
        if self.login_customer_id:
            config["login_customer_id"] = self.login_customer_id.replace("-", "")
        return config
