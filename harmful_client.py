import logging

import trio
from trio_websocket import ConnectionClosed, open_websocket_url


async def hamful_client():
    for text in ('hi there', '{"sometext": "somevalue"}'):
        try:
            async with open_websocket_url(
                'ws://localhost:8000/', ssl_context=None
            ) as ws:
                await ws.send_message(text)
                logging.debug(dir(ws))
                message = await ws.get_message()
                logging.info(f'Received message {message}')
        except OSError as ose:
            logging.error(f'Connection attempt failed: {ose}')
        except ConnectionClosed as e:
            logging.error(f'Connection closed with: {e} {ws.closed}')


async def main():
    await hamful_client()


if __name__ == '__main__':
    trio.run(main)
