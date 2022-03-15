import json
import logging
from contextlib import suppress
from functools import partial

import trio
from trio_websocket import ConnectionClosed, serve_websocket

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)


async def collect_all_data(sending_channel, receiving_channel):
    buses = {}
    message = ''
    while True:
        with trio.move_on_after(1):
            async for message in receiving_channel:
                logger.debug(receiving_channel.statistics())
                buses.update(message)
                current_position = {
                        'msgType': 'Buses',
                        'buses': [
                            {
                                'busId': bus_id,
                                'lat': bus_params['lat'],
                                'lng': bus_params['lng'],
                                'route': bus_params['route']
                            } for bus_id, bus_params in buses.items()
                        ]
                    }
                message = json.dumps(current_position)
                logger.debug(f'Buses total: {len(message)}')
        await sending_channel.send(message)
        await trio.sleep(0)


async def listen_browser(ws):
    while True:
        try:
            message = await ws.get_message()
        except ConnectionClosed:
            logger.debug('Connection from browser left')
            return
        logger.info(message)
        await trio.sleep(0)


async def talk_to_browser(receiving_channel, nursery, request):
    # global buses
    ws = await request.accept()
    nursery.start_soon(listen_browser, ws)

    # buses = {}
    while True:
        try:
            async for message in receiving_channel:
                await ws.send_message(message)
        except ConnectionClosed:
            pass
        await trio.sleep(0)


async def receive_coords_data(sending_channel, request):
    # global buses
    sending_channel = sending_channel.clone()
    buses = {}
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()

            bus = json.loads(message)
            buses[bus.get('busId')] = {
                'lat': bus.get('lat'),
                'lng': bus.get('lng'),
                'route': str(bus.get('route'))
            }
            await sending_channel.send(buses)
            # logger.debug(buses)
            logger.debug(f'Coords qty: {len(buses)}')
        except ConnectionClosed:
            break
        await trio.sleep(0)


async def main():
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    (
        send_to_processing,
        recieve_for_processing
    ) = trio.open_memory_channel(0)
    (
        send_for_render,
        recieve_for_render
    ) = trio.open_memory_channel(0)
    receive_func = partial(
        receive_coords_data, send_to_processing
    )
    serve_recieve = partial(
        serve_websocket,
        receive_func,
        '127.0.0.1',
        8080,
        ssl_context=None
    )

    async with trio.open_nursery() as nursery:
        sender_func = partial(
            talk_to_browser, recieve_for_render, nursery
        )
        serve_sending = partial(
            serve_websocket,
            sender_func,
            '127.0.0.1',
            8000,
            ssl_context=None
        )

        nursery.start_soon(
            serve_recieve
        )
        nursery.start_soon(
            serve_sending
        )
        nursery.start_soon(
            collect_all_data, send_for_render, recieve_for_processing
        )


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
