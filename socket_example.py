from contextlib import suppress

import trio
from trio_websocket import ConnectionClosed, serve_websocket


async def echo_server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            await ws.send_message(message)
        except ConnectionClosed:
            break


async def main():
    await serve_websocket(echo_server, '127.0.0.1', 8000, ssl_context=None)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
