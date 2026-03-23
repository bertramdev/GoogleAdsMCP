"""Centralized MCP ToolAnnotations for all Google Ads tools."""

from mcp.types import ToolAnnotations

# --- Read-only tools (24) — query the Google Ads API but never mutate ---
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    openWorldHint=True,
)

# --- Read-only local tools (2) — pure computation, no API call ---
READ_ONLY_LOCAL = ToolAnnotations(
    readOnlyHint=True,
    openWorldHint=False,
)

# --- Create tools (11) — create new resources; NOT idempotent ---
CREATE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)

# --- Update tools (4) — modify existing resources; idempotent ---
UPDATE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

# --- Destructive tools (6) — remove or set REMOVED status; idempotent ---
DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=True,
)
