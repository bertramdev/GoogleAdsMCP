"""Tests that every registered MCP tool has correct ToolAnnotations."""

from __future__ import annotations

import pytest

from google_ads_mcp.annotations import CREATE, DESTRUCTIVE, READ_ONLY, READ_ONLY_LOCAL, UPDATE
from google_ads_mcp.server import mcp

# ── Expected annotation mapping (tool name → annotation constant) ──────────

EXPECTED: dict[str, object] = {
    # accounts.py
    "list_accessible_accounts": READ_ONLY,
    "get_account_info": READ_ONLY,
    "get_account_hierarchy": READ_ONLY,
    # ad_groups.py
    "list_ad_groups": READ_ONLY,
    "get_ad_group": READ_ONLY,
    "create_ad_group": CREATE,
    "update_ad_group": UPDATE,
    "set_ad_group_status": DESTRUCTIVE,
    # ads.py
    "list_ads": READ_ONLY,
    "get_ad_details": READ_ONLY,
    "create_responsive_search_ad": CREATE,
    "create_responsive_display_ad": CREATE,
    "create_video_ad": CREATE,
    "create_demand_gen_ad": CREATE,
    "set_ad_status": DESTRUCTIVE,
    # budgets.py
    "list_budgets": READ_ONLY,
    "get_budget_utilization": READ_ONLY,
    "create_budget": CREATE,
    "update_budget": UPDATE,
    # campaigns.py
    "list_campaigns": READ_ONLY,
    "get_campaign": READ_ONLY,
    "create_campaign": CREATE,
    "update_campaign": UPDATE,
    "set_campaign_status": DESTRUCTIVE,
    "remove_campaign": DESTRUCTIVE,
    # keywords.py
    "list_keywords": READ_ONLY,
    "get_keyword_performance": READ_ONLY,
    "add_keywords": CREATE,
    "update_keyword_bid": UPDATE,
    "remove_keyword": DESTRUCTIVE,
    # performance_max.py
    "list_asset_groups": READ_ONLY,
    "get_asset_group_details": READ_ONLY,
    "get_asset_performance": READ_ONLY,
    "get_pmax_placement_performance": READ_ONLY,
    "create_performance_max_campaign": CREATE,
    "add_assets_to_group": CREATE,
    "add_audience_signal": CREATE,
    "remove_asset_from_group": DESTRUCTIVE,
    # reporting.py
    "execute_gaql": READ_ONLY,
    "get_campaign_performance": READ_ONLY,
    "get_ad_group_performance": READ_ONLY,
    "get_search_terms_report": READ_ONLY,
    "get_keyword_performance_report": READ_ONLY,
    "get_account_performance_summary": READ_ONLY,
    # utilities.py
    "list_gaql_resources": READ_ONLY_LOCAL,
    "get_field_metadata": READ_ONLY,
    "convert_micros": READ_ONLY_LOCAL,
}


def _get_tools() -> dict:
    """Return the registered tool map from FastMCP."""
    return mcp._tool_manager._tools


# ── Structural tests ───────────────────────────────────────────────────────


class TestAllToolsAnnotated:
    """Ensure every registered tool has annotations and is covered by the mapping."""

    def test_every_tool_has_annotations(self):
        for name, tool in _get_tools().items():
            assert tool.annotations is not None, f"Tool '{name}' is missing annotations"

    def test_no_unmapped_tools(self):
        registered = set(_get_tools().keys())
        mapped = set(EXPECTED.keys())
        unmapped = registered - mapped
        assert not unmapped, f"Tools registered but not in EXPECTED mapping: {unmapped}"

    def test_no_stale_mapping_entries(self):
        registered = set(_get_tools().keys())
        mapped = set(EXPECTED.keys())
        stale = mapped - registered
        assert not stale, f"EXPECTED has entries for non-existent tools: {stale}"

    def test_tool_count(self):
        assert len(_get_tools()) == 47, f"Expected 47 tools, found {len(_get_tools())}"


# ── Per-tool annotation correctness ───────────────────────────────────────


@pytest.mark.parametrize("tool_name,expected_ann", list(EXPECTED.items()))
def test_tool_annotation_matches(tool_name, expected_ann):
    tools = _get_tools()
    assert tool_name in tools, f"Tool '{tool_name}' not registered"
    actual = tools[tool_name].annotations
    assert actual == expected_ann, (
        f"Tool '{tool_name}' annotation mismatch:\n"
        f"  expected: {expected_ann}\n"
        f"  actual:   {actual}"
    )


# ── Category-level invariant tests ────────────────────────────────────────


class TestReadOnlyTools:
    """Read-only tools must have readOnlyHint=True."""

    @pytest.fixture
    def read_tools(self):
        return {n: _get_tools()[n] for n, a in EXPECTED.items() if a in (READ_ONLY, READ_ONLY_LOCAL)}

    def test_read_only_hint(self, read_tools):
        for name, tool in read_tools.items():
            assert tool.annotations.readOnlyHint is True, f"'{name}' should be readOnlyHint=True"


class TestCreateTools:
    """Create tools must not be destructive and must not be idempotent."""

    @pytest.fixture
    def create_tools(self):
        return {n: _get_tools()[n] for n, a in EXPECTED.items() if a is CREATE}

    def test_not_destructive(self, create_tools):
        for name, tool in create_tools.items():
            assert tool.annotations.destructiveHint is False, f"'{name}' should be destructiveHint=False"

    def test_not_idempotent(self, create_tools):
        for name, tool in create_tools.items():
            assert tool.annotations.idempotentHint is False, f"'{name}' should be idempotentHint=False"


class TestDestructiveTools:
    """Destructive tools must have destructiveHint=True."""

    @pytest.fixture
    def destructive_tools(self):
        return {n: _get_tools()[n] for n, a in EXPECTED.items() if a is DESTRUCTIVE}

    def test_destructive_hint(self, destructive_tools):
        for name, tool in destructive_tools.items():
            assert tool.annotations.destructiveHint is True, f"'{name}' should be destructiveHint=True"

    def test_idempotent(self, destructive_tools):
        for name, tool in destructive_tools.items():
            assert tool.annotations.idempotentHint is True, f"'{name}' should be idempotentHint=True"
