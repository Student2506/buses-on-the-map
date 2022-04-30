import logging
from contextlib import suppress

import asyncclick as click
from trio_websocket import ConnectionClosed, open_websocket_url


async def harmful_bus(port):
    for text in ('hi there', '{"sometext": "somevalue"}'):
        try:
            async with open_websocket_url(
                f'ws://localhost:{port}/', ssl_context=None
            ) as ws:
                await ws.send_message(text)
                logging.debug(dir(ws))
                message = await ws.get_message()
                logging.info(f'Received message {message}')
        except OSError as ose:
            logging.error(f'Connection attempt failed: {ose}')
        except ConnectionClosed as e:
            logging.error(f'Connection on {port} closed with: {e} {ws.closed}')


@click.command()
@click.option(
    '--port', default=8080,
    help="Allows to choose port 8080 (for bus)/8000 (for browser) to check"
)
async def main(port):
    await harmful_bus(port)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        main(_anyio_backend="trio")
