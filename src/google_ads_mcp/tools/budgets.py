"""Budget management tools — create, update, list, and check utilization."""

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
def list_budgets(
    customer_id: str,
    ctx: Context,
    limit: int = 100,
) -> dict:
    """List campaign budgets in the account.

    Args:
        customer_id: Google Ads customer ID.
        limit: Max budgets to return (default 100).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        query = f"""
            SELECT
                campaign_budget.id,
                campaign_budget.name,
                campaign_budget.amount_micros,
                campaign_budget.delivery_method,
                campaign_budget.status,
                campaign_budget.explicitly_shared,
                campaign_budget.reference_count,
                campaign_budget.total_amount_micros
            FROM campaign_budget
            ORDER BY campaign_budget.name
            LIMIT {limit}
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"budgets": results, "count": len(results)},
            message=f"Found {len(results)} budget(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def create_budget(
    customer_id: str,
    name: str,
    amount: float,
    ctx: Context,
    delivery_method: str = "STANDARD",
    explicitly_shared: bool = False,
) -> dict:
    """Create a new campaign budget.

    Args:
        customer_id: Google Ads customer ID.
        name: Budget name.
        amount: Daily budget amount in currency (e.g., 50.00 for $50/day).
        delivery_method: 'STANDARD' (spread evenly) or 'ACCELERATED'.
        explicitly_shared: If True, budget can be shared across multiple campaigns.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        budget_service = client.get_service("CampaignBudgetService")
        budget_op = client.client.operation("create", "CampaignBudget")
        budget = budget_op.create
        budget.name = name
        budget.amount_micros = currency_to_micros(amount)
        budget.explicitly_shared = explicitly_shared

        delivery_enum = client.get_type("BudgetDeliveryMethodEnum").BudgetDeliveryMethod
        budget.delivery_method = getattr(delivery_enum, delivery_method)

        response = budget_service.mutate_campaign_budgets(
            customer_id=cid, operations=[budget_op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Budget '{name}' created (${amount:.2f}/day)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def update_budget(
    customer_id: str,
    budget_id: str,
    ctx: Context,
    amount: float | None = None,
    name: str | None = None,
    delivery_method: str | None = None,
) -> dict:
    """Update an existing campaign budget.

    Args:
        customer_id: Google Ads customer ID.
        budget_id: Budget ID to update.
        amount: New daily budget amount in currency.
        name: New budget name.
        delivery_method: New delivery method -- 'STANDARD' or 'ACCELERATED'.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        budget_service = client.get_service("CampaignBudgetService")
        budget_op = client.client.operation("update", "CampaignBudget")
        budget = budget_op.update
        budget.resource_name = budget_service.campaign_budget_path(cid, budget_id)

        update_mask = []
        if amount is not None:
            budget.amount_micros = currency_to_micros(amount)
            update_mask.append("amount_micros")
        if name is not None:
            budget.name = name
            update_mask.append("name")
        if delivery_method is not None:
            delivery_enum = client.get_type("BudgetDeliveryMethodEnum").BudgetDeliveryMethod
            budget.delivery_method = getattr(delivery_enum, delivery_method)
            update_mask.append("delivery_method")

        if not update_mask:
            return error_response("No fields to update. Provide at least one field.")

        from google.protobuf import field_mask_pb2

        budget_op.update_mask.CopyFrom(
            field_mask_pb2.FieldMask(paths=update_mask)
        )

        response = budget_service.mutate_campaign_budgets(
            customer_id=cid, operations=[budget_op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Budget {budget_id} updated successfully",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool()
def get_budget_utilization(
    customer_id: str,
    ctx: Context,
    date_range: str = "LAST_7_DAYS",
    campaign_id: str | None = None,
) -> dict:
    """Get budget vs actual spend for campaigns.

    Shows how much of each campaign's budget has been utilized.

    Args:
        customer_id: Google Ads customer ID.
        date_range: Date range (predefined or 'YYYY-MM-DD,YYYY-MM-DD').
        campaign_id: Optional -- filter to a single campaign.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = ["campaign.status = 'ENABLED'"]
        if campaign_id:
            where_clauses.append(f"campaign.id = {campaign_id}")

        if "," in date_range:
            start, end = date_range.split(",", 1)
            where_clauses.append(f"segments.date BETWEEN '{start.strip()}' AND '{end.strip()}'")
        else:
            where_clauses.append(f"segments.date DURING {date_range}")

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign_budget.amount_micros,
                segments.date,
                metrics.cost_micros
            FROM campaign
            WHERE {where}
            ORDER BY campaign.name, segments.date
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"utilization": results, "row_count": len(results)},
            message=f"Budget utilization: {len(results)} row(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))
