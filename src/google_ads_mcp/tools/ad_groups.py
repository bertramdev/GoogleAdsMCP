"""Ad group management tools — CRUD operations for ad groups."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from google_ads_mcp.helpers import (
    currency_to_micros,
    error_response,
    execute_query,
    extract_google_ads_error,
    success_response,
)
from google_ads_mcp.server import get_client, mcp


@mcp.tool()
def list_ad_groups(
    customer_id: str,
    campaign_id: str,
    ctx: Context,
    status_filter: str | None = None,
    limit: int = 100,
) -> dict:
    """List ad groups in a campaign.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: Campaign ID to list ad groups for.
        status_filter: Optional -- 'ENABLED', 'PAUSED', or 'REMOVED'.
        limit: Max ad groups to return (default 100).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = [f"campaign.id = {campaign_id}"]
        if status_filter:
            where_clauses.append(f"ad_group.status = '{status_filter}'")

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type,
                ad_group.cpc_bid_micros,
                ad_group.target_cpa_micros,
                campaign.id,
                campaign.name
            FROM ad_group
            WHERE {where}
            ORDER BY ad_group.name
            LIMIT {limit}
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"ad_groups": results, "count": len(results)},
            message=f"Found {len(results)} ad group(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def get_ad_group(
    customer_id: str,
    ad_group_id: str,
    ctx: Context,
) -> dict:
    """Get details for a single ad group.

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type,
                ad_group.cpc_bid_micros,
                ad_group.cpm_bid_micros,
                ad_group.target_cpa_micros,
                ad_group.target_roas,
                ad_group.ad_rotation_mode,
                campaign.id,
                campaign.name,
                campaign.advertising_channel_type
            FROM ad_group
            WHERE ad_group.id = {ad_group_id}
        """
        results = execute_query(client, cid, query)
        if not results:
            return error_response(f"Ad group {ad_group_id} not found")
        return success_response(data=results[0])
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def create_ad_group(
    customer_id: str,
    campaign_id: str,
    name: str,
    ctx: Context,
    cpc_bid: float | None = None,
    target_cpa: float | None = None,
    ad_group_type: str = "SEARCH_STANDARD",
    status: str = "ENABLED",
) -> dict:
    """Create a new ad group in a campaign.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: Campaign ID to create the ad group in.
        name: Ad group name.
        cpc_bid: Max CPC bid in currency (e.g., 2.50 for $2.50).
        target_cpa: Target CPA in currency (overrides campaign-level if set).
        ad_group_type: Ad group type -- 'SEARCH_STANDARD', 'DISPLAY_STANDARD',
            'VIDEO_TRUE_VIEW_IN_STREAM', 'VIDEO_BUMPER', etc.
        status: Initial status -- 'ENABLED' (default) or 'PAUSED'.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        campaign_service = client.get_service("CampaignService")
        ad_group_service = client.get_service("AdGroupService")

        ad_group_op = client.client.operation("create", "AdGroup")
        ad_group = ad_group_op.create
        ad_group.name = name
        ad_group.campaign = campaign_service.campaign_path(cid, campaign_id)

        status_enum = client.get_type("AdGroupStatusEnum").AdGroupStatus
        ad_group.status = getattr(status_enum, status)

        type_enum = client.get_type("AdGroupTypeEnum").AdGroupType
        ad_group.type_ = getattr(type_enum, ad_group_type)

        if cpc_bid is not None:
            ad_group.cpc_bid_micros = currency_to_micros(cpc_bid)
        if target_cpa is not None:
            ad_group.target_cpa_micros = currency_to_micros(target_cpa)

        response = ad_group_service.mutate_ad_groups(
            customer_id=cid, operations=[ad_group_op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Ad group '{name}' created successfully",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def update_ad_group(
    customer_id: str,
    ad_group_id: str,
    ctx: Context,
    name: str | None = None,
    cpc_bid: float | None = None,
    target_cpa: float | None = None,
    status: str | None = None,
) -> dict:
    """Update an existing ad group.

    Only provided fields will be updated.

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID to update.
        name: New ad group name.
        cpc_bid: New max CPC bid in currency.
        target_cpa: New target CPA in currency.
        status: New status -- 'ENABLED', 'PAUSED', or 'REMOVED'.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ad_group_service = client.get_service("AdGroupService")
        ad_group_op = client.client.operation("update", "AdGroup")
        ad_group = ad_group_op.update
        ad_group.resource_name = ad_group_service.ad_group_path(cid, ad_group_id)

        update_mask = []
        if name is not None:
            ad_group.name = name
            update_mask.append("name")
        if cpc_bid is not None:
            ad_group.cpc_bid_micros = currency_to_micros(cpc_bid)
            update_mask.append("cpc_bid_micros")
        if target_cpa is not None:
            ad_group.target_cpa_micros = currency_to_micros(target_cpa)
            update_mask.append("target_cpa_micros")
        if status is not None:
            status_enum = client.get_type("AdGroupStatusEnum").AdGroupStatus
            ad_group.status = getattr(status_enum, status)
            update_mask.append("status")

        if not update_mask:
            return error_response("No fields to update. Provide at least one field.")

        from google.protobuf import field_mask_pb2

        ad_group_op.update_mask.CopyFrom(
            field_mask_pb2.FieldMask(paths=update_mask)
        )

        response = ad_group_service.mutate_ad_groups(
            customer_id=cid, operations=[ad_group_op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Ad group {ad_group_id} updated successfully",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def set_ad_group_status(
    customer_id: str,
    ad_group_id: str,
    status: str,
    ctx: Context,
) -> dict:
    """Set an ad group's status (enable, pause, or remove).

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID.
        status: New status -- 'ENABLED', 'PAUSED', or 'REMOVED'.
    """
    if status not in ("ENABLED", "PAUSED", "REMOVED"):
        return error_response(f"Invalid status '{status}'. Must be ENABLED, PAUSED, or REMOVED.")
    return update_ad_group(customer_id=customer_id, ad_group_id=ad_group_id, status=status, ctx=ctx)
