from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core.config import settings


def _sanitize_banner(value: bytes) -> str | None:
    text = value.decode("utf-8", errors="ignore")
    clean = "".join(char for char in text if char.isprintable()).strip()
    return clean or None


async def scan_ports(
    host: str,
    ports: list[int],
    *,
    display_host: str | None = None,
    concurrency: int | None = None,
    timeout: float | None = None,
    banner_max_bytes: int | None = None,
) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency or settings.scan_concurrency)
    connection_timeout = timeout or settings.scan_default_timeout_seconds
    banner_limit = banner_max_bytes or settings.scan_banner_max_bytes
    started = time.perf_counter()

    async def scan_one(port: int) -> dict[str, Any]:
        async with semaphore:
            writer = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=connection_timeout
                )
                try:
                    banner = await asyncio.wait_for(
                        reader.read(banner_limit), timeout=connection_timeout
                    )
                except asyncio.TimeoutError:
                    banner = b""
                return {
                    "port": port,
                    "open": True,
                    "banner": _sanitize_banner(banner),
                }
            except (asyncio.TimeoutError, ConnectionError, OSError):
                return {"port": port, "open": False, "banner": None}
            finally:
                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except OSError:
                        pass

    results = await asyncio.gather(*(scan_one(port) for port in ports))
    return {
        "host": display_host or host,
        "ports": results,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }
