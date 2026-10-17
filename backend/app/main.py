import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes.analyses import router as analyses_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.commitments import router as commitments_router
from backend.app.api.routes.health import router as health_router
from backend.app.core.config import PROJECT_ROOT, get_settings
from backend.app.core.errors import (
    error_response,
    register_error_handlers,
)
from backend.app.db.database import initialize_database

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("commitai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.6.0",
    description="API para detectar y gestionar compromisos.",
    lifespan=lifespan,
)

register_error_handlers(app)
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(commitments_router, prefix="/api")
app.include_router(analyses_router, prefix="/api")

FRONTEND_DIR = PROJECT_ROOT / "frontend"

app.mount(
    "/assets",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="assets",
)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/login", include_in_schema=False)
def login():
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/register", include_in_schema=False)
def register():
    return FileResponse(FRONTEND_DIR / "register.html")

@app.middleware("http")
async def request_logging(request: Request, call_next):
    request.state.request_id = str(uuid4())
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(
            "request_id=%s exception_type=%s",
            request.state.request_id,
            type(exc).__name__,
        )
        response = error_response(
            request,
            500,
            "internal_error",
            "Ocurrió un error interno.",
        )

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request.state.request_id

    route = request.scope.get("route")
    route_name = getattr(route, "path", "unmatched")

    logger.info(
        "request_id=%s method=%s route=%s status=%s duration_ms=%.1f",
        request.state.request_id,
        request.method,
        route_name,
        response.status_code,
        elapsed_ms,
    )

    return response