# Google Ads MCP Server

A comprehensive Google Ads MCP server providing ~47 tools for full read/write access to Google Ads accounts. Built for Claude Desktop, Claude Code, and other MCP-compatible clients.

## Features

- **Accounts** — list accessible accounts, get account info, MCC hierarchy
- **Campaigns** — full CRUD for Search, Display, Video, Demand Gen campaigns
- **Ad Groups** — create, update, list, and manage ad groups
- **Ads** — RSA, Responsive Display, Video, and Demand Gen ad creation
- **Keywords** — add, remove, update bids, get performance
- **Performance Max** — complete PMax support: asset groups, assets, audience signals
- **Budgets** — create, update, list, and check utilization
- **Reporting** — flexible GAQL queries, campaign/ad group/keyword performance
- **Utilities** — GAQL resource discovery, field metadata, micros conversion

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Google Ads API credentials (developer token, GCP service account JSON key)

### Installation

```bash
git clone <repo-url>
cd GoogleAdsMCP
uv sync
```

### Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `GOOGLE_ADS_DEVELOPER_TOKEN` — your API developer token
- `GOOGLE_ADS_SERVICE_ACCOUNT_PATH` — path to GCP service account JSON key file
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` — MCC customer ID (if using MCC)

Optional:
- `GOOGLE_ADS_IMPERSONATED_EMAIL` — Workspace user email for domain-wide delegation
- `GOOGLE_ADS_CUSTOMER_ID` — default customer ID for operations

### Running

```bash
uv run google-ads-mcp
```

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/GoogleAdsMCP", "google-ads-mcp"],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "...",
        "GOOGLE_ADS_SERVICE_ACCOUNT_PATH": "/path/to/service-account.json",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "...",
        "GOOGLE_ADS_IMPERSONATED_EMAIL": "user@yourdomain.com"
      }
    }
  }
}
```

### Claude Code Configuration

Add to `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/GoogleAdsMCP", "google-ads-mcp"],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "...",
        "GOOGLE_ADS_SERVICE_ACCOUNT_PATH": "/path/to/service-account.json",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID": "...",
        "GOOGLE_ADS_IMPERSONATED_EMAIL": "user@yourdomain.com"
      }
    }
  }
}
```

## Testing

```bash
uv run pytest
```

## Tool Reference

See [PLAN.md](PLAN.md) for the full tool inventory with descriptions.
