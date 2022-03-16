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
        # with trio.move_on_after(.01):
        async for message in receiving_channel:
            logger.debug(receiving_channel.statistics())
            buses.update(message)
            try:
                sending_channel.send_nowait(buses)
            except trio.WouldBlock:
                pass
        await trio.sleep(0)


async def listen_browser(ws, coords_sending):
    while True:
        try:
            message = await ws.get_message()
        except ConnectionClosed:
            logger.debug('Connection from browser left')
            return
        message = json.loads(message)
        if message.get('msgType', None) == 'newBounds':
            await coords_sending.send(message.get('data'))
        await trio.sleep(0)


def is_inside(bounds, lat, lng):
    return (bounds['south_lat'] <= lat <= bounds['north_lat'] and
            bounds['west_lng'] <= lng <= bounds['east_lng'])


async def send_buses(ws, bounds):
    pass


async def talk_to_browser(receiving_channel, nursery, request):
    ws = await request.accept()
    coords_sending, coords_receiving = trio.open_memory_channel(0)
    nursery.start_soon(listen_browser, ws, coords_sending)
    new_coords = await coords_receiving.receive()
    while True:
        try:
            async for message in receiving_channel:
                try:
                    new_coords = coords_receiving.receive_nowait()
                except trio.WouldBlock:
                    pass
                else:
                    logger.info(new_coords)
                current_position = {
                        'msgType': 'Buses',
                        'buses': [
                            {
                                'busId': bus_id,
                                'lat': bus_params['lat'],
                                'lng': bus_params['lng'],
                                'route': bus_params['route']
                            } for bus_id, bus_params in message.items()
                            if is_inside(
                                new_coords,
                                bus_params['lat'],
                                bus_params['lng']
                            )
                        ]
                    }
                message = json.dumps(current_position)

                await ws.send_message(message)
            logger.debug('stop')

        except ConnectionClosed:
            pass
        await trio.sleep(0)


async def receive_coords_data(sending_channel, request):
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
            logger.debug(f'Coords qty: {len(buses)}')
        except ConnectionClosed:
            break
        await trio.sleep(0)


async def main():
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    async with trio.open_nursery() as nursery:
        (
            send_to_processing,
            recieve_for_processing
        ) = trio.open_memory_channel(0)
        (
            send_for_render,
            recieve_for_render
        ) = trio.open_memory_channel(0)
        async with send_for_render, recieve_for_render, send_to_processing,\
                recieve_for_processing:
            receive_func = partial(
                receive_coords_data, send_to_processing.clone()
            )
            serve_recieve = partial(
                serve_websocket,
                receive_func,
                '127.0.0.1',
                8080,
                ssl_context=None
            )
            sender_func = partial(
                talk_to_browser, recieve_for_render.clone(), nursery
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
                collect_all_data,
                send_for_render.clone(),
                recieve_for_processing.clone()
            )


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
