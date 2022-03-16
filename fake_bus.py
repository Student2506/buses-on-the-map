import json
from contextlib import suppress
from sys import stderr

import trio
from trio_websocket import open_websocket_url

SEND_TIMEOUT = 10


async def main():
    with open('156.json', encoding='utf-8') as fp:
        route_156 = json.load(fp)
    try:
        async with open_websocket_url('ws://127.0.0.1:8000') as ws:
            for coordinates in route_156['coordinates']:
                message = json.dumps({
                    'busId': route_156['name'],
                    'lat': coordinates[0],
                    'lng': coordinates[1],
                    'route': route_156['name']
                })
                await ws.send_message(message)
                await trio.sleep(SEND_TIMEOUT)
            # message = await ws.get_message()
            # print('bubub')
    except OSError as ose:
        print(f'Connection attempt failed {ose}', file=stderr)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
