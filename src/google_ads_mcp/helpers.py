"""Helper functions for Google Ads MCP tools."""

from __future__ import annotations

import logging
from typing import Any

from google.protobuf.json_format import MessageToDict

logger = logging.getLogger(__name__)


def sanitize_customer_id(customer_id: str) -> str:
    """Strip dashes from customer ID: '123-456-7890' → '1234567890'."""
    return customer_id.replace("-", "")


def micros_to_currency(micros: int) -> float:
    """Convert micros to currency amount. 1,000,000 micros = $1.00."""
    return micros / 1_000_000


def currency_to_micros(amount: float) -> int:
    """Convert currency amount to micros. $1.00 = 1,000,000 micros."""
    return int(amount * 1_000_000)


def proto_to_dict(proto_obj: Any) -> dict:
    """Convert a protobuf/proto-plus object to a Python dict.

    Handles both proto-plus wrapper objects and raw protobuf messages.
    """
    if proto_obj is None:
        return {}
    try:
        # proto-plus objects have a _pb attribute for the raw protobuf
        pb = getattr(proto_obj, "_pb", proto_obj)
        return MessageToDict(pb, preserving_proto_field_name=True)
    except Exception:
        return {"raw": str(proto_obj)}


def execute_query(
    client_wrapper,
    customer_id: str,
    query: str,
) -> list[dict]:
    """Execute a GAQL query and return results as a list of dicts.

    Args:
        client_wrapper: GoogleAdsClientWrapper instance.
        customer_id: Customer ID (already sanitized).
        query: GAQL query string.

    Returns:
        List of result dicts.
    """
    ga_service = client_wrapper.get_service("GoogleAdsService")
    response = ga_service.search(customer_id=customer_id, query=query)
    results = []
    for row in response:
        results.append(proto_to_dict(row))
    return results


def execute_query_stream(
    client_wrapper,
    customer_id: str,
    query: str,
) -> list[dict]:
    """Execute a GAQL query using streaming and return results as a list of dicts.

    More efficient for large result sets.
    """
    ga_service = client_wrapper.get_service("GoogleAdsService")
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    results = []
    for batch in stream:
        for row in batch.results:
            results.append(proto_to_dict(row))
    return results


def build_date_clause(date_range: str) -> str:
    """Build a GAQL WHERE clause for a date range.

    Accepts predefined ranges (LAST_7_DAYS, LAST_30_DAYS, etc.)
    or custom 'YYYY-MM-DD,YYYY-MM-DD' format.
    """
    if "," in date_range:
        start, end = date_range.split(",", 1)
        return f"segments.date BETWEEN '{start.strip()}' AND '{end.strip()}'"
    return f"segments.date DURING {date_range}"


def format_resource_name(resource_type: str, customer_id: str, resource_id: str) -> str:
    """Format a Google Ads resource name.

    Example: format_resource_name("campaigns", "1234567890", "111") → "customers/1234567890/campaigns/111"
    """
    return f"customers/{customer_id}/{resource_type}/{resource_id}"


def success_response(data: Any = None, message: str = "") -> dict:
    """Build a standard success response."""
    result: dict[str, Any] = {"success": True}
    if message:
        result["message"] = message
    if data is not None:
        result["data"] = data
    return result


def error_response(error: str, details: Any = None) -> dict:
    """Build a standard error response."""
    result: dict[str, Any] = {"success": False, "error": error}
    if details is not None:
        result["details"] = details
    return result


def extract_google_ads_error(exception: Exception) -> str:
    """Extract a human-readable error message from a GoogleAdsException."""
    try:
        from google.ads.googleads.errors import GoogleAdsException

        if isinstance(exception, GoogleAdsException):
            messages = []
            for error in exception.failure.errors:
                messages.append(error.message)
            return "; ".join(messages) if messages else str(exception)
    except ImportError:
        pass
    return str(exception)
