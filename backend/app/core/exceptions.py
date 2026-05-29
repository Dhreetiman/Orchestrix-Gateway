from fastapi import status


class GatewayError(Exception):
    """Base class for gateway-domain errors that map to HTTP responses."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"

    def __init__(self, message: str, *, detail: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


class AuthError(GatewayError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"


class RateLimitError(GatewayError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limited"


class ProviderError(GatewayError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "provider_error"


class ProviderNotFoundError(GatewayError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "provider_not_found"


class ValidationError(GatewayError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "validation_error"
