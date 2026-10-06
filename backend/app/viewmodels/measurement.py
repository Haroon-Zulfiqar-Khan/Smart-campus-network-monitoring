"""ViewModel: bounded transfer commands independent of ASGI request/response types."""

import asyncio
import os
import time
from ..models.measurement import reserve, confirm_upload, authorize
from ..config import settings
from ..errors import DomainError


class MeasurementViewModel:
    def __init__(self):
        self.slots = asyncio.Semaphore(settings.max_concurrent_transfers)

    def authorize(self, token, db):
        return authorize(token, db)

    async def acquire(self):
        if self.slots.locked():
            raise DomainError(429, "Measurement service is busy; retry shortly")
        await self.slots.acquire()

    async def download(self, id, size):
        await self.acquire()
        try:
            reserve(id, size)
        except Exception:
            self.slots.release()
            raise
        chunk = os.urandom(min(65536, size))

        async def stream():
            remaining = size
            try:
                while remaining:
                    payload = chunk[: min(len(chunk), remaining)]
                    remaining -= len(payload)
                    yield payload
                    await asyncio.sleep(0)
            finally:
                self.slots.release()

        return {"stream": stream(), "bytes": size}

    async def upload(self, id, length, has_length, chunks):
        if length == 0 and has_length:
            raise DomainError(422, "Upload body is empty")
        if length < 0 or length > settings.max_upload_bytes:
            raise DomainError(413, "Upload exceeds configured byte limit")
        await self.acquire()
        received = 0
        started = time.perf_counter()
        try:
            reserve(id, length or settings.max_upload_bytes)
            async with asyncio.timeout(30):
                async for chunk in chunks:
                    received += len(chunk)
                    if received > settings.max_upload_bytes or length and received > length:
                        raise DomainError(413, "Upload exceeds byte limit")
            if received == 0:
                raise DomainError(422, "Upload body is empty")
            if length and length != received:
                raise DomainError(400, "Upload body length mismatch")
            confirm_upload(id, received)
            return {
                "received_bytes": received,
                "server_receive_seconds": round(time.perf_counter() - started, 6),
            }
        except TimeoutError:
            raise DomainError(408, "Upload exceeded 30 second deadline")
        finally:
            self.slots.release()
