import json
import logging
import os

import trio
from trio_websocket import open_websocket_url

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)


async def run_bus(url, bus_id, route):
    async with open_websocket_url(url) as ws:
        TEMPLATE = {}
        for coords in route['coordinates']:
            TEMPLATE = {
                'busId': bus_id,
                'lat': coords[0],
                'lng': coords[1],
                'route': str(route['name'])
            }

            message = json.dumps(TEMPLATE, ensure_ascii=False)
            await ws.send_message(message)
            await trio.sleep(1)


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, encoding='utf-8') as f:
                yield json.load(f)


async def main():
    url = 'ws://127.0.0.1:8080'
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    try:
        async with trio.open_nursery() as nursery:
            for route in load_routes():
                for i in range(1):
                    nursery.start_soon(
                        run_bus, url, f"{route['name']}-{str(i)}", route
                    )
    except OSError as ose:
        logger.debug(f'Connection attempt failed: {ose}')
    except trio.MultiError:
        logger.debug('Server has closed connection.')


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
