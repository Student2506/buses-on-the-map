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

            # logger.debug(buses)
        except ConnectionClosed:
            break
        await trio.sleep(RECEIVE_TIMEOUT)


async def talk_to_browser(nursery, request):
    global buses
    ws = await request.accept()
    # async with trio.open_nursery() as nursery:
    nursery.start_soon(listen_browser, ws)
    while True:
        try:
            # await listen_browser(ws)
            message = {
                'msgType': 'Buses',
                'buses': [bus for bus in buses.values()]
            }
            message = json.dumps(message)
            await ws.send_message(message)
        except ConnectionClosed:
            break
        await trio.sleep(SEND_TIMEOUT)


def is_inside(bounds, lat, lng):
    return (bounds['south_lat'] <= lat <= bounds['north_lat'] and
            bounds['west_lng'] <= lng <= bounds['east_lng'])


async def listen_browser(ws):
    global buses
    logger.debug(f'And our ws is: {ws}')
    while True:
        try:
            message = await ws.get_message()
            message = json.loads(message)
            if message.get('msgType') == 'newBounds':
                bounds = message.get('data')
                logger.debug(bounds)
                bus_inside = [
                    bus['busId'] for bus in buses.values()
                    if is_inside(bounds, bus.get('lat'), bus.get('lng'))
                ]

                logger.debug(f'{len(bus_inside)} buses inside bounds')
        except ConnectionClosed:
            break
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
