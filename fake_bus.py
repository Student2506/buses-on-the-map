import json
import logging
import os
from contextlib import suppress
from contextvars import ContextVar
from itertools import cycle, islice
from random import choice, randint
from sys import stderr

import asyncclick as click
import trio
from trio_websocket import open_websocket_url

SEND_TIMEOUT = ContextVar('send_timeout', default=0.1)
ROUTES_NUMBER = ContextVar('routes_number', default=10000)

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


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
    files_count = len([name for name in os.listdir(directory_path) if
                      name.endswith('.json')])
    routes_number = ROUTES_NUMBER.get()
    routes_number = min(files_count, routes_number)
    for filename in os.listdir(directory_path)[:routes_number]:
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                yield json.load(file)


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
    route_random_start(route)
    try:
        # async with open_websocket_url(url) as ws:
        for coordinates in cycle(route['coordinates']):
            message = {
                'busId': bus_id,
                'lat': coordinates[0],
                'lng': coordinates[1],
                'route': route['name']
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
    ROUTES_NUMBER.set(routes_number)
    logging_level = {
        '0': logging.ERROR,
        '1': logging.WARNING,
        '2': logging.INFO,
        '3': logging.DEBUG
    }
    logging.basicConfig(level=logging_level.get(str(verbose)), format=FORMAT)
    channels = []
    for _ in range(websockets_number):
        (
            send_channel,
            receive_channel
        ) = trio.open_memory_channel(0)
        channels.append((send_channel, receive_channel))
    async with trio.open_nursery() as nursery:
        async for route in load_routes():
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
