import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        # Log incoming request path and method
        logger.info(f"--> Incoming {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        process_time = (time.perf_counter() - start_time) * 1000
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        
        logger.info(f"<-- Completed {request.method} {request.url.path} with status {response.status_code} in {process_time:.2f}ms")
        return response
