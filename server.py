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
    route = browser_responder.params

    ws = await request.accept()
    while True:
        try:
            for coords in route['coordinates']:
                TEMPLATE['buses'] = [
                    {
                        'busId': route['name'],
                        'lat': coords[0],
                        'lng': coords[1],
                        'route': str(route['name'])
                    }
                ]
                message = json.dumps(TEMPLATE)
                await ws.send_message(message)
                await trio.sleep(1)
        except ConnectionClosed:
            break
        await trio.sleep(1)


async def main():
    async with await trio.open_file('156.json', encoding='utf-8') as f:
        route = json.loads(await f.read())

    logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    responder_func = browser_responder
    responder_func.params = route
    await serve_websocket(
        responder_func, '127.0.0.1', 8000, ssl_context=None
    )


if __name__ == '__main__':
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
