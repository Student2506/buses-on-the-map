import json
import logging
import os

import trio
from trio_websocket import open_websocket_url

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, encoding='utf-8') as f:
                yield json.load(f)


async def main():
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    try:
        for route in load_routes():
            async with open_websocket_url('ws://127.0.0.1:8080') as ws:
                TEMPLATE = {}
                for coords in route['coordinates']:
                    TEMPLATE = {
                        'busId': route['name'],
                        'lat': coords[0],
                        'lng': coords[1],
                        'route': str(route['name'])
                    }

                    message = json.dumps(TEMPLATE, ensure_ascii=False)
                    await ws.send_message(message)
                    await trio.sleep(1)
    except OSError as ose:
        logger.debug(f'Connection attempt failed: {ose}')


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
