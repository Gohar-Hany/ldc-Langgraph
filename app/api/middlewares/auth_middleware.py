import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger
from app.services.metrics_service import metrics_service


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Injects and propagates unique Correlation IDs (X-Request-ID).
    2. Measures exact processing latency (X-Process-Time-Ms).
    3. Feeds telemetry data into MetricsService for Prometheus/Grafana observability.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate correlation ID
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        
        start_time = time.perf_counter()
        logger.info(f"--> [{request_id}] Incoming {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        process_time = (time.perf_counter() - start_time) * 1000
        
        # Inject standard telemetry headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        
        # Record into MetricsService
        metrics_service.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=process_time
        )
        
        logger.info(
            f"<-- [{request_id}] Completed {request.method} {request.url.path} "
            f"with status {response.status_code} in {process_time:.2f}ms"
        )
        return response
