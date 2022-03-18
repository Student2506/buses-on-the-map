import json
import logging
from contextlib import suppress
from functools import partial

import trio
from trio_websocket import ConnectionClosed, serve_websocket

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
RECEIVE_TIMEOUT = 1
SEND_TIMEOUT = 1


buses = {}
bounds = {}


async def get_buses(request):
    global buses
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            message = json.loads(message)
            buses.update({bus.get('busId'): {
                'busId': bus.get('busId'),
                'lat': bus.get('lat'),
                'lng': bus.get('lng'),
                'route': bus.get('route')
            } for bus in message})
        except ConnectionClosed:
            break
        await trio.sleep(RECEIVE_TIMEOUT)


async def talk_to_browser(nursery, request):

    ws = await request.accept()
    while True:
        try:
            await listen_browser(ws)
        except ConnectionClosed:
            break
        await trio.sleep(SEND_TIMEOUT)


def is_inside(bounds, lat, lng):
    return (bounds['south_lat'] <= lat <= bounds['north_lat'] and
            bounds['west_lng'] <= lng <= bounds['east_lng'])


async def send_buses(ws, bounds):
    global buses
    buses_bounded = [{
        'busId': bus.get('busId'),
        'lat': bus.get('lat'),
        'lng': bus.get('lng'),
        'route': bus.get('route')
    } for bus in buses.values() if is_inside(
        bounds, bus.get('lat'), bus.get('lng')
    )]
    message = {
        'msgType': 'Buses',
        'buses': buses_bounded
    }
    message = json.dumps(message)
    await ws.send_message(message)


async def listen_browser(ws):
    logger.debug(f'And our ws is: {ws}')
    # while True:
    message = {}
    global bounds
    with trio.move_on_after(SEND_TIMEOUT):
        message = await ws.get_message()
        message = json.loads(message)
    if message.get('msgType') == 'newBounds':
        bounds = message.get('data')
        logger.debug(bounds)
    await send_buses(ws, bounds)
    await trio.sleep(0)


async def main():
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    trio_websocket_logger = logging.getLogger(name='trio-websocket')
    trio_websocket_logger.setLevel(logging.WARNING)
    bus_receive_socket = partial(
        serve_websocket, get_buses, '127.0.0.1', 8080, ssl_context=None
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
            8000,
            ssl_context=None
        )
        nursery.start_soon(bus_receive_socket)
        nursery.start_soon(browser_socket)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
