"""Custom exceptions for bulletin board system"""

from typing import Any, Dict, Optional


class BulletinBoardError(Exception):
    """Base exception for bulletin board system"""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class DatabaseError(BulletinBoardError):
    """Database operation errors"""

    pass


class ValidationError(BulletinBoardError):
    """Data validation errors"""

    pass


class AuthorizationError(BulletinBoardError):
    """Authorization/access control errors"""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, code="UNAUTHORIZED", **kwargs)


class NotFoundError(BulletinBoardError):
    """Resource not found errors"""

    def __init__(self, resource: str, identifier: Any = None, **kwargs):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, code="NOT_FOUND", **kwargs)


class ExternalAPIError(BulletinBoardError):
    """External API call errors"""

    def __init__(
        self, service: str, message: str, status_code: Optional[int] = None, **kwargs
    ):
        super().__init__(
            f"External API error ({service}): {message}",
            code="EXTERNAL_API_ERROR",
            details={
                "service": service,
                "status_code": status_code,
                **kwargs.get("details", {}),
            },
        )


class ConfigurationError(BulletinBoardError):
    """Configuration errors"""

    def __init__(self, message: str, missing_config: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if missing_config:
            details["missing_config"] = missing_config
        super().__init__(message, code="CONFIG_ERROR", details=details)


class RateLimitError(BulletinBoardError):
    """Rate limiting errors"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, code="RATE_LIMIT", details=details)
