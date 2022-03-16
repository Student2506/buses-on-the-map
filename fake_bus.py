import contextvars
import json
import logging
import os
from contextlib import suppress
from functools import wraps
from itertools import cycle, islice
from random import choice, randint

import asyncclick as click
import trio
from trio_websocket import ConnectionClosed, HandshakeError, open_websocket_url

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
REFRESH_TIMEOUT = contextvars.ContextVar('refresh_timeout')
logger = logging.getLogger(__name__)


def relaunch_on_disconnect(async_function):
    @wraps(async_function)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                return await async_function(*args, **kwargs)
            except (ConnectionClosed, HandshakeError):
                logger.error('Connection closed')
                await trio.sleep(10)
    return wrapper


@relaunch_on_disconnect
async def send_updates(server_address, receive_channel):
    async with open_websocket_url(f'ws://{server_address}:8080') as ws:
        async for message in receive_channel:
            await ws.send_message(message)
            await trio.sleep(REFRESH_TIMEOUT.get())


def generate_bus_id(route_id, bus_index):
    return f'{route_id}-{bus_index}'


def route_random_start(route):
    coords = route['coordinates']
    checkpoint = randint(0, len(coords))
    first_part_of_route_coords = list(
        islice(coords, checkpoint)
    )
    second_part_of_route_coords = list(
        islice(coords, checkpoint, None)
    )
    route_current = second_part_of_route_coords + first_part_of_route_coords
    route['coordinates'] = route_current


async def run_bus(bus_id, route, send_channel):
    await trio.sleep(randint(0, REFRESH_TIMEOUT.get()))
    route_random_start(route)
    while True:
        current_position = {}
        for coords in cycle(route['coordinates']):
            current_position = {
                'busId': bus_id,
                'lat': coords[0],
                'lng': coords[1],
                'route': bus_id.split('-')[0]
            }

            message = json.dumps(current_position, ensure_ascii=False)
            await send_channel.send(message)
            await trio.sleep(0)


async def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, encoding='utf-8') as f:
                yield json.load(f)


@click.command()
@click.option('--server', default='127.0.0.1')
@click.option('--routes_number', default=40)
@click.option('--buses_per_route', default=10)
@click.option('--websockets_number', default=5)
@click.option('--emulator_id', default='')
@click.option('--refresh_timeout', default=5)
@click.option('--v', default=logging.INFO)
async def main(
    server, routes_number, buses_per_route, websockets_number, emulator_id,
    refresh_timeout, v
):
    logging.basicConfig(level=v, format=FORMAT)
    REFRESH_TIMEOUT.set(refresh_timeout)
    channels = []
    for _ in range(websockets_number):
        (
            send_channel,
            receive_channel
        ) = trio.open_memory_channel(0)
        channels.append((send_channel, receive_channel))
    try:
        routes = []
        async for route in load_routes():
            routes.append(route)
        routes_number = min(len(routes), routes_number)
        async with trio.open_nursery() as nursery:
            for route in routes[:routes_number]:
                for i in range(buses_per_route):
                    send_channel, _ = choice(channels)
                    nursery.start_soon(
                        run_bus,
                        generate_bus_id(f'{emulator_id}{route["name"]}', i),
                        route,
                        send_channel
                    )
            for _, receive_channel in channels:
                nursery.start_soon(
                    send_updates,
                    server,
                    receive_channel
                )
    except OSError as ose:
        logger.error(f'Connection attempt failed: {ose}')
    # except ConnectionClosed:
    #     logger.error('Server has closed connection.')

if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        main(_anyio_backend="trio")
