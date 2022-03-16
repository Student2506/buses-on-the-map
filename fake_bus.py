import json
import os
from contextlib import suppress
from sys import stderr

import trio
from trio_websocket import open_websocket_url

SEND_TIMEOUT = 10


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                yield json.load(file)


async def run_bus(url, bus_id, route):
    try:
        async with open_websocket_url(url) as ws:
            for coordinates in route['coordinates']:
                message = json.dumps({
                    'busId': bus_id,
                    'lat': coordinates[0],
                    'lng': coordinates[1],
                    'route': route['name']
                }, ensure_ascii=False)
                await ws.send_message(message)
                await trio.sleep(SEND_TIMEOUT)
    except OSError as ose:
        print(f'Connection attempt failed {ose}', file=stderr)


async def main():
    async with trio.open_nursery() as nursery:
        for route in load_routes():
            nursery.start_soon(
                run_bus,
                'ws://127.0.0.1:8080',
                route['name'],
                route
            )


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
