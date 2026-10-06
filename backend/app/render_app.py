"""Single-instance hackathon host. Periodic rules run while the web service is awake."""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from .main import app as api
from .measurement import app as measurement
from .config import settings
from .db import SessionLocal
from .worker import tick


def run_tick():
    with SessionLocal() as db:
        tick(db)
        db.commit()


async def periodic_rules():
    while True:
        try:
            await asyncio.to_thread(run_tick)
        except Exception as error:
            logging.error("Periodic network checks failed (%s)", type(error).__name__)
        await asyncio.sleep(settings.worker_interval_seconds)


@asynccontextmanager
async def lifespan(app):
    async with api.router.lifespan_context(api):
        task = asyncio.create_task(periodic_rules())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/probe", measurement)
app.mount("/", api)
