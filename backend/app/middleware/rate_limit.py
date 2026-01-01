from slowapi import Limiter
from starlette.requests import Request


def get_real_client_ip(request: Request) -> str:
    """Extract real client IP, trusting X-Forwarded-For from our proxy.

    When behind a reverse proxy (like Caddy), the client's real IP is in
    the X-Forwarded-For header. We take the first IP (original client).
    Falls back to request.client.host for direct connections.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_real_client_ip)
