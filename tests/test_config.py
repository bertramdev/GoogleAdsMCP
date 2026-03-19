"""Tests for config module."""

from __future__ import annotations

from unittest.mock import patch

from google_ads_mcp.config import GoogleAdsSettings


def test_settings_to_client_dict():
    """Test that settings convert to GoogleAdsClient-compatible dict."""
    with patch.dict("os.environ", {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "dev_token",
        "GOOGLE_ADS_CLIENT_ID": "client_id",
        "GOOGLE_ADS_CLIENT_SECRET": "client_secret",
        "GOOGLE_ADS_REFRESH_TOKEN": "refresh_token",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "123-456-7890",
    }):
        settings = GoogleAdsSettings()
        config = settings.to_client_dict()

        assert config["developer_token"] == "dev_token"
        assert config["client_id"] == "client_id"
        assert config["client_secret"] == "client_secret"
        assert config["refresh_token"] == "refresh_token"
        assert config["login_customer_id"] == "1234567890"
        assert config["use_proto_plus"] is True


def test_settings_strips_dashes_from_login_customer_id():
    """Test that dashes are stripped from login_customer_id."""
    with patch.dict("os.environ", {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "t",
        "GOOGLE_ADS_CLIENT_ID": "c",
        "GOOGLE_ADS_CLIENT_SECRET": "s",
        "GOOGLE_ADS_REFRESH_TOKEN": "r",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "123-456-7890",
    }):
        settings = GoogleAdsSettings()
        config = settings.to_client_dict()
        assert config["login_customer_id"] == "1234567890"


def test_settings_without_login_customer_id():
    """Test that login_customer_id is excluded when not set."""
    with patch.dict("os.environ", {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "t",
        "GOOGLE_ADS_CLIENT_ID": "c",
        "GOOGLE_ADS_CLIENT_SECRET": "s",
        "GOOGLE_ADS_REFRESH_TOKEN": "r",
    }, clear=False):
        settings = GoogleAdsSettings(_env_file=None)
        config = settings.to_client_dict()
        assert "login_customer_id" not in config
