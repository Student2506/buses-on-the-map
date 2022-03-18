import json
import logging
from contextlib import suppress
from functools import partial

import trio
from trio_websocket import ConnectionClosed, serve_websocket

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
RECEIVE_TIMEOUT = 0.1
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

            logger.debug(message)
        except ConnectionClosed:
            break
        await trio.sleep(RECEIVE_TIMEOUT)


async def talk_to_browser(request):
    global buses
    ws = await request.accept()
    while True:
        try:
            message = {
                'msgType': 'Buses',
                'buses': [bus for bus in buses.values()]
            }
            message = json.dumps(message)
            await ws.send_message(message)
        except ConnectionClosed:
            break
        await trio.sleep(SEND_TIMEOUT)


async def main():
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    get_buses_func = partial(
        serve_websocket, get_buses, '127.0.0.1', 8080, ssl_context=None
    )
    talk_to_browser_func = partial(
        serve_websocket, talk_to_browser, '127.0.0.1', 8000, ssl_context=None
    )
    async with trio.open_nursery() as nursery:
        nursery.start_soon(get_buses_func)
        nursery.start_soon(talk_to_browser_func)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
