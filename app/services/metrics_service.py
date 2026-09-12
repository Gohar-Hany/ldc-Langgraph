import time
from collections import defaultdict
from threading import Lock
from typing import Any, Dict

from app.core.config import settings


class MetricsService:
    """
    Thread-safe in-memory observability & telemetry collector.
    Tracks requests, latencies, LLM usage, RAG retrievals, tool calls,
    and exports data in both structured JSON and Prometheus format.
    """

    def __init__(self):
        self._lock = Lock()
        self.start_time = time.time()
        self.total_requests = 0
        self.total_latency_ms = 0.0
        self.requests_by_endpoint = defaultdict(int)
        self.requests_by_status = defaultdict(int)
        
        self.llm_calls_total = 0
        self.llm_errors_total = 0
        self.rag_queries_total = 0
        self.tool_calls_total = defaultdict(int)
        self.hitl_approvals_total = defaultdict(int)
        self.cache_hits_total = 0
        self.cache_misses_total = 0

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float):
        with self._lock:
            self.total_requests += 1
            self.total_latency_ms += duration_ms
            
            # Normalize path for route grouping (e.g. /api/v1/chat/approvals/{thread_id}/decide)
            normalized_path = path
            if "/approvals/" in path and ("/decide" in path or "/status" in path):
                parts = path.split("/")
                # Replace dynamic thread_id with placeholder
                if len(parts) >= 6:
                    normalized_path = f"/{parts[1]}/{parts[2]}/{parts[3]}/{parts[4]}/:thread_id/{parts[6]}"
            elif "/tickets/" in path and len(path.split("/")) > 4:
                normalized_path = "/api/v1/tickets/:id"

            self.requests_by_endpoint[f"{method} {normalized_path}"] += 1
            self.requests_by_status[status_code] += 1

    def record_llm_call(self, model: str = "", success: bool = True):
        with self._lock:
            self.llm_calls_total += 1
            if not success:
                self.llm_errors_total += 1

    def record_rag_query(self):
        with self._lock:
            self.rag_queries_total += 1

    def record_tool_call(self, tool_name: str):
        with self._lock:
            self.tool_calls_total[tool_name] += 1

    def record_hitl_decision(self, approved: bool):
        with self._lock:
            key = "approved" if approved else "rejected"
            self.hitl_approvals_total[key] += 1

    def record_cache_hit(self):
        with self._lock:
            self.cache_hits_total += 1

    def record_cache_miss(self):
        with self._lock:
            self.cache_misses_total += 1

    def get_metrics_json(self) -> Dict[str, Any]:
        with self._lock:
            uptime_seconds = round(time.time() - self.start_time, 2)
            avg_latency = (
                round(self.total_latency_ms / self.total_requests, 2)
                if self.total_requests > 0
                else 0.0
            )

            total_cache_lookups = self.cache_hits_total + self.cache_misses_total
            cache_hit_rate = (
                round((self.cache_hits_total / total_cache_lookups) * 100, 2)
                if total_cache_lookups > 0
                else 0.0
            )

            return {
                "app_name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "uptime_seconds": uptime_seconds,
                "telemetry": {
                    "total_requests": self.total_requests,
                    "average_latency_ms": avg_latency,
                    "requests_by_status": dict(self.requests_by_status),
                    "requests_by_endpoint": dict(self.requests_by_endpoint),
                    "llm_calls_total": self.llm_calls_total,
                    "llm_errors_total": self.llm_errors_total,
                    "rag_queries_total": self.rag_queries_total,
                    "cache_hits_total": self.cache_hits_total,
                    "cache_misses_total": self.cache_misses_total,
                    "cache_hit_rate_pct": cache_hit_rate,
                    "tool_calls_total": dict(self.tool_calls_total),
                    "hitl_approvals_total": dict(self.hitl_approvals_total)
                }
            }

    def get_prometheus_metrics(self) -> str:
        with self._lock:
            uptime_seconds = round(time.time() - self.start_time, 2)
            avg_latency = (
                round(self.total_latency_ms / self.total_requests, 2)
                if self.total_requests > 0
                else 0.0
            )

            lines = [
                f"# HELP app_uptime_seconds Application uptime in seconds",
                f"# TYPE app_uptime_seconds gauge",
                f"app_uptime_seconds {uptime_seconds}",
                "",
                f"# HELP http_requests_total Total number of HTTP requests processed",
                f"# TYPE http_requests_total counter",
                f"http_requests_total {self.total_requests}",
                "",
                f"# HELP http_request_duration_ms_average Average request latency in milliseconds",
                f"# TYPE http_request_duration_ms_average gauge",
                f"http_request_duration_ms_average {avg_latency}",
                "",
                f"# HELP http_requests_by_status Total HTTP requests partitioned by status code",
                f"# TYPE http_requests_by_status counter"
            ]

            for code, count in self.requests_by_status.items():
                lines.append(f'http_requests_by_status{{code="{code}"}} {count}')

            lines.extend([
                "",
                f"# HELP agent_llm_calls_total Total invocations of LLM service",
                f"# TYPE agent_llm_calls_total counter",
                f"agent_llm_calls_total {self.llm_calls_total}",
                "",
                f"# HELP agent_rag_queries_total Total knowledge retrieval operations in Qdrant",
                f"# TYPE agent_rag_queries_total counter",
                f"agent_rag_queries_total {self.rag_queries_total}",
                "",
                f"# HELP agent_semantic_cache_hits_total Total semantic cache hits (saved LLM invocations)",
                f"# TYPE agent_semantic_cache_hits_total counter",
                f"agent_semantic_cache_hits_total {self.cache_hits_total}",
                "",
                f"# HELP agent_semantic_cache_misses_total Total semantic cache misses",
                f"# TYPE agent_semantic_cache_misses_total counter",
                f"agent_semantic_cache_misses_total {self.cache_misses_total}",
                ""
            ])

            if self.tool_calls_total:
                lines.append("# HELP agent_tool_executions_total Tool execution counts")
                lines.append("# TYPE agent_tool_executions_total counter")
                for tool, count in self.tool_calls_total.items():
                    lines.append(f'agent_tool_executions_total{{tool="{tool}"}} {count}')
                lines.append("")

            if self.hitl_approvals_total:
                lines.append("# HELP agent_hitl_decisions_total Human-in-the-Loop supervisor decisions")
                lines.append("# TYPE agent_hitl_decisions_total counter")
                for outcome, count in self.hitl_approvals_total.items():
                    lines.append(f'agent_hitl_decisions_total{{outcome="{outcome}"}} {count}')
                lines.append("")

            return "\n".join(lines)


# Singleton instance
metrics_service = MetricsService()
