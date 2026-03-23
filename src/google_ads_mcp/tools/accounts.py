"""Account management tools — list accounts, get info, hierarchy."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from google_ads_mcp.annotations import READ_ONLY
from google_ads_mcp.helpers import (
    error_response,
    execute_query,
    extract_google_ads_error,
    success_response,
)
from google_ads_mcp.server import get_client, mcp


@mcp.tool(annotations=READ_ONLY)
def list_accessible_accounts(ctx: Context) -> dict:
    """List all Google Ads accounts accessible via current credentials.

    Returns accounts accessible through the authenticated MCC or direct account.
    """
    try:
        client = get_client(ctx)
        customer_service = client.get_service("CustomerService")
        response = customer_service.list_accessible_customers()
        accounts = [rn.split("/")[-1] for rn in response.resource_names]
        return success_response(
            data={"accounts": accounts, "count": len(accounts)},
            message=f"Found {len(accounts)} accessible account(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_account_info(customer_id: str, ctx: Context) -> dict:
    """Get details for a Google Ads account (name, currency, timezone, etc.).

    Args:
        customer_id: Google Ads customer ID (e.g., '123-456-7890' or '1234567890').
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        query = """
            SELECT
                customer.id,
                customer.descriptive_name,
                customer.currency_code,
                customer.time_zone,
                customer.manager,
                customer.test_account,
                customer.auto_tagging_enabled,
                customer.tracking_url_template
            FROM customer
            LIMIT 1
        """
        results = execute_query(client, cid, query)
        if not results:
            return error_response(f"No account found for customer ID {customer_id}")
        return success_response(data=results[0])
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_account_hierarchy(ctx: Context, customer_id: str | None = None) -> dict:
    """Get the MCC account hierarchy tree.

    Lists all child accounts under the given MCC account.

    Args:
        customer_id: MCC customer ID. Uses default if not provided.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        query = """
            SELECT
                customer_client.client_customer,
                customer_client.id,
                customer_client.descriptive_name,
                customer_client.currency_code,
                customer_client.time_zone,
                customer_client.manager,
                customer_client.level,
                customer_client.test_account,
                customer_client.status
            FROM customer_client
            ORDER BY customer_client.level, customer_client.descriptive_name
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"hierarchy": results, "count": len(results)},
            message=f"Found {len(results)} account(s) in hierarchy",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))
