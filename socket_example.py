import json
from contextlib import suppress

import trio
from trio_websocket import ConnectionClosed, serve_websocket


MESSAGE = {
  "msgType": "Buses",
  "buses": [
    {"busId": "c790сс", "lat": 55.7500, "lng": 37.600, "route": "120"},
    {"busId": "a134aa", "lat": 55.7494, "lng": 37.621, "route": "670к"},
  ]
}


async def echo_server(request):
    ws = await request.accept()
    with open('156.json', encoding='utf-8') as fp:
        route_156 = json.load(fp)
    # while True:
    for coordinates in route_156['coordinates']:
        try:
            # message = await ws.get_message()
            MESSAGE['buses'] = [
                {
                    'busId': route_156['name'],
                    'lat': coordinates[0],
                    'lng': coordinates[1],
                    'route': route_156['name']
                 }
            ]
            message = json.dumps(MESSAGE)
            await ws.send_message(message)
        except ConnectionClosed:
            break
        await trio.sleep(1)


async def main():
    await serve_websocket(echo_server, '127.0.0.1', 8000, ssl_context=None)


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
