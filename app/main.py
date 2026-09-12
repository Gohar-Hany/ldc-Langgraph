import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings, validate_production_secrets
from app.core.logging import logger
from app.api.v1.router import api_router
from app.api.middlewares.auth_middleware import RequestLoggingMiddleware
from app.api.middlewares.rate_limiter import RateLimiterMiddleware
from app.services.metrics_service import metrics_service
from app.api.middlewares.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce production security invariants before accepting any traffic
    validate_production_secrets()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    yield
    # Gracefully close the PostgreSQL connection pool on shutdown (Fix H-03)
    try:
        from app.agent.graph import checkpointer
        from langgraph.checkpoint.postgres import PostgresSaver
        if isinstance(checkpointer, PostgresSaver) and hasattr(checkpointer, "_pool"):
            checkpointer._pool.close()
            logger.info("[Lifespan] PostgreSQL connection pool closed.")
    except Exception as e:
        logger.warning(f"[Lifespan] Could not close checkpointer pool: {e}")
    logger.info(f"Shutting down {settings.APP_NAME}")


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Role-Based Enterprise AI Support Agent using LangGraph & FastAPI",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan
    )

    # 1. CORS Configuration — Whitelist only; never allow_origins=["*"] with credentials
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Bypass-Cache", "X-Bypass-Rate-Limit"],
    )

    # 2. Custom Middlewares
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RateLimiterMiddleware)

    # 3. Exception Handlers
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, global_exception_handler)

    # 4. Include Routers
    application.include_router(api_router, prefix=settings.API_V1_STR)

    @application.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
    async def health_check():
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT
        }

    @application.get("/health/live", tags=["Health"], status_code=status.HTTP_200_OK)
    async def liveness_probe():
        """Lightweight Kubernetes liveness probe."""
        return {"status": "alive", "timestamp": time.time()}

    @application.get("/health/ready", tags=["Health"], status_code=status.HTTP_200_OK)
    async def readiness_probe():
        """
        Comprehensive readiness probe verifying external cloud dependencies:
        Supabase PostgreSQL, Qdrant Cloud Vector DB, LLM Service, and Tavily Search.
        """
        dependencies = {}

        # 1. Supabase Database check
        try:
            from app.services.database_service import database_service
            db_ok = database_service.client is not None
            dependencies["supabase_postgresql"] = {"status": "ready" if db_ok else "unconfigured"}
        except Exception as e:
            dependencies["supabase_postgresql"] = {"status": "degraded", "error": str(e)}

        # 2. Qdrant Cloud Vector DB check
        try:
            from app.services.qdrant_cloud_service import qdrant_service
            qdrant_ok = qdrant_service.client is not None
            dependencies["qdrant_vector_db"] = {"status": "ready" if qdrant_ok else "unconfigured"}
        except Exception as e:
            dependencies["qdrant_vector_db"] = {"status": "degraded", "error": str(e)}

        # 3. LLM Service check
        try:
            from app.services.llm_service import llm_service
            llm_ok = llm_service.client is not None
            dependencies["llm_orchestrator"] = {"status": "ready" if llm_ok else "unconfigured", "provider": settings.LLM_PROVIDER}
        except Exception as e:
            dependencies["llm_orchestrator"] = {"status": "degraded", "error": str(e)}

        # 4. Tavily External Search check
        try:
            from app.services.external_search_service import external_search_service
            tavily_ok = external_search_service.client is not None
            dependencies["tavily_external_search"] = {
                "status": "ready" if tavily_ok else "fallback_mode",
                "mode": "live" if tavily_ok else "resilient_fallback"
            }
        except Exception as e:
            dependencies["tavily_external_search"] = {"status": "degraded", "error": str(e)}

        # 5. LangGraph State Checkpointer check (Fix M-06)
        try:
            from app.agent.graph import checkpointer
            cp_ok = checkpointer is not None
            pool_healthy = True
            if hasattr(checkpointer, "_pool") and checkpointer._pool is not None:
                pool_healthy = not getattr(checkpointer._pool, "closed", False)
            dependencies["langgraph_checkpointer"] = {
                "status": "ready" if (cp_ok and pool_healthy) else "degraded",
                "type": type(checkpointer).__name__ if checkpointer else "none"
            }
        except Exception as e:
            dependencies["langgraph_checkpointer"] = {"status": "degraded", "error": str(e)}

        all_ready = all(d.get("status") in ["ready", "fallback_mode"] for d in dependencies.values())

        return {
            "status": "ready" if all_ready else "partially_degraded",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "dependencies": dependencies
        }

    @application.get("/metrics", tags=["Observability"])
    async def get_metrics(format: str = "json"):
        """
        Telemetry and metrics endpoint.
        Pass ?format=prometheus for Prometheus text exposition format.
        """
        from fastapi.responses import PlainTextResponse, JSONResponse
        if format.lower() == "prometheus":
            return PlainTextResponse(metrics_service.get_prometheus_metrics())
        return JSONResponse(metrics_service.get_metrics_json())

    @application.get("/", tags=["Root"])
    async def root():
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics"
        }

    return application


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
