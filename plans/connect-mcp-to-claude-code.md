# Plan: Connect Google Ads MCP to Claude Code for Real-World Testing

## Context
The Google Ads MCP server (47 tools) is built and has credentials configured in `.env`. We need to register it as an MCP server in Claude Code so we can invoke its tools interactively from this session.

## Step 1: Add MCP server config

MCP servers are defined in `.mcp.json` (not `settings.local.json`). Created `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/tlong/VSProjects/MCPs/GoogleAdsMCP", "google-ads-mcp"],
      "cwd": "/Users/tlong/VSProjects/MCPs/GoogleAdsMCP"
    }
  }
}
```

Also added to `.claude/settings.local.json`:
```json
{ "enableAllProjectMcpServers": true }
```

Key details:
- `cwd` ensures Pydantic Settings finds the `.env` file (it loads from CWD)
- `--directory` ensures uv resolves the project correctly
- `.mcp.json` added to `.gitignore` to keep local paths out of git

## Step 2: Restart Claude Code session

After updating settings, the user needs to restart Claude Code (`/exit` and reopen) so it picks up the new MCP server and starts the process.

## Step 3: Test incrementally (read-only first)

1. **Stateless utility** — call `convert_micros` or `list_gaql_resources` (no API call, verifies server connectivity)
2. **Auth test** — call `list_accessible_accounts` (first real API call, confirms credentials work)
3. **Account info** — call `get_account_info` with a customer ID from step 2
4. **Reporting** — call `get_account_performance_summary` or `execute_gaql` with a simple query
5. **Campaign data** — call `list_campaigns` to see real campaign data

## Step 4: Troubleshoot if needed

Common issues:
- `.env` not found → check `cwd` in server config
- Auth errors → verify service account path, developer token, impersonated email
- MCC errors → ensure `login_customer_id` is set if using MCC account
- Server not starting → run `uv run --directory /Users/tlong/VSProjects/MCPs/GoogleAdsMCP google-ads-mcp` manually to see stderr

## Files modified
- `.mcp.json` — MCP server definition (created)
- `.claude/settings.local.json` — added `enableAllProjectMcpServers: true`
- `.gitignore` — added `.mcp.json`

## Verification
After restart, Claude Code should show the google-ads MCP tools available. We test by calling tools in order of complexity (stateless → auth-required → data queries).
