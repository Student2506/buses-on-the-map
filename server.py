import logging
from contextlib import suppress

import trio
from trio_websocket import ConnectionClosed, serve_websocket

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
RECEIVE_TIMEOUT = 1


async def echo_server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            # await ws.send_message(message)
            logger.debug(message)
        except ConnectionClosed:
            break
        await trio.sleep(RECEIVE_TIMEOUT)


async def main():
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    await serve_websocket(echo_server, '127.0.0.1', 8000, ssl_context=None)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
