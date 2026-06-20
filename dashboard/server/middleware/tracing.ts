import { Elysia } from "elysia";
import { logger } from "../utils/logger";

/**
 * Parses W3C traceparent or custom X-Trace-ID header.
 * Standard traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
 */
function parseTraceId(request: Request): string {
	const traceparent = request.headers.get("traceparent");
	if (traceparent) {
		const parts = traceparent.split("-");
		if (parts.length >= 2 && parts[1]) {
			return parts[1]; // Extract W3C Trace ID
		}
	}

	const xTraceId = request.headers.get("x-trace-id") || request.headers.get("X-Trace-ID");
	if (xTraceId) {
		return xTraceId;
	}

	return crypto.randomUUID();
}

/**
 * Format a W3C traceparent string given a Trace ID.
 */
function formatTraceparent(traceId: string): string {
	// If not a 32-character hex, convert UUID to 32-character hex (strip dashes)
	const cleanId = traceId.replace(/-/g, "").padEnd(32, "0").slice(0, 32);
	const parentId = Math.random().toString(16).substring(2, 18).padEnd(16, "0"); // 16 hex chars
	return `00-${cleanId}-${parentId}-01`;
}

export const tracingMiddleware = new Elysia()
	.derive({ as: "global" }, ({ request, set }) => {
		const traceId = parseTraceId(request);
		const traceparent = formatTraceparent(traceId);

		// Propagate trace headers in the response
		set.headers["X-Trace-ID"] = traceId;
		set.headers.traceparent = traceparent;

		const requestLogger = logger.child({ traceId });
		const startTime = performance.now();

		return {
			traceId,
			traceparent,
			log: requestLogger,
			_startTime: startTime,
		};
	})
	.onAfterResponse(({ request, log, _startTime, set }) => {
		const duration = Math.round(performance.now() - _startTime);
		const url = new URL(request.url);

		// Log access with method, path, status, and duration
		log.info(`${request.method} ${url.pathname} - ${set.status || 200}`, {
			method: request.method,
			path: url.pathname,
			status: set.status || 200,
			duration_ms: duration,
		});
	});
