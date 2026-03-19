"""Tests for helpers module."""

from __future__ import annotations

from google_ads_mcp.helpers import (
    build_date_clause,
    currency_to_micros,
    error_response,
    micros_to_currency,
    sanitize_customer_id,
    success_response,
)


def test_sanitize_customer_id_with_dashes():
    assert sanitize_customer_id("123-456-7890") == "1234567890"


def test_sanitize_customer_id_without_dashes():
    assert sanitize_customer_id("1234567890") == "1234567890"


def test_micros_to_currency():
    assert micros_to_currency(1_000_000) == 1.0
    assert micros_to_currency(2_500_000) == 2.5
    assert micros_to_currency(0) == 0.0


def test_currency_to_micros():
    assert currency_to_micros(1.0) == 1_000_000
    assert currency_to_micros(2.5) == 2_500_000
    assert currency_to_micros(0.0) == 0


def test_success_response():
    result = success_response(data={"key": "value"}, message="ok")
    assert result["success"] is True
    assert result["message"] == "ok"
    assert result["data"] == {"key": "value"}


def test_success_response_minimal():
    result = success_response()
    assert result["success"] is True
    assert "data" not in result


def test_error_response():
    result = error_response("Something failed")
    assert result["success"] is False
    assert result["error"] == "Something failed"


def test_error_response_with_details():
    result = error_response("Failed", details={"code": 123})
    assert result["success"] is False
    assert result["details"] == {"code": 123}


def test_build_date_clause_predefined():
    assert build_date_clause("LAST_30_DAYS") == "segments.date DURING LAST_30_DAYS"


def test_build_date_clause_custom():
    assert build_date_clause("2024-01-01,2024-01-31") == "segments.date BETWEEN '2024-01-01' AND '2024-01-31'"


def test_build_date_clause_custom_with_spaces():
    assert build_date_clause("2024-01-01, 2024-01-31") == "segments.date BETWEEN '2024-01-01' AND '2024-01-31'"
