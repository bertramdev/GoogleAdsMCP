"""Shared test fixtures for Google Ads MCP tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from google_ads_mcp.client import GoogleAdsClientWrapper
from google_ads_mcp.config import GoogleAdsSettings


@pytest.fixture
def mock_settings():
    """Create mock GoogleAdsSettings."""
    with patch.object(GoogleAdsSettings, "__init__", lambda self, **kwargs: None):
        settings = GoogleAdsSettings.__new__(GoogleAdsSettings)
        settings.developer_token = "test_token"
        settings.client_id = "test_client_id"
        settings.client_secret = "test_client_secret"
        settings.refresh_token = "test_refresh_token"
        settings.login_customer_id = "1234567890"
        settings.customer_id = "9876543210"
        return settings


@pytest.fixture
def mock_google_ads_client():
    """Create a mock GoogleAdsClient."""
    return MagicMock()


@pytest.fixture
def mock_client_wrapper(mock_settings, mock_google_ads_client):
    """Create a mock GoogleAdsClientWrapper."""
    with patch("google_ads_mcp.client.GoogleAdsClient") as mock_client_class:
        mock_client_class.load_from_dict.return_value = mock_google_ads_client
        wrapper = GoogleAdsClientWrapper(mock_settings)
        return wrapper
