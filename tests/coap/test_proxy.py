"""
Module 1 Assignment - Task 2.3
CoAP-HTTP Proxy Integration Test

Do not modify this file.

This test starts the CoAP server and a lightweight HTTP-to-CoAP proxy,
then verifies that HTTP GET requests return the same JSON as direct CoAP
GET requests.  It also checks that HTTP response headers map correctly
to the underlying CoAP options (Content-Format -> Content-Type, etc.).

Requirements:
    pip install aiocoap aiohttp pytest-asyncio
"""

import asyncio
import json
import socket
import pytest
import pytest_asyncio
import aiohttp
from aiohttp import web

import aiocoap
from aiocoap import Message, Code

from src.coap.server import build_server

COAP_BASE = "coap://localhost"
HTTP_PROXY_HOST = "localhost"

CONTENT_FORMAT_MAP = {
    0:  "text/plain",
    50: "application/json",
    60: "application/cbor",
}

pytestmark = pytest.mark.asyncio


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def _coap_to_http_handler(request: web.Request) -> web.Response:
    """Translate an HTTP GET into a CoAP GET and return the result."""
    path = request.path
    coap_uri = f"{COAP_BASE}{path}"

    ctx = await aiocoap.Context.create_client_context()
    try:
        coap_req = Message(code=Code.GET, uri=coap_uri)
        coap_resp = await ctx.request(coap_req).response

        content_format = coap_resp.opt.content_format
        content_type = CONTENT_FORMAT_MAP.get(content_format, "application/octet-stream")

        headers = {"Content-Type": content_type}

        if coap_resp.opt.etag is not None:
            headers["ETag"] = coap_resp.opt.etag.hex()

        max_age = coap_resp.opt.max_age
        if max_age is not None:
            headers["Cache-Control"] = f"max-age={max_age}"

        return web.Response(
            body=coap_resp.payload,
            status=200,
            headers=headers,
        )
    finally:
        await ctx.shutdown()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def proxy_port():
    return _find_free_port()


@pytest_asyncio.fixture(scope="module")
async def coap_server():
    """Start the CoAP resource server."""
    ctx = await build_server()
    yield ctx
    await ctx.shutdown()


@pytest_asyncio.fixture(scope="module")
async def http_proxy(coap_server, proxy_port):
    """Start the HTTP-to-CoAP proxy on a free port."""
    app = web.Application()
    app.router.add_get("/{path:.*}", _coap_to_http_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HTTP_PROXY_HOST, proxy_port)
    await site.start()
    yield site
    await runner.cleanup()


class TestCoAPHTTPProxy:
    """Verify that HTTP requests through the proxy return correct CoAP data."""

    async def test_http_get_temperature_returns_json(self, coap_server, http_proxy, proxy_port):
        """HTTP GET /factory/line1/temperature must return valid JSON with
        the same structure as a direct CoAP GET."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{HTTP_PROXY_HOST}:{proxy_port}/factory/line1/temperature"
            ) as resp:
                assert resp.status == 200
                body = await resp.json()
                assert "value" in body, "Response must contain 'value' key"
                assert "unit" in body, "Response must contain 'unit' key"
                assert body["unit"] == "C"

    async def test_http_content_type_maps_from_coap(self, coap_server, http_proxy, proxy_port):
        """HTTP Content-Type header must map from CoAP Content-Format 50."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{HTTP_PROXY_HOST}:{proxy_port}/factory/line1/temperature"
            ) as resp:
                ct = resp.headers.get("Content-Type", "")
                assert "application/json" in ct, (
                    f"Content-Type should be application/json (from CoAP "
                    f"Content-Format 50), got: {ct}"
                )

    async def test_http_matches_direct_coap(self, coap_server, http_proxy, proxy_port):
        """HTTP response payload structure must match a direct CoAP GET."""
        coap_req = Message(
            code=Code.GET,
            uri=f"{COAP_BASE}/factory/line1/temperature",
        )
        ctx = await aiocoap.Context.create_client_context()
        try:
            coap_resp = await ctx.request(coap_req).response
            coap_data = json.loads(coap_resp.payload)
        finally:
            await ctx.shutdown()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{HTTP_PROXY_HOST}:{proxy_port}/factory/line1/temperature"
            ) as resp:
                http_data = await resp.json()

        assert set(coap_data.keys()) == set(http_data.keys()), (
            "HTTP and CoAP responses must have the same JSON keys"
        )
        assert coap_data["unit"] == http_data["unit"]

    async def test_http_get_manifest_block2(self, coap_server, http_proxy, proxy_port):
        """HTTP GET /factory/manifest must return the full reassembled
        Block2 payload (>= 3 KB)."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{HTTP_PROXY_HOST}:{proxy_port}/factory/manifest"
            ) as resp:
                assert resp.status == 200
                body = await resp.read()
                assert len(body) >= 3072, (
                    f"Manifest must be >= 3072 bytes, got {len(body)}"
                )
                data = json.loads(body)
                assert "entries" in data or "devices" in data
