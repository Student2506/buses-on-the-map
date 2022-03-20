"""Completely broken"""
import os
import sys
from functools import partial

import pytest
import trio
from trio.testing import open_stream_to_socket_listener
from trio_websocket import serve_websocket

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from server import talk_to_browser


@pytest.fixture
async def echo_client(nursery, request):
    browser_func = partial(
        talk_to_browser,
        nursery
    )
    listener = await nursery.start(
        partial(serve_websocket, browser_func, host='127.0.0.1', port=0, ssl_context=None)
    )
    echo_client = await open_stream_to_socket_listener(listener)
    async with echo_client:
        yield echo_client


async def test_browser_communication(echo_client):
    for test_byte in [b'a', b'b', b'c']:
        await echo_client.send_all(test_byte)
        assert await echo_client.receive_some(1) == test_byte
