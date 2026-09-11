import time
from collections import defaultdict
from threading import Lock
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import logger


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter per client IP.
    Safeguards the enterprise API against denial of service and automated spam.
    Exempts health, metrics, and documentation endpoints.
    """

    EXEMPT_PATHS = {"/health", "/health/live", "/health/ready", "/metrics", "/docs", "/redoc", "/openapi.json", "/"}
    _lock = Lock()
    _requests = defaultdict(list)

    @classmethod
    def reset(cls):
        """Reset in-memory rate limiting counters (for testing and maintenance)."""
        with cls._lock:
            cls._requests.clear()

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Allow explicit header bypass for integration tests
        if request.headers.get("X-Bypass-Rate-Limit") == "true":
            return await call_next(request)

        # Exempt monitoring and metadata endpoints
        path = request.url.path
        if path in self.EXEMPT_PATHS or path.startswith("/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown_client"
        now = time.time()
        window_seconds = 60.0
        max_requests = settings.RATE_LIMIT_PER_MINUTE

        with self._lock:
            # Clean timestamps older than window
            valid_timestamps = [ts for ts in self._requests[client_ip] if now - ts < window_seconds]
            
            if len(valid_timestamps) >= max_requests:
                logger.warning(f"[RateLimiter] Client '{client_ip}' exceeded limit ({max_requests} req/min) on {path}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": {
                            "code": 429,
                            "message": f"Rate limit of {max_requests} requests per minute exceeded. Please try again later."
                        }
                    },
                    headers={"Retry-After": "60"}
                )

            valid_timestamps.append(now)
            self._requests[client_ip] = valid_timestamps

        return await call_next(request)
