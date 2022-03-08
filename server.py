import json
import logging
from functools import partial

import trio
from trio_websocket import ConnectionClosed, serve_websocket

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)

buses = {}


async def talk_to_browser(request):
    global buses
    ws = await request.accept()
    while True:
        try:
            buses_list = [
                {
                    'busId': bus,
                    'lat': bus[1]['lat'],
                    'lng': bus[1]['lng'],
                    'route': bus[1]['route']
                } for bus in buses.items()
            ]
            TEMPLATE = {
                'msgType': 'Buses',
                'buses': buses_list
            }
            message = json.dumps(TEMPLATE)
            await ws.send_message(message)
        except ConnectionClosed:
            break
        await trio.sleep(1)


async def receive_coords_data(request):
    global buses
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            bus = json.loads(message)
            buses[str(bus.get('busId'))] = {
                'lat': bus.get('lat'),
                'lng': bus.get('lng'),
                'route': bus.get('route'),
            }

            logger.debug(json.dumps(bus, ensure_ascii=False))
        except ConnectionClosed:
            break
        await trio.sleep(1)


async def main():
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    receive_func = partial(
        serve_websocket,
        receive_coords_data,
        '127.0.0.1',
        8080,
        ssl_context=None
    )
    sender_func = partial(
        serve_websocket,
        talk_to_browser,
        '127.0.0.1',
        8000,
        ssl_context=None
    )

    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            receive_func
        )
        nursery.start_soon(
            sender_func
        )


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
