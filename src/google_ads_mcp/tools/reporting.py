"""Reporting tools — GAQL execution, campaign/ad group/keyword performance."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from google_ads_mcp.helpers import (
    build_date_clause,
    error_response,
    execute_query,
    extract_google_ads_error,
    success_response,
)
from google_ads_mcp.annotations import READ_ONLY
from google_ads_mcp.server import get_client, mcp


@mcp.tool(annotations=READ_ONLY)
def execute_gaql(
    customer_id: str,
    query: str,
    ctx: Context,
) -> dict:
    """Execute an arbitrary GAQL (Google Ads Query Language) query.

    This is the most flexible tool -- use it for any read query not covered by other tools.
    GAQL reference: https://developers.google.com/google-ads/api/docs/query/overview

    Args:
        customer_id: Google Ads customer ID.
        query: Full GAQL query string (SELECT ... FROM ... WHERE ...).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        results = execute_query(client, cid, query)
        return success_response(
            data={"results": results, "row_count": len(results)},
            message=f"Query returned {len(results)} row(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_campaign_performance(
    customer_id: str,
    ctx: Context,
    date_range: str = "LAST_30_DAYS",
    campaign_id: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
) -> dict:
    """Get campaign performance metrics over a date range.

    Args:
        customer_id: Google Ads customer ID.
        date_range: Date range -- use predefined (LAST_7_DAYS, LAST_30_DAYS, THIS_MONTH,
            LAST_MONTH, etc.) or custom 'YYYY-MM-DD,YYYY-MM-DD'.
        campaign_id: Optional -- filter to a single campaign.
        status_filter: Optional -- filter by status (ENABLED, PAUSED, REMOVED).
        limit: Max rows to return (default 50).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = []
        if campaign_id:
            where_clauses.append(f"campaign.id = {campaign_id}")
        if status_filter:
            where_clauses.append(f"campaign.status = '{status_filter}'")

        where_clauses.append(build_date_clause(date_range))

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_per_conversion
            FROM campaign
            WHERE {where}
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"performance": results, "row_count": len(results)},
            message=f"Campaign performance: {len(results)} row(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_ad_group_performance(
    customer_id: str,
    ctx: Context,
    campaign_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
    limit: int = 50,
) -> dict:
    """Get ad group performance metrics.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: Optional -- filter to ad groups in this campaign.
        date_range: Date range (predefined or 'YYYY-MM-DD,YYYY-MM-DD').
        limit: Max rows (default 50).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = []
        if campaign_id:
            where_clauses.append(f"campaign.id = {campaign_id}")

        where_clauses.append(build_date_clause(date_range))

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.cost_per_conversion
            FROM ad_group
            WHERE {where}
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"performance": results, "row_count": len(results)},
            message=f"Ad group performance: {len(results)} row(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_search_terms_report(
    customer_id: str,
    ctx: Context,
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
    limit: int = 100,
) -> dict:
    """Get search terms that triggered your ads.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: Optional campaign filter.
        ad_group_id: Optional ad group filter.
        date_range: Date range (predefined or 'YYYY-MM-DD,YYYY-MM-DD').
        limit: Max rows (default 100).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = []
        if campaign_id:
            where_clauses.append(f"campaign.id = {campaign_id}")
        if ad_group_id:
            where_clauses.append(f"ad_group.id = {ad_group_id}")

        where_clauses.append(build_date_clause(date_range))

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                search_term_view.search_term,
                search_term_view.status,
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.cost_micros,
                metrics.conversions
            FROM search_term_view
            WHERE {where}
            ORDER BY metrics.impressions DESC
            LIMIT {limit}
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"search_terms": results, "row_count": len(results)},
            message=f"Search terms report: {len(results)} row(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_keyword_performance_report(
    customer_id: str,
    ctx: Context,
    campaign_id: str | None = None,
    ad_group_id: str | None = None,
    date_range: str = "LAST_30_DAYS",
    limit: int = 100,
) -> dict:
    """Get keyword-level performance metrics.

    Args:
        customer_id: Google Ads customer ID.
        campaign_id: Optional campaign filter.
        ad_group_id: Optional ad group filter.
        date_range: Date range (predefined or 'YYYY-MM-DD,YYYY-MM-DD').
        limit: Max rows (default 100).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = [
            "ad_group_criterion.type = 'KEYWORD'",
            "ad_group_criterion.status != 'REMOVED'",
        ]
        if campaign_id:
            where_clauses.append(f"campaign.id = {campaign_id}")
        if ad_group_id:
            where_clauses.append(f"ad_group.id = {ad_group_id}")

        where_clauses.append(build_date_clause(date_range))

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.quality_info.quality_score,
                segments.date,
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
            data={"keywords": results, "row_count": len(results)},
            message=f"Keyword performance: {len(results)} row(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_account_performance_summary(
    customer_id: str,
    ctx: Context,
    date_range: str = "LAST_30_DAYS",
) -> dict:
    """Get account-level daily performance summary.

    Args:
        customer_id: Google Ads customer ID.
        date_range: Date range (predefined or 'YYYY-MM-DD,YYYY-MM-DD').
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = []
        where_clauses.append(build_date_clause(date_range))

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_per_conversion,
                metrics.all_conversions,
                metrics.interactions,
                metrics.interaction_rate
            FROM customer
            WHERE {where}
            ORDER BY segments.date DESC
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"daily_summary": results, "row_count": len(results)},
            message=f"Account performance: {len(results)} day(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))
