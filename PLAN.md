# Google Ads MCP Server — Implementation Plan

## Context

Build a comprehensive Google Ads MCP server in Python that provides full read/write access to Google Ads accounts. The official Google Ads MCP is read-only with only 2 tools. This implementation will expose ~47 tools across 9 categories — campaign management, ad groups, ads, keywords, budgets, **Performance Max** (asset groups, assets, audience signals), reporting, accounts, and utilities. It runs locally via stdio transport for use with Claude Desktop, Claude Code, and potentially OpenAI/Gemini.

**Campaign type scope**: Full write support for **Search** and **Performance Max**. Ad creation tools also included for **Display** (responsive display ads), **Video** (in-stream/bumper/in-feed), and **Demand Gen**. Shopping is read-only (requires Merchant Center integration). Campaign CRUD, ad group CRUD, and keyword management work for all channel types that use the standard ad group model. The flexible `execute_gaql` tool covers reads for any campaign type.

User already has Google Ads API credentials configured.

---

## Tech Stack

- **Python 3.14** with `uv` for dependency management
- **`mcp[cli]>=1.26.0`** — official MCP Python SDK with FastMCP
- **`google-ads>=29.2.0`** — Google Ads Python client (API v19)
- **`pydantic>=2.0` + `pydantic-settings>=2.0`** — config and response models
- **`python-dotenv>=1.0.0`** — `.env` file loading
- **`hatchling`** — build backend
- **`pytest` + `pytest-asyncio`** — testing

---

## Project Structure

```
GoogleAdsMCP/
├── pyproject.toml
├── .python-version
├── .gitignore
├── .env.example
├── README.md
├── CLAUDE.md
├── src/
│   └── google_ads_mcp/
│       ├── __init__.py
│       ├── server.py
│       ├── config.py
│       ├── client.py
│       ├── helpers.py
│       ├── models.py
│       ├── exceptions.py
│       └── tools/
│           ├── __init__.py
│           ├── accounts.py
│           ├── campaigns.py
│           ├── ad_groups.py
│           ├── ads.py
│           ├── keywords.py
│           ├── budgets.py
│           ├── performance_max.py
│           ├── reporting.py
│           └── utilities.py
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_helpers.py
    └── test_tools/
        └── (one file per tool module)
```

---

## Tool Inventory (~47 tools)

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
