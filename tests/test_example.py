"""Completely broken"""
import os
import sys
from functools import partial

import pytest
import trio
from trio.testing import open_stream_to_socket_listener


try:
    from trio.lowlevel import current_task  # pylint: disable=ungrouped-imports
except ImportError:
    from trio.hazmat import current_task  # pylint: disable=ungrouped-imports

from trio_websocket import (
    connect_websocket,
    connect_websocket_url,
    ConnectionClosed,
    ConnectionRejected,
    ConnectionTimeout,
    DisconnectionTimeout,
    Endpoint,
    HandshakeError,
    open_websocket,
    open_websocket_url,
    serve_websocket,
    WebSocketServer,
    wrap_client_stream,
    wrap_server_stream
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from server import talk_to_browser

HOST = '127.0.0.1'
RESOURCE = '/'


@pytest.fixture
async def echo_server(nursery):
    ''' A server that reads one message, sends back the same message,
    then closes the connection. '''
    serve_fn = partial(
        serve_websocket, talk_to_browser, HOST, 0,
        ssl_context=None)
    server = await nursery.start(serve_fn)
    yield server


@pytest.fixture
async def echo_conn(echo_server):
    ''' Return a client connection instance that is connected to an echo
    server. '''
    async with open_websocket(
        HOST, echo_server.port, RESOURCE,
            use_ssl=False) as conn:
        yield conn


async def test_serve_handler_nursery(nursery):
    task = current_task()
    async with trio.open_nursery() as handler_nursery:
        browser_func = partial(
            talk_to_browser,
            nursery
        )
        serve_with_nursery = partial(
            serve_websocket, browser_func,
            HOST, 0, None, handler_nursery=handler_nursery)
        server = await nursery.start(serve_with_nursery)
        port = server.port
        # The server nursery begins with one task (server.listen).
        assert len(nursery.child_tasks) == 1
        no_clients_nursery_count = len(task.child_nurseries)
        async with open_websocket(HOST, port, RESOURCE, use_ssl=False) as conn:
            # The handler nursery should have one task in it
            # (conn._reader_task).
            assert len(handler_nursery.child_tasks) == 1
