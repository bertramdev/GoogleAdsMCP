"""Keyword management tools — add, remove, update bids, get performance."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from google.protobuf import field_mask_pb2

from google_ads_mcp.helpers import (
    build_date_clause,
    currency_to_micros,
    error_response,
    execute_query,
    extract_google_ads_error,
    success_response,
)
from google_ads_mcp.annotations import CREATE, DESTRUCTIVE, READ_ONLY, UPDATE
from google_ads_mcp.server import get_client, mcp


@mcp.tool(annotations=READ_ONLY)
def list_keywords(
    customer_id: str,
    ad_group_id: str,
    ctx: Context,
    status_filter: str | None = None,
    limit: int = 200,
) -> dict:
    """List keywords in an ad group.

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID.
        status_filter: Optional -- 'ENABLED', 'PAUSED', or 'REMOVED'.
        limit: Max keywords to return (default 200).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = [
            f"ad_group.id = {ad_group_id}",
            "ad_group_criterion.type = 'KEYWORD'",
        ]
        if status_filter:
            where_clauses.append(f"ad_group_criterion.status = '{status_filter}'")
        else:
            where_clauses.append("ad_group_criterion.status != 'REMOVED'")

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group_criterion.cpc_bid_micros,
                ad_group_criterion.quality_info.quality_score,
                ad_group.id,
                ad_group.name
            FROM ad_group_criterion
            WHERE {where}
            ORDER BY ad_group_criterion.keyword.text
            LIMIT {limit}
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"keywords": results, "count": len(results)},
            message=f"Found {len(results)} keyword(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=CREATE)
def add_keywords(
    customer_id: str,
    ad_group_id: str,
    keywords: list[dict],
    ctx: Context,
) -> dict:
    """Add keywords to an ad group (batch operation).

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID to add keywords to.
        keywords: List of keyword dicts, each with:
            - text (str): The keyword text.
            - match_type (str): 'EXACT', 'PHRASE', or 'BROAD'.
            - cpc_bid (float, optional): Max CPC bid in currency.

    Example:
        keywords=[
            {"text": "buy shoes online", "match_type": "PHRASE", "cpc_bid": 1.50},
            {"text": "running shoes", "match_type": "BROAD"},
            {"text": "[red running shoes]", "match_type": "EXACT", "cpc_bid": 2.00},
        ]
    """
    if not keywords:
        return error_response("No keywords provided. Pass a list of keyword dicts.")

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ad_group_service = client.get_service("AdGroupService")
        ad_group_criterion_service = client.get_service("AdGroupCriterionService")

        operations = []
        for kw in keywords:
            text = kw.get("text", "").strip()
            match_type = kw.get("match_type", "BROAD").upper()
            cpc_bid = kw.get("cpc_bid")

            if not text:
                continue

            op = client.client.operation("create", "AdGroupCriterion")
            criterion = op.create
            criterion.ad_group = ad_group_service.ad_group_path(cid, ad_group_id)
            criterion.keyword.text = text

            match_enum = client.get_type("KeywordMatchTypeEnum").KeywordMatchType
            criterion.keyword.match_type = getattr(match_enum, match_type)

            status_enum = client.get_type("AdGroupCriterionStatusEnum").AdGroupCriterionStatus
            criterion.status = status_enum.ENABLED

            if cpc_bid is not None:
                criterion.cpc_bid_micros = currency_to_micros(cpc_bid)

            operations.append(op)

        if not operations:
            return error_response("No valid keywords to add after filtering.")

        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=cid, operations=operations
        )
        results = [r.resource_name for r in response.results]
        return success_response(
            data={"resource_names": results, "count": len(results)},
            message=f"Added {len(results)} keyword(s) to ad group {ad_group_id}",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=DESTRUCTIVE)
def remove_keyword(
    customer_id: str,
    ad_group_id: str,
    criterion_id: str,
    ctx: Context,
    confirm_removal: bool = False,
) -> dict:
    """Remove a keyword from an ad group.

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID containing the keyword.
        criterion_id: Keyword criterion ID to remove.
        confirm_removal: Must be True to proceed. Safety check.
    """
    if not confirm_removal:
        return error_response(
            "Removal not confirmed. Set confirm_removal=True to remove this keyword."
        )

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ad_group_criterion_service = client.get_service("AdGroupCriterionService")
        resource_name = ad_group_criterion_service.ad_group_criterion_path(
            cid, ad_group_id, criterion_id
        )

        op = client.client.operation("remove", "AdGroupCriterion")
        op.remove = resource_name

        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=cid, operations=[op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Keyword {criterion_id} removed from ad group {ad_group_id}",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=UPDATE)
def update_keyword_bid(
    customer_id: str,
    ad_group_id: str,
    criterion_id: str,
    cpc_bid: float,
    ctx: Context,
) -> dict:
    """Update the CPC bid for a keyword.

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID containing the keyword.
        criterion_id: Keyword criterion ID to update.
        cpc_bid: New max CPC bid in currency (e.g., 2.50 for $2.50).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ad_group_criterion_service = client.get_service("AdGroupCriterionService")

        op = client.client.operation("update", "AdGroupCriterion")
        criterion = op.update
        criterion.resource_name = ad_group_criterion_service.ad_group_criterion_path(
            cid, ad_group_id, criterion_id
        )
        criterion.cpc_bid_micros = currency_to_micros(cpc_bid)

        op.update_mask.CopyFrom(
            field_mask_pb2.FieldMask(paths=["cpc_bid_micros"])
        )

        response = ad_group_criterion_service.mutate_ad_group_criteria(
            customer_id=cid, operations=[op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Keyword {criterion_id} bid updated to ${cpc_bid:.2f}",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_keyword_performance(
    customer_id: str,
    ad_group_id: str,
    ctx: Context,
    date_range: str = "LAST_30_DAYS",
    limit: int = 100,
) -> dict:
    """Get keyword performance metrics for an ad group.

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID.
        date_range: Date range (predefined or 'YYYY-MM-DD,YYYY-MM-DD').
        limit: Max rows (default 100).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = [
            f"ad_group.id = {ad_group_id}",
            "ad_group_criterion.type = 'KEYWORD'",
            "ad_group_criterion.status != 'REMOVED'",
        ]

        where_clauses.append(build_date_clause(date_range))

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.quality_info.quality_score,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.cost_per_conversion
            FROM keyword_view
            WHERE {where}
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"keyword_performance": results, "row_count": len(results)},
            message=f"Keyword performance: {len(results)} row(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))
