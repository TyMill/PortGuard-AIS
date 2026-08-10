"""Package-specific exception hierarchy."""


class PortGuardError(Exception):
    """Base exception for PortGuard-AIS."""


class InputSchemaError(PortGuardError):
    """Raised when AIS input does not satisfy the expected schema."""


class ConfigurationError(PortGuardError):
    """Raised when runtime configuration is internally inconsistent."""
