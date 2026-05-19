import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from utils.logger import trace_var

logger = logging.getLogger("rpa.middleware.tracing")


class TracingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI / Starlette middleware that intercepts requests, propagates
    W3C traceparent or custom X-Trace-ID, sets contextvars, and records timing logs.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Parse W3C traceparent or custom X-Trace-ID header
        traceparent = request.headers.get("traceparent")
        x_trace_id = request.headers.get("x-trace-id") or request.headers.get("X-Trace-ID")

        trace_id = None
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 2 and parts[1]:
                trace_id = parts[1]  # Extract W3C Trace ID

        if not trace_id:
            trace_id = x_trace_id or str(uuid.uuid4())

        # 2. Bind the active Trace ID to async-safe context
        token = trace_var.set(trace_id)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            # Propagate back in response headers
            response.headers["X-Trace-ID"] = trace_id
            response.headers["traceparent"] = f"00-{trace_id.replace('-', '').ljust(32, '0')[:32]}-00f067aa0ba902b7-01"

            return response

        finally:
            duration = int((time.perf_counter() - start_time) * 1000)
            # Log the request completion
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code if 'response' in locals() else 500} ({duration}ms)",
                extra={"method": request.method, "path": request.url.path, "duration_ms": duration},
            )
            # Reset contextvar token
            trace_var.reset(token)
