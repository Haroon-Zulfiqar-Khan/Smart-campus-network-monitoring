"""Separate ASGI transport host for measurement Views (port 8001)."""

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from .config import settings
from .db import get_db
from .security import bearer
from .viewmodels.measurement import MeasurementViewModel
from .errors import DomainError

app = FastAPI(title="Campus bounded measurement service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Received-Bytes", "Content-Length"],
)
viewmodel = MeasurementViewModel()
HEADERS = {
    "Cache-Control": "no-store, no-cache, max-age=0",
    "Content-Encoding": "identity",
    "Timing-Allow-Origin": ", ".join(settings.cors_origins),
    "X-Content-Type-Options": "nosniff",
}


@app.exception_handler(DomainError)
@app.exception_handler(HTTPException)
async def error(request, exc):
    return JSONResponse(
        {"error": {"code": str(exc.status_code), "message": exc.detail}},
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse(
        {"error": {"code": "database_unavailable", "message": "Measurement state is unavailable"}},
        status_code=503,
    )


def session(auth=Depends(bearer), db=Depends(get_db)):
    if not auth:
        raise HTTPException(401, "Measurement token required")
    return viewmodel.authorize(auth.credentials, db)


@app.get("/health/live")
def live():
    return {"status": "ok", "service": "measurement"}


@app.get("/measure/ping")
def ping(id=Depends(session)):
    return Response(b"pong", media_type="application/octet-stream", headers=HEADERS)


@app.get("/measure/download")
async def download(
    bytes: int = Query(1024 * 1024, ge=1024, le=settings.max_download_bytes), id=Depends(session)
):
    data = await viewmodel.download(id, bytes)
    return StreamingResponse(
        data["stream"],
        media_type="application/octet-stream",
        headers={**HEADERS, "Content-Length": str(data["bytes"])},
    )


@app.post("/measure/upload")
async def upload(request: Request, id=Depends(session)):
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        raise HTTPException(400, "Invalid Content-Length")
    data = await viewmodel.upload(id, length, "content-length" in request.headers, request.stream())
    return JSONResponse(data, headers={**HEADERS, "X-Received-Bytes": str(data["received_bytes"])})
