import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mlft")

from app.database import engine  # noqa: E402  (after logging is configured)
from app.api.routes.auth import router as auth_router  # noqa: E402
from app.api.routes.results import router as results_router  # noqa: E402
from app.api.routes.search import router as search_router  # noqa: E402
from app.api.routes.sources import router as sources_router  # noqa: E402


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(
        "%s %s starting (env=%s, storage=%s)",
        settings.app_name,
        settings.version,
        settings.environment,
        settings.storage_dir,
    )
    if settings.is_production and not settings.secure_cookies:
        logger.warning("COOKIE_SECURE is off in production; sessions will travel over plain HTTP.")
    yield
    engine.dispose()


app = FastAPI(
    title=f"{settings.app_name} API",
    description="Image- and text-guided object search across CCTV and video footage.",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unexpected errors and return a generic message (no internals leaked)."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )


@app.get("/", include_in_schema=False)
def root():
    return {"name": settings.app_name, "version": settings.version, "status": "running"}


@app.get("/health", tags=["Health"])
def health_check():
    """Liveness: the process is up."""
    return {"status": "healthy", "service": "mlft-backend"}


@app.get("/health/ready", tags=["Health"])
def readiness_check():
    """Readiness: the database is reachable."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed: database unavailable")
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unreachable"},
        )
    return {"status": "ready", "database": "ok"}


app.include_router(auth_router)
app.include_router(search_router)
app.include_router(results_router)
app.include_router(sources_router)
