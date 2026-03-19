"""Campaign management tools — CRUD operations for campaigns."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from google.protobuf import field_mask_pb2

from google_ads_mcp.helpers import (
    currency_to_micros,
    error_response,
    execute_query,
    extract_google_ads_error,
    success_response,
)
from google_ads_mcp.server import get_client, mcp


@mcp.tool()
def list_campaigns(
    customer_id: str,
    ctx: Context,
    status_filter: str | None = None,
    limit: int = 100,
) -> dict:
    """List campaigns in a Google Ads account.

    Args:
        customer_id: Google Ads customer ID.
        status_filter: Optional filter -- 'ENABLED', 'PAUSED', or 'REMOVED'.
        limit: Max campaigns to return (default 100).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where = ""
        if status_filter:
            where = f"WHERE campaign.status = '{status_filter}'"
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.bidding_strategy_type,
                campaign.campaign_budget,
                campaign.start_date,
                campaign.end_date,
                campaign.serving_status,
                campaign_budget.amount_micros
            FROM campaign
            {where}
            ORDER BY campaign.name
            LIMIT {limit}
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"campaigns": results, "count": len(results)},
            message=f"Found {len(results)} campaign(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def get_campaign(
    customer_id: str,
    campaign_id: str,
    ctx: Context,
) -> dict:
    """Get details for a single campaign.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: The campaign ID.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.advertising_channel_sub_type,
                campaign.bidding_strategy_type,
                campaign.campaign_budget,
                campaign.start_date,
                campaign.end_date,
                campaign.serving_status,
                campaign.target_cpa.target_cpa_micros,
                campaign.target_roas.target_roas,
                campaign.maximize_conversions.target_cpa_micros,
                campaign.maximize_conversion_value.target_roas,
                campaign.network_settings.target_google_search,
                campaign.network_settings.target_search_network,
                campaign.network_settings.target_content_network,
                campaign_budget.amount_micros,
                campaign_budget.delivery_method
            FROM campaign
            WHERE campaign.id = {campaign_id}
        """
        results = execute_query(client, cid, query)
        if not results:
            return error_response(f"Campaign {campaign_id} not found")
        return success_response(data=results[0])
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def create_campaign(
    customer_id: str,
    name: str,
    budget_amount: float,
    ctx: Context,
    channel_type: str = "SEARCH",
    bidding_strategy: str = "MAXIMIZE_CONVERSIONS",
    target_cpa: float | None = None,
    target_roas: float | None = None,
    network_settings: dict | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    status: str = "PAUSED",
) -> dict:
    """Create a new campaign with a budget.

    Creates both the campaign budget and campaign in a single atomic operation.
    Campaign is created as PAUSED by default for safety.

    Args:
        customer_id: Google Ads customer ID.
        name: Campaign name.
        budget_amount: Daily budget in currency (e.g., 50.00 for $50/day).
        channel_type: Campaign type -- 'SEARCH', 'DISPLAY', 'VIDEO', 'DEMAND_GEN', 'SHOPPING'.
        bidding_strategy: Bidding strategy -- 'MAXIMIZE_CONVERSIONS', 'MAXIMIZE_CONVERSION_VALUE',
            'MAXIMIZE_CLICKS', 'TARGET_SPEND', 'MANUAL_CPC', 'TARGET_CPA', 'TARGET_ROAS'.
        target_cpa: Target CPA in currency (required if bidding_strategy is TARGET_CPA).
        target_roas: Target ROAS as a decimal (e.g., 3.0 for 300% ROAS).
        network_settings: Optional dict with keys: target_google_search, target_search_network,
            target_content_network (all bool).
        start_date: Campaign start date (YYYY-MM-DD). Defaults to today.
        end_date: Optional campaign end date (YYYY-MM-DD).
        status: Initial status -- 'PAUSED' (default, recommended) or 'ENABLED'.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        budget_temp_id = -1
        mutate_ops = []

        # 1. Create budget operation
        budget_op = client.client.operation("create", "CampaignBudget")
        budget = budget_op.create
        budget.name = f"{name} Budget"
        budget.amount_micros = currency_to_micros(budget_amount)
        budget.delivery_method = client.get_type("BudgetDeliveryMethodEnum").BudgetDeliveryMethod.STANDARD
        budget.resource_name = client.get_service("CampaignBudgetService").campaign_budget_path(
            cid, str(budget_temp_id)
        )

        mutate_op1 = client.get_type("MutateOperation")
        mutate_op1.campaign_budget_operation.CopyFrom(budget_op)
        mutate_ops.append(mutate_op1)

        # 2. Create campaign operation
        campaign_op = client.client.operation("create", "Campaign")
        campaign = campaign_op.create
        campaign.name = name
        campaign.campaign_budget = client.get_service("CampaignBudgetService").campaign_budget_path(
            cid, str(budget_temp_id)
        )

        channel_enum = client.get_type("AdvertisingChannelTypeEnum").AdvertisingChannelType
        campaign.advertising_channel_type = getattr(channel_enum, channel_type)

        status_enum = client.get_type("CampaignStatusEnum").CampaignStatus
        campaign.status = getattr(status_enum, status)

        if bidding_strategy == "MAXIMIZE_CONVERSIONS":
            campaign.maximize_conversions.target_cpa_micros = (
                currency_to_micros(target_cpa) if target_cpa else 0
            )
        elif bidding_strategy == "MAXIMIZE_CONVERSION_VALUE":
            campaign.maximize_conversion_value.target_roas = target_roas or 0.0
        elif bidding_strategy == "MAXIMIZE_CLICKS":
            campaign.maximize_clicks.cpc_bid_ceiling_micros = 0
        elif bidding_strategy == "MANUAL_CPC":
            campaign.manual_cpc.enhanced_cpc_enabled = True
        elif bidding_strategy == "TARGET_CPA":
            if not target_cpa:
                return error_response("target_cpa is required for TARGET_CPA bidding strategy")
            campaign.maximize_conversions.target_cpa_micros = currency_to_micros(target_cpa)
        elif bidding_strategy == "TARGET_ROAS":
            if not target_roas:
                return error_response("target_roas is required for TARGET_ROAS bidding strategy")
            campaign.maximize_conversion_value.target_roas = target_roas

        if channel_type == "SEARCH":
            ns = campaign.network_settings
            if network_settings:
                ns.target_google_search = network_settings.get("target_google_search", True)
                ns.target_search_network = network_settings.get("target_search_network", True)
                ns.target_content_network = network_settings.get("target_content_network", False)
            else:
                ns.target_google_search = True
                ns.target_search_network = True
                ns.target_content_network = False

        if start_date:
            campaign.start_date = start_date
        if end_date:
            campaign.end_date = end_date

        mutate_op2 = client.get_type("MutateOperation")
        mutate_op2.campaign_operation.CopyFrom(campaign_op)
        mutate_ops.append(mutate_op2)

        ga_service = client.get_service("GoogleAdsService")
        response = ga_service.mutate(customer_id=cid, mutate_operations=mutate_ops)

        campaign_rns = [r.campaign_result.resource_name for r in response.mutate_operation_responses if r.campaign_result.resource_name]
        budget_rns = [r.campaign_budget_result.resource_name for r in response.mutate_operation_responses if r.campaign_budget_result.resource_name]

        return success_response(
            data={
                "campaign_resource_name": campaign_rns[0] if campaign_rns else None,
                "budget_resource_name": budget_rns[0] if budget_rns else None,
            },
            message=f"Campaign '{name}' created successfully (status: {status})",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def update_campaign(
    customer_id: str,
    campaign_id: str,
    ctx: Context,
    name: str | None = None,
    status: str | None = None,
    target_cpa: float | None = None,
    target_roas: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Update an existing campaign's properties.

    Only provided fields will be updated.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: Campaign ID to update.
        name: New campaign name.
        status: New status -- 'ENABLED', 'PAUSED'.
        target_cpa: New target CPA (for maximize_conversions with target).
        target_roas: New target ROAS (for maximize_conversion_value with target).
        start_date: New start date (YYYY-MM-DD).
        end_date: New end date (YYYY-MM-DD).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        campaign_service = client.get_service("CampaignService")
        campaign_op = client.client.operation("update", "Campaign")
        campaign = campaign_op.update
        campaign.resource_name = campaign_service.campaign_path(cid, campaign_id)

        update_mask = []
        if name is not None:
            campaign.name = name
            update_mask.append("name")
        if status is not None:
            status_enum = client.get_type("CampaignStatusEnum").CampaignStatus
            campaign.status = getattr(status_enum, status)
            update_mask.append("status")
        if target_cpa is not None:
            campaign.maximize_conversions.target_cpa_micros = currency_to_micros(target_cpa)
            update_mask.append("maximize_conversions.target_cpa_micros")
        if target_roas is not None:
            campaign.maximize_conversion_value.target_roas = target_roas
            update_mask.append("maximize_conversion_value.target_roas")
        if start_date is not None:
            campaign.start_date = start_date
            update_mask.append("start_date")
        if end_date is not None:
            campaign.end_date = end_date
            update_mask.append("end_date")

        if not update_mask:
            return error_response("No fields to update. Provide at least one field.")

        campaign_op.update_mask.CopyFrom(
            field_mask_pb2.FieldMask(paths=update_mask)
        )

        response = campaign_service.mutate_campaigns(
            customer_id=cid, operations=[campaign_op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Campaign {campaign_id} updated successfully",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def set_campaign_status(
    customer_id: str,
    campaign_id: str,
    status: str,
    ctx: Context,
) -> dict:
    """Set a campaign's status (enable, pause, or remove).

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: Campaign ID.
        status: New status -- 'ENABLED', 'PAUSED', or 'REMOVED'.
    """
    if status not in ("ENABLED", "PAUSED", "REMOVED"):
        return error_response(f"Invalid status '{status}'. Must be ENABLED, PAUSED, or REMOVED.")
    return update_campaign(customer_id=customer_id, campaign_id=campaign_id, status=status, ctx=ctx)


@mcp.tool()
def remove_campaign(
    customer_id: str,
    campaign_id: str,
    ctx: Context,
    confirm_removal: bool = False,
) -> dict:
    """Soft-delete (remove) a campaign.

    This is a destructive operation. The campaign will be set to REMOVED status.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: Campaign ID to remove.
        confirm_removal: Must be True to proceed. Safety check for destructive operation.
    """
    if not confirm_removal:
        return error_response(
            "Removal not confirmed. Set confirm_removal=True to remove this campaign. "
            "This will set the campaign to REMOVED status (soft delete)."
        )
    return set_campaign_status(customer_id=customer_id, campaign_id=campaign_id, status="REMOVED", ctx=ctx)
