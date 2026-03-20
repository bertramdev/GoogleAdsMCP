# Plan: Audit All GAQL Fields Against Google Ads API v23

## Context
We've found 4 GAQL field mismatches during live testing (invalid fields, wrong resource attributes, incompatible metrics). Since these were AI-generated queries, there are likely more. This plan systematically validates all 24 GAQL queries across 9 tool files against the actual API.

## Known Issues (already fixed in code, uncommitted)
1. `campaign.start_date` / `campaign.end_date` — not selectable GAQL fields (committed)
2. `asset_group_asset.performance_label` — doesn't exist; only on `ad_group_ad_asset_view`
3. `performance_max_placement_view` — only supports `metrics.impressions`
4. `get_field_metadata` — used `google_ads_field.` prefix; GoogleAdsFieldService doesn't use it

## Strategy

### Step 1: Fix `get_field_metadata` and restart
The fixes from last session (items 2-4) are in the code but the MCP server hasn't restarted. After restarting, `get_field_metadata` becomes our validation tool.

### Step 2: Validate each resource's fields programmatically
For each of the 13 unique FROM resources used in queries, call `get_field_metadata` to get the authoritative list of selectable fields. Cross-reference against what our queries use.

Resources to validate:
| Resource | Used In | Queries |
|----------|---------|---------|
| `customer` | accounts.py, reporting.py | 2 |
| `customer_client` | accounts.py | 1 |
| `campaign` | campaigns.py, budgets.py, reporting.py | 4 |
| `campaign_budget` | budgets.py | 1 |
| `ad_group` | ad_groups.py, reporting.py | 3 |
| `ad_group_ad` | ads.py | 2 |
| `ad_group_criterion` | keywords.py | 1 |
| `keyword_view` | keywords.py, reporting.py | 2 |
| `search_term_view` | reporting.py | 1 |
| `asset_group` | performance_max.py | 2 |
| `asset_group_asset` | performance_max.py | 2 |
| `asset_group_signal` | performance_max.py | 1 |
| `performance_max_placement_view` | performance_max.py | 1 |

Also validate metrics compatibility per resource (some metrics only work with certain FROM resources).

### Step 3: Fix any mismatches found
For each invalid field:
- If it has a valid replacement (e.g., renamed field) → replace
- If it's simply not selectable → remove from SELECT
- If a metric is incompatible with the resource → remove or find alternative

### Step 4: Test all fixed queries against live data
Re-run every read-only tool against JuiceLand (6238255881) to confirm no GAQL errors.

### Step 5: Add a validation test
Create a pytest test that programmatically extracts all GAQL queries from tool source files and validates field names against a known-good field list. This prevents regressions when queries are modified.

## Queries Already Validated (16/24 passed live testing)
- accounts.py: `get_account_info`, `get_account_hierarchy`
- campaigns.py: `list_campaigns`, `get_campaign`
- ad_groups.py: `list_ad_groups`
- ads.py: `list_ads`
- keywords.py: `list_keywords`, `get_keyword_performance`
- budgets.py: `list_budgets`, `get_budget_utilization`
- reporting.py: `get_campaign_performance`, `get_ad_group_performance`, `get_search_terms_report`, `get_keyword_performance_report`, `get_account_performance_summary`
- performance_max.py: `list_asset_groups`

## Queries Still Needing Validation (8/24)
- ads.py: `get_ad_details` — untested, has many RSA-specific fields
- ad_groups.py: `get_ad_group` — untested, has `ad_group.target_roas`, `ad_group.cpm_bid_micros`, `ad_group.ad_rotation_mode`
- performance_max.py: `get_asset_group_details` (3 sub-queries), `get_asset_performance`, `get_pmax_placement_performance`
- utilities.py: `get_field_metadata`

## Files to Modify
- `src/google_ads_mcp/tools/performance_max.py` — already has fixes pending
- `src/google_ads_mcp/tools/utilities.py` — already has fix pending
- `src/google_ads_mcp/tools/ad_groups.py` — may need fixes after validation
- `src/google_ads_mcp/tools/ads.py` — may need fixes after validation
- Any other file where validation reveals issues
- `tests/` — new validation test

## Verification
1. All 24 GAQL queries execute without field errors
2. `uv run pytest` passes
3. Commit and push
