"""GoogleAdsClient wrapper for MCP server."""

from __future__ import annotations

import logging

from google.ads.googleads.client import GoogleAdsClient

from .config import GoogleAdsSettings

logger = logging.getLogger(__name__)

# Google Ads API version
API_VERSION = "v19"


class GoogleAdsClientWrapper:
    """Wraps GoogleAdsClient with convenience methods."""

    def __init__(self, settings: GoogleAdsSettings) -> None:
        self.settings = settings
        self._client = GoogleAdsClient.load_from_dict(settings.to_client_dict())
        self.default_customer_id = settings.customer_id.replace("-", "") if settings.customer_id else ""
        logger.info("GoogleAdsClient initialized successfully")

    @property
    def client(self) -> GoogleAdsClient:
        """Access the underlying GoogleAdsClient."""
        return self._client

    def get_service(self, service_name: str):
        """Get a Google Ads API service by name."""
        return self._client.get_service(service_name, version=API_VERSION)

    def get_type(self, type_name: str):
        """Get a Google Ads API type by name."""
        return self._client.get_type(type_name)

    def resolve_customer_id(self, customer_id: str | None) -> str:
        """Resolve customer ID: use provided value or fall back to default.

        Args:
            customer_id: Customer ID (may contain dashes) or None.

        Returns:
            Sanitized customer ID string.

        Raises:
            ValueError: If no customer ID is provided and no default is set.
        """
        if customer_id:
            return customer_id.replace("-", "")
        if self.default_customer_id:
            return self.default_customer_id
        raise ValueError(
            "No customer_id provided and no default GOOGLE_ADS_CUSTOMER_ID set. "
            "Pass customer_id parameter or set GOOGLE_ADS_CUSTOMER_ID env var."
        )
