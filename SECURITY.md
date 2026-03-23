# Security

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please open a [GitHub Issue](https://github.com/bertramdev/GoogleAdsMCP/issues) with the label `security`.

## Scope

This MCP server provides read/write access to Google Ads accounts. See the [Security Considerations](README.md#security-considerations) section in the README for a detailed analysis of the impact surface.

Key points:
- The server **cannot** modify account access, user permissions, credentials, or billing
- Write tools can create/modify campaigns, ad groups, ads, keywords, and budgets
- Removal tools require `confirm_removal=True` as a server-side safety guard
- `execute_gaql` can read sensitive resources like `customer_user_access` (read-only)
