"""Validate all GAQL queries in tool source files against known-good field rules.

Prevents regressions from invalid GAQL fields, wrong resource attributes,
and incompatible metrics. See docs/gaql-field-audit-plan.md for context.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).parent.parent / "src" / "google_ads_mcp" / "tools"

# Valid field prefixes for each FROM resource (including joinable resources)
RESOURCE_VALID_PREFIXES: dict[str, set[str]] = {
    "customer": {"customer", "metrics", "segments"},
    "customer_client": {"customer_client"},
    "campaign": {"campaign", "campaign_budget", "metrics", "segments"},
    "campaign_budget": {"campaign_budget"},
    "ad_group": {"ad_group", "campaign", "metrics", "segments"},
    "ad_group_ad": {"ad_group_ad", "ad_group", "campaign", "metrics", "segments"},
    "ad_group_criterion": {"ad_group_criterion", "ad_group", "campaign", "metrics", "segments"},
    "keyword_view": {"ad_group_criterion", "ad_group", "campaign", "metrics", "segments"},
    "search_term_view": {"search_term_view", "ad_group", "campaign", "metrics", "segments"},
    "asset_group": {"asset_group", "campaign"},
    "asset_group_asset": {"asset_group_asset", "asset_group", "asset", "campaign"},
    "asset_group_signal": {"asset_group_signal", "asset_group"},
    "performance_max_placement_view": {
        "performance_max_placement_view",
        "campaign",
        "metrics",
        "segments",
    },
}

# Known-invalid fields that must never appear in queries (regression blocklist)
BLOCKED_FIELDS = {
    "asset_group_asset.performance_label",  # doesn't exist; only on ad_group_ad_asset_view
    "campaign.start_date",  # not selectable in GAQL
    "campaign.end_date",  # not selectable in GAQL
}

# Metrics incompatible with specific FROM resources
BLOCKED_METRICS_PER_RESOURCE: dict[str, set[str]] = {
    "performance_max_placement_view": {
        "metrics.clicks",
        "metrics.cost_micros",
        "metrics.conversions",
        "metrics.ctr",
        "metrics.average_cpc",
        "metrics.cost_per_conversion",
        "metrics.conversions_value",
        "metrics.all_conversions",
        "metrics.interactions",
        "metrics.interaction_rate",
    },
}


def extract_gaql_queries(source: str) -> list[dict[str, str | list[str]]]:
    """Extract GAQL queries from Python source code.

    Finds GAQL queries inside string literals (triple-quoted strings) by
    first extracting all string contents, then matching SELECT...FROM patterns.

    Returns list of dicts with 'select_fields', 'from_resource', and 'raw' keys.
    """
    # Extract triple-quoted string contents (both f-strings and regular)
    string_pattern = re.compile(r'[fF]?"""(.*?)"""', re.DOTALL)
    select_pattern = re.compile(
        r"SELECT\s+(.*?)\s+FROM\s+(\w+)",
        re.DOTALL | re.IGNORECASE,
    )

    queries = []
    for string_match in string_pattern.finditer(source):
        string_content = string_match.group(1)

        for match in select_pattern.finditer(string_content):
            select_block = match.group(1)
            from_resource = match.group(2).strip()

            # Skip GoogleAdsFieldService queries (different API, not GAQL)
            if from_resource == "google_ads_field":
                continue

            # Parse SELECT fields
            raw_fields = [f.strip() for f in select_block.split(",")]
            fields = []
            for f in raw_fields:
                cleaned = f.strip()
                if not cleaned or cleaned.startswith("{") or cleaned.startswith("--"):
                    continue
                # Take only the field name (first word-like token with dots)
                field_match = re.match(r"([\w.]+)", cleaned)
                if field_match:
                    fields.append(field_match.group(1))

            # Skip docstring examples (contain '...' or have no real fields)
            if not fields or "..." in " ".join(fields):
                continue

            # Must have at least one field with a dot (resource.attribute)
            if not any("." in f for f in fields):
                continue

            queries.append({
                "select_fields": fields,
                "from_resource": from_resource,
                "raw": match.group(0)[:200],
            })

    return queries


def get_all_tool_queries() -> list[tuple[str, dict]]:
    """Collect all GAQL queries from all tool files.

    Returns list of (filename, query_info) tuples.
    """
    results = []
    for py_file in sorted(TOOLS_DIR.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text()
        queries = extract_gaql_queries(source)
        for q in queries:
            results.append((py_file.name, q))
    return results


ALL_QUERIES = get_all_tool_queries()


@pytest.mark.parametrize(
    "filename,query",
    ALL_QUERIES,
    ids=[f"{fn}:{q['from_resource']}" for fn, q in ALL_QUERIES],
)
def test_field_prefixes_match_resource(filename: str, query: dict) -> None:
    """Every SELECTed field must have a prefix valid for the FROM resource."""
    from_resource = query["from_resource"]
    valid_prefixes = RESOURCE_VALID_PREFIXES.get(from_resource)

    if valid_prefixes is None:
        pytest.skip(f"No prefix rules defined for resource '{from_resource}'")

    for field in query["select_fields"]:
        prefix = field.split(".")[0]
        assert prefix in valid_prefixes, (
            f"{filename}: field '{field}' has prefix '{prefix}' which is not valid "
            f"for FROM {from_resource}. Valid prefixes: {sorted(valid_prefixes)}"
        )


@pytest.mark.parametrize(
    "filename,query",
    ALL_QUERIES,
    ids=[f"{fn}:{q['from_resource']}" for fn, q in ALL_QUERIES],
)
def test_no_blocked_fields(filename: str, query: dict) -> None:
    """No query should use a known-invalid field."""
    for field in query["select_fields"]:
        assert field not in BLOCKED_FIELDS, (
            f"{filename}: field '{field}' is in the blocklist — "
            f"it is not a valid GAQL field."
        )


@pytest.mark.parametrize(
    "filename,query",
    ALL_QUERIES,
    ids=[f"{fn}:{q['from_resource']}" for fn, q in ALL_QUERIES],
)
def test_no_incompatible_metrics(filename: str, query: dict) -> None:
    """No query should use metrics incompatible with its FROM resource."""
    from_resource = query["from_resource"]
    blocked_metrics = BLOCKED_METRICS_PER_RESOURCE.get(from_resource, set())

    for field in query["select_fields"]:
        assert field not in blocked_metrics, (
            f"{filename}: metric '{field}' is incompatible with "
            f"FROM {from_resource}."
        )


def test_all_from_resources_have_prefix_rules() -> None:
    """Every FROM resource used in queries should have prefix validation rules."""
    resources_used = {q["from_resource"] for _, q in ALL_QUERIES}
    missing = resources_used - set(RESOURCE_VALID_PREFIXES.keys())
    assert not missing, (
        f"These FROM resources have no prefix rules defined: {sorted(missing)}. "
        f"Add them to RESOURCE_VALID_PREFIXES."
    )


def test_query_extraction_finds_expected_count() -> None:
    """Sanity check: we should find at least 20 GAQL queries across all tools."""
    assert len(ALL_QUERIES) >= 20, (
        f"Expected at least 20 GAQL queries but found {len(ALL_QUERIES)}. "
        f"The extraction regex may need updating."
    )
