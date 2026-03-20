"""Performance Max tools — asset groups, assets, audience signals, PMax reporting."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from google_ads_mcp.helpers import (
    build_date_clause,
    currency_to_micros,
    error_response,
    execute_query,
    extract_google_ads_error,
    success_response,
)
from google_ads_mcp.annotations import CREATE, DESTRUCTIVE, READ_ONLY
from google_ads_mcp.server import get_client, mcp


@mcp.tool(annotations=CREATE)
def create_performance_max_campaign(
    customer_id: str,
    campaign_name: str,
    budget_amount: float,
    asset_group_name: str,
    final_urls: list[str],
    headlines: list[str],
    long_headlines: list[str],
    descriptions: list[str],
    business_name: str,
    ctx: Context,
    marketing_image_assets: list[str] | None = None,
    square_image_assets: list[str] | None = None,
    logo_assets: list[str] | None = None,
    youtube_video_assets: list[str] | None = None,
    bidding_strategy: str = "MAXIMIZE_CONVERSIONS",
    target_cpa: float | None = None,
    target_roas: float | None = None,
    status: str = "PAUSED",
) -> dict:
    """Create a complete Performance Max campaign with budget, campaign, and asset group.

    Creates everything in a single atomic batch operation using temporary IDs.
    Campaign is created as PAUSED by default for safety.

    PMax minimum requirements:
    - 3+ headlines (max 30 chars each)
    - 1+ long headlines (max 90 chars)
    - 2+ descriptions (max 90 chars each)
    - 1 business name
    - Final URLs
    - Image assets should be pre-uploaded (use asset resource names)

    Args:
        customer_id: Google Ads customer ID.
        campaign_name: Campaign name.
        budget_amount: Daily budget in currency.
        asset_group_name: Name for the asset group.
        final_urls: Landing page URLs.
        headlines: 3-15 headlines (max 30 chars each).
        long_headlines: 1-5 long headlines (max 90 chars each).
        descriptions: 2-5 descriptions (max 90 chars each).
        business_name: Business name for the asset group.
        marketing_image_assets: Landscape image asset resource names (1200x628).
        square_image_assets: Square image asset resource names (1200x1200).
        logo_assets: Logo image asset resource names.
        youtube_video_assets: YouTube video asset resource names.
        bidding_strategy: 'MAXIMIZE_CONVERSIONS' or 'MAXIMIZE_CONVERSION_VALUE'.
        target_cpa: Target CPA (for maximize_conversions with target).
        target_roas: Target ROAS (for maximize_conversion_value with target).
        status: Initial status -- 'PAUSED' (default) or 'ENABLED'.
    """
    if len(headlines) < 3:
        return error_response("PMax requires at least 3 headlines (max 30 chars each).")
    if len(long_headlines) < 1:
        return error_response("PMax requires at least 1 long headline (max 90 chars).")
    if len(descriptions) < 2:
        return error_response("PMax requires at least 2 descriptions (max 90 chars each).")
    if not final_urls:
        return error_response("At least one final URL is required.")

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        BUDGET_TEMP_ID = -1
        CAMPAIGN_TEMP_ID = -2
        ASSET_GROUP_TEMP_ID = -3

        mutate_ops = []

        # 1. Budget
        budget_service = client.get_service("CampaignBudgetService")
        budget_op = client.client.operation("create", "CampaignBudget")
        budget = budget_op.create
        budget.name = f"{campaign_name} Budget"
        budget.amount_micros = currency_to_micros(budget_amount)
        budget.delivery_method = client.get_type("BudgetDeliveryMethodEnum").BudgetDeliveryMethod.STANDARD
        budget.resource_name = budget_service.campaign_budget_path(cid, str(BUDGET_TEMP_ID))

        mutate_op = client.get_type("MutateOperation")
        mutate_op.campaign_budget_operation.CopyFrom(budget_op)
        mutate_ops.append(mutate_op)

        # 2. Campaign
        campaign_service = client.get_service("CampaignService")
        campaign_op = client.client.operation("create", "Campaign")
        campaign = campaign_op.create
        campaign.name = campaign_name
        campaign.campaign_budget = budget_service.campaign_budget_path(cid, str(BUDGET_TEMP_ID))
        campaign.resource_name = campaign_service.campaign_path(cid, str(CAMPAIGN_TEMP_ID))

        channel_enum = client.get_type("AdvertisingChannelTypeEnum").AdvertisingChannelType
        campaign.advertising_channel_type = channel_enum.PERFORMANCE_MAX

        status_enum = client.get_type("CampaignStatusEnum").CampaignStatus
        campaign.status = getattr(status_enum, status)

        if bidding_strategy == "MAXIMIZE_CONVERSIONS":
            campaign.maximize_conversions.target_cpa_micros = (
                currency_to_micros(target_cpa) if target_cpa else 0
            )
        elif bidding_strategy == "MAXIMIZE_CONVERSION_VALUE":
            campaign.maximize_conversion_value.target_roas = target_roas or 0.0

        campaign.url_expansion_opt_out = False

        mutate_op = client.get_type("MutateOperation")
        mutate_op.campaign_operation.CopyFrom(campaign_op)
        mutate_ops.append(mutate_op)

        # 3. Asset Group
        asset_group_service = client.get_service("AssetGroupService")
        ag_op = client.client.operation("create", "AssetGroup")
        asset_group = ag_op.create
        asset_group.name = asset_group_name
        asset_group.campaign = campaign_service.campaign_path(cid, str(CAMPAIGN_TEMP_ID))
        asset_group.resource_name = asset_group_service.asset_group_path(
            cid, str(ASSET_GROUP_TEMP_ID)
        )
        asset_group.final_urls.extend(final_urls)

        ag_status_enum = client.get_type("AssetGroupStatusEnum").AssetGroupStatus
        asset_group.status = ag_status_enum.ENABLED

        mutate_op = client.get_type("MutateOperation")
        mutate_op.asset_group_operation.CopyFrom(ag_op)
        mutate_ops.append(mutate_op)

        # 4. Text assets linked to asset group
        asset_group_rn = asset_group_service.asset_group_path(cid, str(ASSET_GROUP_TEMP_ID))
        field_type_enum = client.get_type("AssetFieldTypeEnum").AssetFieldType

        asset_temp_id = -100
        asset_service = client.get_service("AssetService")

        def add_text_asset(text: str, field_type):
            nonlocal asset_temp_id
            a_op = client.client.operation("create", "Asset")
            asset = a_op.create
            asset.text_asset.text = text
            asset.resource_name = asset_service.asset_path(cid, str(asset_temp_id))

            m_op = client.get_type("MutateOperation")
            m_op.asset_operation.CopyFrom(a_op)
            mutate_ops.append(m_op)

            link_op = client.client.operation("create", "AssetGroupAsset")
            link = link_op.create
            link.asset = asset_service.asset_path(cid, str(asset_temp_id))
            link.asset_group = asset_group_rn
            link.field_type = field_type

            m_op2 = client.get_type("MutateOperation")
            m_op2.asset_group_asset_operation.CopyFrom(link_op)
            mutate_ops.append(m_op2)

            asset_temp_id -= 1

        for h in headlines:
            add_text_asset(h, field_type_enum.HEADLINE)
        for lh in long_headlines:
            add_text_asset(lh, field_type_enum.LONG_HEADLINE)
        for d in descriptions:
            add_text_asset(d, field_type_enum.DESCRIPTION)
        add_text_asset(business_name, field_type_enum.BUSINESS_NAME)

        # 5. Link pre-uploaded image/video assets
        def link_existing_asset(asset_rn: str, field_type):
            link_op = client.client.operation("create", "AssetGroupAsset")
            link = link_op.create
            link.asset = asset_rn
            link.asset_group = asset_group_rn
            link.field_type = field_type

            m_op = client.get_type("MutateOperation")
            m_op.asset_group_asset_operation.CopyFrom(link_op)
            mutate_ops.append(m_op)

        if marketing_image_assets:
            for img in marketing_image_assets:
                link_existing_asset(img, field_type_enum.MARKETING_IMAGE)
        if square_image_assets:
            for img in square_image_assets:
                link_existing_asset(img, field_type_enum.SQUARE_MARKETING_IMAGE)
        if logo_assets:
            for img in logo_assets:
                link_existing_asset(img, field_type_enum.LOGO)
        if youtube_video_assets:
            for vid in youtube_video_assets:
                link_existing_asset(vid, field_type_enum.YOUTUBE_VIDEO)

        # Execute batch
        ga_service = client.get_service("GoogleAdsService")
        response = ga_service.mutate(customer_id=cid, mutate_operations=mutate_ops)

        campaign_rns = []
        budget_rns = []
        ag_rns = []
        for r in response.mutate_operation_responses:
            if r.campaign_result.resource_name:
                campaign_rns.append(r.campaign_result.resource_name)
            if r.campaign_budget_result.resource_name:
                budget_rns.append(r.campaign_budget_result.resource_name)
            if r.asset_group_result.resource_name:
                ag_rns.append(r.asset_group_result.resource_name)

        return success_response(
            data={
                "campaign_resource_name": campaign_rns[0] if campaign_rns else None,
                "budget_resource_name": budget_rns[0] if budget_rns else None,
                "asset_group_resource_name": ag_rns[0] if ag_rns else None,
                "total_operations": len(mutate_ops),
            },
            message=f"PMax campaign '{campaign_name}' created (status: {status})",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def list_asset_groups(
    customer_id: str,
    campaign_id: str,
    ctx: Context,
) -> dict:
    """List asset groups in a Performance Max campaign.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: PMax campaign ID.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        query = f"""
            SELECT
                asset_group.id,
                asset_group.name,
                asset_group.status,
                asset_group.final_urls,
                asset_group.ad_strength,
                campaign.id,
                campaign.name
            FROM asset_group
            WHERE campaign.id = {campaign_id}
            ORDER BY asset_group.name
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"asset_groups": results, "count": len(results)},
            message=f"Found {len(results)} asset group(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_asset_group_details(
    customer_id: str,
    asset_group_id: str,
    ctx: Context,
) -> dict:
    """Get full details of an asset group including linked assets and signals.

    Args:
        customer_id: Google Ads customer ID.
        asset_group_id: Asset group ID.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ag_query = f"""
            SELECT
                asset_group.id,
                asset_group.name,
                asset_group.status,
                asset_group.final_urls,
                asset_group.final_mobile_urls,
                asset_group.ad_strength,
                campaign.id,
                campaign.name
            FROM asset_group
            WHERE asset_group.id = {asset_group_id}
        """
        ag_results = execute_query(client, cid, ag_query)

        assets_query = f"""
            SELECT
                asset_group_asset.asset,
                asset_group_asset.field_type,
                asset_group_asset.status,
                asset.id,
                asset.name,
                asset.type,
                asset.text_asset.text,
                asset.image_asset.full_size.url,
                asset.youtube_video_asset.youtube_video_id
            FROM asset_group_asset
            WHERE asset_group.id = {asset_group_id}
        """
        asset_results = execute_query(client, cid, assets_query)

        signals_query = f"""
            SELECT
                asset_group_signal.resource_name,
                asset_group_signal.audience.audience
            FROM asset_group_signal
            WHERE asset_group.id = {asset_group_id}
        """
        signal_results = execute_query(client, cid, signals_query)

        return success_response(
            data={
                "asset_group": ag_results[0] if ag_results else None,
                "linked_assets": asset_results,
                "audience_signals": signal_results,
                "asset_count": len(asset_results),
            },
            message=f"Asset group details with {len(asset_results)} linked asset(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=CREATE)
def add_assets_to_group(
    customer_id: str,
    asset_group_id: str,
    assets: list[dict],
    ctx: Context,
) -> dict:
    """Add assets to an existing asset group (batch link operation).

    Args:
        customer_id: Google Ads customer ID.
        asset_group_id: Asset group ID.
        assets: List of asset dicts, each with:
            - asset_resource_name (str): Full asset resource name.
            - field_type (str): Asset field type -- 'HEADLINE', 'LONG_HEADLINE',
              'DESCRIPTION', 'BUSINESS_NAME', 'MARKETING_IMAGE',
              'SQUARE_MARKETING_IMAGE', 'LOGO', 'YOUTUBE_VIDEO', 'CALL_TO_ACTION_SELECTION'.

    Example:
        assets=[
            {"asset_resource_name": "customers/123/assets/456", "field_type": "HEADLINE"},
            {"asset_resource_name": "customers/123/assets/789", "field_type": "MARKETING_IMAGE"},
        ]
    """
    if not assets:
        return error_response("No assets provided.")

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        asset_group_service = client.get_service("AssetGroupService")
        asset_group_asset_service = client.get_service("AssetGroupAssetService")
        asset_group_rn = asset_group_service.asset_group_path(cid, asset_group_id)

        field_type_enum = client.get_type("AssetFieldTypeEnum").AssetFieldType

        operations = []
        for a in assets:
            op = client.client.operation("create", "AssetGroupAsset")
            link = op.create
            link.asset = a["asset_resource_name"]
            link.asset_group = asset_group_rn
            link.field_type = getattr(field_type_enum, a["field_type"])
            operations.append(op)

        response = asset_group_asset_service.mutate_asset_group_assets(
            customer_id=cid, operations=operations
        )
        results = [r.resource_name for r in response.results]
        return success_response(
            data={"resource_names": results, "count": len(results)},
            message=f"Linked {len(results)} asset(s) to asset group {asset_group_id}",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=DESTRUCTIVE)
def remove_asset_from_group(
    customer_id: str,
    asset_group_id: str,
    asset_resource_name: str,
    field_type: str,
    ctx: Context,
    confirm_removal: bool = False,
) -> dict:
    """Remove an asset from an asset group.

    Args:
        customer_id: Google Ads customer ID.
        asset_group_id: Asset group ID.
        asset_resource_name: Full resource name of the asset to unlink.
        field_type: The field type of the asset link (e.g., 'HEADLINE', 'MARKETING_IMAGE').
        confirm_removal: Must be True to proceed.
    """
    if not confirm_removal:
        return error_response(
            "Removal not confirmed. Set confirm_removal=True to remove this asset from the group."
        )

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        asset_group_asset_service = client.get_service("AssetGroupAssetService")

        asset_id = asset_resource_name.split("/")[-1]
        resource_name = f"customers/{cid}/assetGroupAssets/{asset_group_id}~{asset_id}~{field_type}"

        op = client.client.operation("remove", "AssetGroupAsset")
        op.remove = resource_name

        response = asset_group_asset_service.mutate_asset_group_assets(
            customer_id=cid, operations=[op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Asset removed from asset group {asset_group_id}",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=CREATE)
def add_audience_signal(
    customer_id: str,
    asset_group_id: str,
    ctx: Context,
    audience_resource_name: str | None = None,
    search_themes: list[str] | None = None,
) -> dict:
    """Add audience or search theme signals to a PMax asset group.

    Audience signals help Google's AI find the right customers. They're suggestions,
    not hard targeting constraints.

    Args:
        customer_id: Google Ads customer ID.
        asset_group_id: Asset group ID.
        audience_resource_name: Audience resource name (from audience manager).
        search_themes: List of search theme strings (keywords that describe your ideal customer).
    """
    if not audience_resource_name and not search_themes:
        return error_response("Provide either audience_resource_name or search_themes (or both).")

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        asset_group_service = client.get_service("AssetGroupService")
        asset_group_signal_service = client.get_service("AssetGroupSignalService")
        asset_group_rn = asset_group_service.asset_group_path(cid, asset_group_id)

        all_ops = []

        if audience_resource_name:
            op = client.client.operation("create", "AssetGroupSignal")
            signal = op.create
            signal.asset_group = asset_group_rn
            signal.audience.audience = audience_resource_name
            all_ops.append(op)

        if search_themes:
            for theme in search_themes:
                op = client.client.operation("create", "AssetGroupSignal")
                signal = op.create
                signal.asset_group = asset_group_rn
                search_theme_info = client.get_type("SearchThemeInfo")
                search_theme_info.text = theme
                signal.search_theme = search_theme_info
                all_ops.append(op)

        response = asset_group_signal_service.mutate_asset_group_signals(
            customer_id=cid, operations=all_ops
        )
        results = [r.resource_name for r in response.results]
        return success_response(
            data={"resource_names": results, "count": len(results)},
            message=f"Added {len(results)} audience signal(s) to asset group {asset_group_id}",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_asset_performance(
    customer_id: str,
    ctx: Context,
    campaign_id: str | None = None,
    asset_group_id: str | None = None,
) -> dict:
    """Get asset-level performance labels (BEST, GOOD, LOW, etc.) for PMax.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: Optional -- filter to a specific campaign.
        asset_group_id: Optional -- filter to a specific asset group.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        where_clauses = []
        if campaign_id:
            where_clauses.append(f"campaign.id = {campaign_id}")
        if asset_group_id:
            where_clauses.append(f"asset_group.id = {asset_group_id}")

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT
                asset_group.id,
                asset_group.name,
                asset_group_asset.field_type,
                asset_group_asset.status,
                asset.id,
                asset.name,
                asset.type,
                asset.text_asset.text,
                asset.image_asset.full_size.url,
                campaign.id,
                campaign.name
            FROM asset_group_asset
            {where}
            ORDER BY asset_group_asset.field_type
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"asset_performance": results, "count": len(results)},
            message=f"Asset performance: {len(results)} asset(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_pmax_placement_performance(
    customer_id: str,
    campaign_id: str,
    ctx: Context,
    date_range: str = "LAST_30_DAYS",
) -> dict:
    """Get PMax placement performance breakdown (Search, YouTube, Display, Discover, Gmail).

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: PMax campaign ID.
        date_range: Date range (predefined or 'YYYY-MM-DD,YYYY-MM-DD').
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        where_clauses = [f"campaign.id = {campaign_id}"]

        where_clauses.append(build_date_clause(date_range))

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                performance_max_placement_view.display_name,
                performance_max_placement_view.placement,
                performance_max_placement_view.placement_type,
                metrics.impressions
            FROM performance_max_placement_view
            WHERE {where}
            ORDER BY metrics.impressions DESC
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"placements": results, "count": len(results)},
            message=f"PMax placement performance: {len(results)} placement(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))
