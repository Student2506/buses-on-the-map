# Автобусы на карте Москвы

Веб-приложение показывает передвижение автобусов на карте Москвы.

<img src="screenshots/buses.gif">

## Как запустить

- Скачайте код
- Установите зависимости
```
python -m pip install -U pip
pip install -r requirements.txt
```

- Запустите сервер
```
python server.py
```
дополнительные ключи:
```
--bus_port (default=8080)
--browser_port (default=8000)
'-v', '--verbose'
```

- Запустите генератор перемещения автобусов
```
python fake_bus.py
```
дополнительные ключи:
```
--server (default='127.0.0.1')
--routes_number (default=10000)
--buses_per_route (default=10)
--websockets_number (default=5)
--emulator_id (default='')
--refresh_timeout (default=0.1)
'-v', '--verbose'
```

- Откройте в браузере файл index.html


## Настройки

Внизу справа на странице можно включить отладочный режим логгирования и указать нестандартный адрес веб-сокета.

<img src="screenshots/settings.png">

Настройки сохраняются в Local Storage браузера и не пропадают после обновления страницы. Чтобы сбросить настройки удалите ключи из Local Storage с помощью Chrome Dev Tools —> Вкладка Application —> Local Storage.

Если что-то работает не так, как ожидалось, то начните с включения отладочного режима логгирования.

## Формат данных

Фронтенд ожидает получить от сервера JSON сообщение со списком автобусов:

```js
{
  "msgType": "Buses",
  "buses": [
    {"busId": "c790сс", "lat": 55.7500, "lng": 37.600, "route": "120"},
    {"busId": "a134aa", "lat": 55.7494, "lng": 37.621, "route": "670к"},
  ]
}
```

Те автобусы, что не попали в список `buses` последнего сообщения от сервера будут удалены с карты.

Фронтенд отслеживает перемещение пользователя по карте и отправляет на сервер новые координаты окна:

```js
{
  "msgType": "newBounds",
  "data": {
    "east_lng": 37.65563964843751,
    "north_lat": 55.77367652953477,
    "south_lat": 55.72628839374007,
    "west_lng": 37.54440307617188,
  },
}
```



## Используемые библиотеки

- [Leaflet](https://leafletjs.com/) — отрисовка карты
- [loglevel](https://www.npmjs.com/package/loglevel) для логгирования


## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).

## Тесты
Утилита test_communication_error.py позволяет протестировать обработку ошибок на стороне сервера со стороны контроллера автобуса или бразуера

```
python test_communication_error.py --port 8000
```

Ожидаемое поведение - вывод ошибки контролеру/клиенту, закрытие соединения и продолжение работы сервера:

<img src="screenshots/error_handling.png">
