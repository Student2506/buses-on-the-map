import glob
import json
import logging
from contextlib import suppress
from contextvars import ContextVar
from functools import wraps
from itertools import cycle, islice
from random import choice, randint
from sys import stderr

import asyncclick as click
import trio
from trio_websocket import ConnectionClosed, HandshakeError, open_websocket_url

SEND_TIMEOUT = ContextVar('send_timeout', default=0.1)
RELAUNCH_TIMEOUT = 10

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)


def relaunch_on_disconnect(async_function):
    @wraps(async_function)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                return await async_function(*args, **kwargs)
            except (ConnectionClosed, HandshakeError):
                logger.error('Connection closed')
                await trio.sleep(RELAUNCH_TIMEOUT)
    return wrapper


@relaunch_on_disconnect
async def send_updates(server_address, receive_channel):
    async with open_websocket_url(f'ws://{server_address}:8080') as ws:
        while True:
            message_to_send = []
            with trio.move_on_after(SEND_TIMEOUT.get()):
                async for message in receive_channel:
                    message_to_send.append(message)
                    await trio.sleep(0)
            message_to_send = json.dumps(message_to_send, ensure_ascii=False)
            await ws.send_message(message_to_send)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def load_routes(directory_path='routes'):
    routes = glob.glob(f'{directory_path}/*.json')
    for filepath in routes:
        with open(filepath, 'r', encoding='utf-8') as file:
            yield json.load(file)


def route_random_start(route):
    rand_route = route.copy()
    coords = rand_route['coordinates']
    checkpoint = randint(0, len(coords))
    first_part_of_route_coords = list(
        islice(coords, checkpoint)
    )
    second_part_of_route_coords = list(
        islice(coords, checkpoint, None)
    )
    route_current = second_part_of_route_coords + first_part_of_route_coords
    rand_route['coordinates'] = route_current
    return rand_route


async def run_bus(bus_id, route, send_channel):
    rand_route = route_random_start(route)
    try:
        for coordinates in cycle(rand_route['coordinates']):
            message = {
                'busId': bus_id,
                'lat': coordinates[0],
                'lng': coordinates[1],
                'route': rand_route['name']
            }
            await send_channel.send(message)
            await trio.sleep(SEND_TIMEOUT.get())
    except OSError as ose:
        print(f'Connection attempt failed {ose}', file=stderr)


@click.command()
@click.option('--server', default='127.0.0.1')
@click.option('--routes_number', default=10000)
@click.option('--buses_per_route', default=10)
@click.option('--websockets_number', default=5)
@click.option('--emulator_id', default='')
@click.option('--refresh_timeout', default=0.1)
@click.option('-v', '--verbose', count=True)
async def main(
    server, routes_number, buses_per_route, websockets_number, emulator_id,
    refresh_timeout, verbose
):
    SEND_TIMEOUT.set(refresh_timeout)
    logging_level = {
        0: logging.ERROR,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG
    }
    logging.basicConfig(level=logging_level.get(verbose), format=FORMAT)
    channels = []
    for _ in range(websockets_number):
        (
            send_channel,
            receive_channel
        ) = trio.open_memory_channel(0)
        channels.append((send_channel, receive_channel))
    async with trio.open_nursery() as nursery:
        routes = []
        async for route in load_routes():
            routes.append(route)
        for route in islice(routes, routes_number):
            for i in range(buses_per_route):
                send_channel, _ = choice(channels)
                nursery.start_soon(
                    run_bus,
                    generate_bus_id(f'{emulator_id}{route["name"]}', str(i)),
                    route,
                    send_channel
                )
        for _, receive_channel in channels:
            nursery.start_soon(
                send_updates,
                server,
                receive_channel
            )


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        main(_anyio_backend="trio")
