import json
import logging
import os
from itertools import cycle, islice
from random import choice, randint

import trio
from trio_websocket import open_websocket_url

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
CHANNELS = 5
BUSES_PER_ROUTE = 40


async def send_updates(server_address, receive_channel):
    async with open_websocket_url(f'ws://{server_address}:8080') as ws:
        async for message in receive_channel:
            await ws.send_message(message)
            await trio.sleep(0)


def generate_bus_id(route_id, bus_index):
    return f'{route_id}-{bus_index}'


async def run_bus(bus_id, route, send_channel):
    await trio.sleep(randint(0, 5))
    coords = route['coordinates']
    checkpoint = randint(0, len(coords))
    first_part_of_route_coords = list(
        islice(coords, checkpoint)
    )
    second_part_of_route_coords = list(
        islice(coords, checkpoint, None)
    )
    route_current = second_part_of_route_coords + first_part_of_route_coords
    while True:
        TEMPLATE = {}
        for coords in cycle(route_current):
            TEMPLATE = {
                'busId': bus_id,
                'lat': coords[0],
                'lng': coords[1],
                'route': bus_id.split('-')[0]
            }

            message = json.dumps(TEMPLATE, ensure_ascii=False)
            await send_channel.send(message)
            await trio.sleep(0)


async def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, encoding='utf-8') as f:
                yield json.load(f)


async def main():
    logging.basicConfig(level=logging.ERROR, format=FORMAT)
    channels = []
    for _ in range(CHANNELS):
        (
            send_channel,
            receive_channel
        ) = trio.open_memory_channel(0)
        channels.append((send_channel, receive_channel))
    try:
        routes = []
        async for route in load_routes():
            routes.append(route)
        async with trio.open_nursery() as nursery:
            for route in routes:
                for i in range(BUSES_PER_ROUTE):
                    send_channel, _ = choice(channels)
                    nursery.start_soon(
                        run_bus,
                        generate_bus_id(route['name'], i),
                        route,
                        send_channel
                    )
            for _, receive_channel in channels:
                nursery.start_soon(
                    send_updates,
                    '127.0.0.1',
                    receive_channel
                )
    except OSError as ose:
        logger.error(f'Connection attempt failed: {ose}')
    except trio.MultiError as e:
        logger.error(f'Server has closed connection.: {e}')


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
