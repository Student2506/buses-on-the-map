import logging

import trio
from trio_websocket import ConnectionClosed, serve_websocket

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)


async def receive_coords_data(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            logger.debug(message)
        except ConnectionClosed:
            break


async def main():
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    await serve_websocket(
        receive_coords_data, '127.0.0.1', 8080, ssl_context=None
    )


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
