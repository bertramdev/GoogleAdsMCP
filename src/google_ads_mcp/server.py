"""FastMCP server definition with lifespan management."""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP

from .client import GoogleAdsClientWrapper
from .config import GoogleAdsSettings

# Configure logging to stderr only (critical for stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Shared application context available to all tools via lifespan."""

    client: GoogleAdsClientWrapper


def get_client(ctx: Context) -> GoogleAdsClientWrapper:
    """Extract the GoogleAdsClientWrapper from MCP tool context."""
    return ctx.request_context.lifespan_context.client


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Initialize the Google Ads client on server startup."""
    logger.info("Starting Google Ads MCP server...")
    try:
        settings = GoogleAdsSettings()
        client_wrapper = GoogleAdsClientWrapper(settings)
        logger.info("Google Ads client initialized successfully")
        yield AppContext(client=client_wrapper)
    except Exception as e:
        logger.error(f"Failed to initialize Google Ads client: {e}")
        raise
    finally:
        logger.info("Google Ads MCP server shutting down")


mcp = FastMCP(
    "Google Ads MCP",
    instructions="Comprehensive Google Ads management with ~47 tools for campaigns, ads, keywords, Performance Max, reporting, and more.",
    lifespan=app_lifespan,
)

# Import all tool modules to register their decorators
import google_ads_mcp.tools  # noqa: E402, F401


def main():
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
