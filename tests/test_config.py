"""Tests for config module."""

from __future__ import annotations

from unittest.mock import patch

from google_ads_mcp.config import GoogleAdsSettings


def test_settings_to_client_dict():
    """Test that settings convert to GoogleAdsClient-compatible dict."""
    with patch.dict("os.environ", {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "dev_token",
        "GOOGLE_ADS_SERVICE_ACCOUNT_PATH": "/path/to/sa.json",
        "GOOGLE_ADS_IMPERSONATED_EMAIL": "user@example.com",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "123-456-7890",
    }):
        settings = GoogleAdsSettings()
        config = settings.to_client_dict()

        assert config["developer_token"] == "dev_token"
        assert config["json_key_file_path"] == "/path/to/sa.json"
        assert config["impersonated_email"] == "user@example.com"
        assert config["login_customer_id"] == "1234567890"
        assert config["use_proto_plus"] is True


def test_settings_strips_dashes_from_login_customer_id():
    """Test that dashes are stripped from login_customer_id."""
    with patch.dict("os.environ", {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "t",
        "GOOGLE_ADS_SERVICE_ACCOUNT_PATH": "/path/to/sa.json",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "123-456-7890",
    }):
        settings = GoogleAdsSettings()
        config = settings.to_client_dict()
        assert config["login_customer_id"] == "1234567890"


def test_settings_without_optional_fields():
    """Test that optional fields are excluded when not set."""
    with patch.dict("os.environ", {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "t",
        "GOOGLE_ADS_SERVICE_ACCOUNT_PATH": "/path/to/sa.json",
    }, clear=False):
        settings = GoogleAdsSettings(_env_file=None)
        config = settings.to_client_dict()
        assert "login_customer_id" not in config
        assert "impersonated_email" not in config
