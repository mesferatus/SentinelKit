import asyncio

import pytest


@pytest.mark.asyncio
async def test_scanner_finds_open_port_and_sanitizes_banner():
    from app.services.port_scanner import scan_ports

    async def banner_server(reader, writer):
        writer.write(b"Sentinel\x00Kit\xff\r\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(banner_server, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        result = await scan_ports(
            "127.0.0.1",
            [port],
            concurrency=2,
            timeout=0.5,
            banner_max_bytes=64,
        )
    finally:
        server.close()
        await server.wait_closed()

    assert result["host"] == "127.0.0.1"
    assert result["ports"] == [
        {"port": port, "open": True, "banner": "SentinelKit"}
    ]
    assert result["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_scanner_reports_closed_port_without_banner():
    from app.services.port_scanner import scan_ports

    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()

    result = await scan_ports("127.0.0.1", [port], timeout=0.1)

    assert result["ports"] == [{"port": port, "open": False, "banner": None}]


@pytest.mark.asyncio
async def test_scanner_connects_to_pinned_ip_but_reports_original_host(monkeypatch):
    from app.services import port_scanner

    connected = []

    async def fake_open_connection(host, port):
        connected.append((host, port))
        raise ConnectionRefusedError

    monkeypatch.setattr(asyncio, "open_connection", fake_open_connection)

    result = await port_scanner.scan_ports(
        "93.184.216.34", [443], display_host="safe.example", timeout=0.1
    )

    assert connected == [("93.184.216.34", 443)]
    assert result["host"] == "safe.example"
