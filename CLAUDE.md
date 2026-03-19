# Google Ads MCP Server

## Project Overview
A comprehensive Google Ads MCP server providing ~47 tools across 9 categories for full read/write access to Google Ads accounts via the MCP protocol.

## Tech Stack
- Python 3.14, uv for dependency management
- `mcp[cli]` (FastMCP) for MCP server
- `google-ads` Python client library (API v19)
- Pydantic v2 for config and models
- pytest for testing

## Architecture
- `src/google_ads_mcp/` — main package
- `src/google_ads_mcp/tools/` — tool modules (one per category)
- Tools return dicts, never raise exceptions (structured error responses)
- Destructive operations require `confirm=True` parameter
- All logging to stderr (stdio transport requirement)
- `json_response=True` on FastMCP for LLM-friendly output

## Key Patterns
- `sanitize_customer_id()` strips dashes: "123-456-7890" → "1234567890"
- `proto_to_dict()` converts protobuf objects to dicts
- Micros conversion: $1.00 = 1,000,000 micros
- Lifespan pattern for shared GoogleAdsClient instance
- Tools registered via decorators in tool modules, imported in `tools/__init__.py`

## Commands
- `uv run google-ads-mcp` — start server
- `uv run pytest` — run tests
- `uv sync` — install dependencies

## Conventions
- Conventional commits (feat:, fix:, docs:, etc.)
- Google-style docstrings
- Type hints on all public functions
- Black formatting, isort for imports
