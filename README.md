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

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Google Ads API credentials (developer token, GCP service account JSON key)

### Installation

```bash
git clone https://github.com/bertramdev/GoogleAdsMCP.git
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

Add to `.mcp.json` in the project root:

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

### Permissions

All tools include [MCP tool annotations](https://modelcontextprotocol.io/docs/concepts/tool-annotations) (`readOnlyHint`, `destructiveHint`, etc.) so clients can make informed permission decisions. However, Claude Code requires explicit allow rules — annotations alone don't auto-approve tools.

**Within this project:** The project-level `.claude/settings.json` auto-allows read-only tools (`get_*`, `list_*`, `execute_gaql`, `convert_micros`). Write tools require approval on each use.

**From other projects:** Project-level permissions don't apply. To allow all tools globally, add to `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__google-ads__*"
    ]
  }
}
```

Or for read-only tools only:

```json
{
  "permissions": {
    "allow": [
      "mcp__google-ads__get_*",
      "mcp__google-ads__list_*",
      "mcp__google-ads__execute_gaql",
      "mcp__google-ads__convert_micros"
    ]
  }
}
```

### Security Considerations

This MCP server **cannot** modify account access, user permissions, login credentials, billing, or payment methods. There are no tools for account administration — a compromised server cannot lock anyone out of their account.

**Worst-case impact if credentials are compromised:**

| Risk | Details |
|------|---------|
| **Financial** | Creating campaigns/budgets or increasing keyword bids could spend money |
| **Disruption** | Pausing/removing campaigns, keywords, or ad groups |
| **Data exposure** | Reading account performance, search terms, and campaign details. `execute_gaql` can also read sensitive resources like `customer_user_access` and `billing_setup` (read-only — no mutations possible via GAQL) |

Removal tools (`remove_campaign`, `remove_keyword`, `remove_asset_from_group`) require `confirm_removal=True` as a server-side safety guard. The `set_*_status` tools execute immediately without a confirmation parameter.

## Testing

```bash
uv run pytest
```

## Tool Reference (47 tools)

### Accounts (3)
- `list_accessible_accounts` — List accounts accessible via credentials
- `get_account_info` — Account details (name, currency, timezone)
- `get_account_hierarchy` — MCC hierarchy tree

### Campaigns (6)
- `list_campaigns` — List campaigns with optional status filter
- `get_campaign` — Single campaign details
- `create_campaign` — Create Search/Display campaign with budget
- `update_campaign` — Update name, bidding strategy, etc.
- `set_campaign_status` — Enable/pause/remove
- `remove_campaign` — Soft delete with confirm

### Ad Groups (5)
- `list_ad_groups` — List ad groups in campaign
- `get_ad_group` — Ad group details
- `create_ad_group` — Create ad group with bid
- `update_ad_group` — Update name, bid, status
- `set_ad_group_status` — Enable/pause/remove

### Ads (7)
- `list_ads` — List ads in ad group
- `create_responsive_search_ad` — RSA for Search campaigns
- `create_responsive_display_ad` — Responsive display ad
- `create_video_ad` — Video ad for YouTube
- `create_demand_gen_ad` — Demand Gen ad
- `set_ad_status` — Enable/pause/remove
- `get_ad_details` — Full ad details

### Keywords (5)
- `list_keywords` — List keywords in ad group
- `add_keywords` — Add keywords with match types (batch)
- `remove_keyword` — Remove keyword
- `update_keyword_bid` — Update CPC bid
- `get_keyword_performance` — Keyword metrics

### Performance Max (8)
- `create_performance_max_campaign` — Full PMax campaign creation
- `list_asset_groups` — List asset groups in PMax campaign
- `get_asset_group_details` — Asset group details with linked assets
- `add_assets_to_group` — Add assets to asset group
- `remove_asset_from_group` — Remove asset from asset group
- `add_audience_signal` — Add audience/search theme signals
- `get_asset_performance` — Asset-level performance labels
- `get_pmax_placement_performance` — Channel breakdown

### Budgets (4)
- `list_budgets` — List campaign budgets
- `create_budget` — Create shared budget
- `update_budget` — Update budget amount
- `get_budget_utilization` — Budget vs actual spend

### Reporting (6)
- `execute_gaql` — Flexible GAQL query execution
- `get_campaign_performance` — Campaign metrics
- `get_ad_group_performance` — Ad group metrics
- `get_search_terms_report` — Search terms report
- `get_keyword_performance_report` — Keyword metrics
- `get_account_performance_summary` — Account daily summary

### Utilities (3)
- `list_gaql_resources` — Available GAQL resources
- `get_field_metadata` — Field metadata for a resource
- `convert_micros` — Micros to currency conversion

## License

Apache 2.0 — see [LICENSE](LICENSE).
