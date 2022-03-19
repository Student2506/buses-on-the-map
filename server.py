import json
import logging
from contextlib import suppress
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from functools import partial

import asyncclick as click
import trio
from trio_websocket import ConnectionClosed, serve_websocket

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
RECEIVE_TIMEOUT = 1
SEND_TIMEOUT = 1
buses_var = ContextVar('buses', default={})


@dataclass
class Bus:
    """Keeps information about buses on map"""
    busId: str
    lat: float
    lng: float
    route: str


@dataclass
class WindowBounds:
    """Keeps info about current browser windows"""
    south_lat: float
    north_lat: float
    west_lng: float
    east_lng: float

    def is_inside(self, lat, lng):
        return (self.south_lat <= lat <= self.north_lat and
                self.west_lng <= lng <= self.east_lng)

    def update(self, south_lat, north_lat, west_lng, east_lng):
        self.south_lat = south_lat
        self.north_lat = north_lat
        self.west_lng = west_lng
        self.east_lng = east_lng


async def get_buses(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            message = json.loads(message)
            buses = buses_var.get()
            buses.update(
                {bus.get('busId'): asdict(Bus(**bus)) for bus in message}
            )
            buses_var.set(buses)
        except ConnectionClosed:
            break
        await trio.sleep(RECEIVE_TIMEOUT)


async def talk_to_browser(nursery, request):
    ws = await request.accept()
    message = await ws.get_message()
    message = json.loads(message)
    if message.get('msgType') == 'newBounds':
        bounds = WindowBounds(**message.get('data'))
    else:
        return

    async def listen_browser(ws, bounds):
        logger.debug(f'And our ws is: {ws}')
        message = {}
        with trio.move_on_after(SEND_TIMEOUT):
            message = await ws.get_message()
            message = json.loads(message)
        if message.get('msgType') == 'newBounds':
            bounds.update(**message.get('data'))
            logger.debug(bounds)
        await send_buses(ws, bounds)
        await trio.sleep(0)

    while True:
        try:
            await listen_browser(ws, bounds)
        except ConnectionClosed:
            break
        await trio.sleep(SEND_TIMEOUT)


async def send_buses(ws, bounds):
    buses = buses_var.get()
    buses_bounded = [
        asdict(Bus(**bus)) for bus in buses.values() if bounds.is_inside(
            bus.get('lat'), bus.get('lng')
        )
    ]
    message = {
        'msgType': 'Buses',
        'buses': buses_bounded
    }
    message = json.dumps(message)
    await ws.send_message(message)


@click.command()
@click.option('--bus_port', default=8080)
@click.option('--browser_port', default=8000)
@click.option('-v', '--verbose', count=True)
async def main(bus_port, browser_port, verbose):
    logging_level = {
        '0': logging.ERROR,
        '1': logging.WARNING,
        '2': logging.INFO,
        '3': logging.DEBUG
    }
    logging.basicConfig(level=logging_level.get(str(verbose)), format=FORMAT)
    trio_websocket_logger = logging.getLogger(name='trio-websocket')
    trio_websocket_logger.setLevel(logging_level.get(str(verbose)))
    bus_receive_socket = partial(
        serve_websocket, get_buses, '127.0.0.1', bus_port, ssl_context=None
    )
    async with trio.open_nursery() as nursery:
        browser_func = partial(
            talk_to_browser,
            nursery
        )
        browser_socket = partial(
            serve_websocket,
            browser_func,
            '127.0.0.1',
            browser_port,
            ssl_context=None
        )
        nursery.start_soon(bus_receive_socket)
        nursery.start_soon(browser_socket)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        main(_anyio_backend="trio")
