"""Custom exception types for Google Ads MCP."""


class GoogleAdsMCPError(Exception):
    """Base exception for Google Ads MCP."""


class ConfigurationError(GoogleAdsMCPError):
    """Raised when required configuration is missing or invalid."""


class AuthenticationError(GoogleAdsMCPError):
    """Raised when Google Ads authentication fails."""


class CustomerNotFoundError(GoogleAdsMCPError):
    """Raised when a customer ID is not found or inaccessible."""


class QueryError(GoogleAdsMCPError):
    """Raised when a GAQL query fails."""


class MutationError(GoogleAdsMCPError):
    """Raised when a mutate operation fails."""


class ConfirmationRequiredError(GoogleAdsMCPError):
    """Raised when a destructive operation requires confirmation."""
