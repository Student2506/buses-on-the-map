import json
import logging

import trio
from trio_websocket import ConnectionClosed, serve_websocket

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)

TEMPLATE = {
    'msgType': 'Buses',
    'buses': [
        {'busId': 'c790cc', 'lat': 55.7500, 'lng': 37.600, 'route': '120'},
        {'busId': 'a134aa', 'lat': 55.7494, 'lng': 37.621, 'route': '670к'},
    ]
}


async def browser_responder(request):
    ws = await request.accept()
    while True:
        try:
            # message = await ws.get_message()
            message = json.loads(TEMPLATE)
            await ws.send_message(message)
        except ConnectionClosed:
            break


async def main():
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    await serve_websocket(
        browser_responder, '127.0.0.1', 8000, ssl_context=None
    )


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
