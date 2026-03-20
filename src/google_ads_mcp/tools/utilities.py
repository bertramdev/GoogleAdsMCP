"""Utility tools — GAQL resources, field metadata, micros conversion."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from google_ads_mcp.helpers import (
    currency_to_micros,
    error_response,
    micros_to_currency,
    success_response,
)
from google_ads_mcp.annotations import READ_ONLY, READ_ONLY_LOCAL
from google_ads_mcp.server import get_client, mcp

# Common GAQL FROM-clause resources
GAQL_RESOURCES = [
    "accessible_bidding_strategy",
    "account_budget",
    "ad_group",
    "ad_group_ad",
    "ad_group_ad_asset_view",
    "ad_group_criterion",
    "ad_group_audience_view",
    "asset",
    "asset_group",
    "asset_group_asset",
    "asset_group_listing_group_filter",
    "asset_group_signal",
    "bidding_strategy",
    "campaign",
    "campaign_budget",
    "campaign_criterion",
    "campaign_audience_view",
    "change_event",
    "change_status",
    "click_view",
    "conversion_action",
    "customer",
    "customer_client",
    "display_keyword_view",
    "gender_view",
    "geographic_view",
    "geo_target_constant",
    "keyword_view",
    "label",
    "language_constant",
    "location_view",
    "managed_placement_view",
    "performance_max_placement_view",
    "search_term_view",
    "shopping_performance_view",
    "topic_view",
    "user_interest",
    "user_list",
    "video",
]


@mcp.tool(annotations=READ_ONLY_LOCAL)
def list_gaql_resources() -> dict:
    """List available GAQL FROM-clause resources for use with execute_gaql.

    Returns commonly used resource names that can be queried via GAQL.
    """
    return success_response(
        data={"resources": GAQL_RESOURCES, "count": len(GAQL_RESOURCES)},
        message="Use these as the FROM clause in GAQL queries with execute_gaql",
    )


@mcp.tool(annotations=READ_ONLY)
def get_field_metadata(
    resource_type: str,
    ctx: Context,
    customer_id: str | None = None,
) -> dict:
    """Get selectable, filterable, and sortable fields for a GAQL resource.

    Args:
        resource_type: Resource name (e.g., 'campaign', 'ad_group', 'ad_group_ad').
        customer_id: Customer ID (uses default if not provided).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        query = f"""
            SELECT
                name,
                category,
                data_type,
                selectable,
                filterable,
                sortable,
                selectable_with,
                is_repeated
            WHERE name LIKE '{resource_type}.%'
            ORDER BY name
        """
        gaf_service = client.get_service("GoogleAdsFieldService")
        response = gaf_service.search_google_ads_fields(query=query)
        fields = []
        for field in response:
            fields.append({
                "name": field.name,
                "category": field.category.name if field.category else None,
                "data_type": field.data_type.name if field.data_type else None,
                "selectable": field.selectable,
                "filterable": field.filterable,
                "sortable": field.sortable,
                "is_repeated": field.is_repeated,
            })
        return success_response(
            data={"resource": resource_type, "fields": fields, "count": len(fields)},
            message=f"Found {len(fields)} fields for '{resource_type}'",
        )
    except Exception as e:
        return error_response(f"Failed to get field metadata: {e}")


@mcp.tool(annotations=READ_ONLY_LOCAL)
def convert_micros(
    value: float,
    direction: str = "to_micros",
) -> dict:
    """Convert between micros and currency amounts.

    Google Ads uses micros for monetary values: $1.00 = 1,000,000 micros.

    Args:
        value: The value to convert.
        direction: 'to_micros' (currency to micros) or 'from_micros' (micros to currency).
    """
    if direction == "to_micros":
        result = currency_to_micros(value)
        return success_response(
            data={"input": value, "micros": result},
            message=f"${value:.2f} = {result:,} micros",
        )
    elif direction == "from_micros":
        result = micros_to_currency(int(value))
        return success_response(
            data={"micros": int(value), "currency": result},
            message=f"{int(value):,} micros = ${result:.2f}",
        )
    else:
        return error_response(f"Invalid direction '{direction}'. Use 'to_micros' or 'from_micros'.")
