"""Pydantic response models for Google Ads MCP tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolResponse(BaseModel):
    """Standard response wrapper for all tool results."""

    success: bool
    message: str = ""
    error: str = ""
    data: Any = None
    details: Any = None
