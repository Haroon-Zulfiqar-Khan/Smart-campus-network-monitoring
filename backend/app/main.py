from contextlib import asynccontextmanager
from collections import defaultdict, deque
import logging
import time
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .config import settings
from .errors import DomainError
from .db import SessionLocal
from .views import auth, admin, locations, tests, complaints, incidents, operations, reports

logger = logging.getLogger("campus")
# A single process local guard. Production ingress must apply shared/distributed limits.
requests = defaultdict(deque)


@asynccontextmanager
async def lifespan(app):
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    yield


app = FastAPI(
    title="Smart Campus Wi-Fi Backend",
    version="1.0.0",
    lifespan=lifespan,
    description="Authenticated campus monitoring, bounded speed tests, explainable scoring and verified IT workflows. All stored timestamps are UTC.",
)


@app.middleware("http")
async def guards(request: Request, call_next):
    rid = str(uuid4())
    if request.url.path not in ("/health/live", "/health/ready"):
        key = (request.client.host if request.client else "unknown", request.url.path.split("/")[1])
        queue = requests[key]
        stamp = time.monotonic()
        while queue and queue[0] < stamp - 60:
            queue.popleft()
        limit = 20 if request.url.path.startswith("/auth") else 180
        if len(queue) >= limit:
            return JSONResponse(
                {"error": {"code": "rate_limited", "message": "Too many requests; retry shortly"}},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        queue.append(stamp)
        # Periodic eviction bounds memory from inactive client keys.
        if len(requests) > 10000:
            for stale in list(requests):
                if not requests[stale] or requests[stale][-1] < stamp - 60:
                    requests.pop(stale, None)
    length = request.headers.get("content-length")
    if length:
        try:
            if int(length) > 65536:
                raise ValueError()
        except ValueError:
            return JSONResponse(
                {
                    "error": {
                        "code": "payload_too_large",
                        "message": "API JSON payload limit is 64 KiB",
                    }
                },
                status_code=413,
            )
    if request.method in ("POST", "PATCH", "PUT"):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 65536:
                return JSONResponse(
                    {
                        "error": {
                            "code": "payload_too_large",
                            "message": "API JSON payload limit is 64 KiB",
                        }
                    },
                    status_code=413,
                )
        request._body = bytes(body)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID"],
)


@app.exception_handler(DomainError)
@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(
        {"error": {"code": str(exc.status_code), "message": exc.detail}},
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Do not echo passwords/tokens or submitted private descriptions in errors.
    details = [
        {"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]} for e in exc.errors()
    ]
    return JSONResponse(
        {"error": {"code": "validation_error", "message": "Invalid request", "details": details}},
        status_code=422,
    )


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse(
        {
            "error": {
                "code": "conflict",
                "message": "Record conflicts with existing data; retry with the same submission ID or correct the references",
            }
        },
        status_code=409,
    )


@app.exception_handler(SQLAlchemyError)
async def db_error(request, exc):
    logger.error("Database operation failed (%s)", type(exc).__name__)
    return JSONResponse(
        {
            "error": {
                "code": "database_unavailable",
                "message": "Cannot save or retrieve data; retry shortly",
            }
        },
        status_code=503,
    )


@app.get("/health/live", tags=["Health"])
def live():
    return {"status": "ok", "service": "campus-api"}


@app.get("/health/ready", tags=["Health"])
def ready():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        db.execute(text("SELECT id FROM campuses LIMIT 1"))
    return {"status": "ready"}


for router in (
    auth.router,
    admin.router,
    locations.router,
    tests.router,
    complaints.router,
    incidents.router,
    operations.router,
    reports.router,
):
    app.include_router(router)
from .views.workspace import router as workspace_router
app.include_router(workspace_router)
from .views.ai import router as ai_router
app.include_router(ai_router)
